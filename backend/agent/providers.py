# -*- coding: utf-8 -*-
"""模型接入：可替换的 provider。

首版提供两个实现：
  * MockProvider     —— 未配置模型密钥时使用，返回固定文本，便于本地联调与测试；
  * DeepSeekProvider —— DeepSeek 的 OpenAI 兼容接口，流式返回文本、工具调用与 usage。

provider 的输入输出与具体厂商无关：
  stream(messages, tools, max_tokens) 依次产出
    {"type": "delta",     "text": "..."}
    {"type": "tool_call", "id": "...", "name": "...", "arguments": {...}}
    {"type": "usage",     "usage": {...}, "inputTokens": n, "outputTokens": n, ...}
    {"type": "done",      "finishReason": "stop" | "tool_calls" | "length"}
"""
import json
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """模型调用失败（网络 / 鉴权 / 返回格式异常）。"""


class ProviderConfigError(ProviderError):
    """模型尚未配置（缺少密钥等）。"""


class MockProvider:
    """本地模拟模型：不联网，用于未配置 API 的开发与自动化测试。"""

    name = "mock"
    model = "mock-agent"

    def __init__(self, reply=None):
        self.reply = reply or (
            "（本地模拟模式）我已经收到你的问题。当前尚未配置真实模型 API，"
            "这里只演示对话链路与用量记录；配置 DEEPSEEK_API_KEY 后即可获得真实回答。"
        )

    def _count(self, text):
        # 粗估：4 个字符约 1 个 token，仅用于本地联调
        return max(1, len(str(text)) // 4)

    def stream(self, messages, tools, max_tokens=4096):
        prompt_tokens = sum(self._count(item.get("content") or "") for item in messages)
        output_tokens = self._count(self.reply)
        yield {"type": "delta", "text": self.reply}
        yield {
            "type": "usage",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": prompt_tokens + output_tokens,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": prompt_tokens,
            },
            "inputTokens": prompt_tokens,
            "outputTokens": output_tokens,
            "cacheHitTokens": 0,
            "cacheMissTokens": prompt_tokens,
        }
        yield {"type": "done", "finishReason": "stop"}


def _extract_usage(usage):
    """把 OpenAI 兼容的 usage 映射成统一字段；DeepSeek 额外返回缓存命中数。"""
    usage = usage or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    cache_hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    if not cache_hit:
        # OpenAI 兼容网关（如并行科技）用 prompt_tokens_details.cached_tokens
        cache_hit = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
    cache_miss = int(usage.get("prompt_cache_miss_tokens") or 0)
    if not cache_miss and input_tokens:
        cache_miss = input_tokens - cache_hit
    return {
        "usage": usage,
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "cacheHitTokens": cache_hit,
        "cacheMissTokens": cache_miss,
    }


class DeepSeekProvider:
    """DeepSeek 的 OpenAI 兼容接口（/chat/completions，SSE 流式）。"""

    name = "deepseek"

    def __init__(self, api_key, base_url=None, model=None, timeout=120):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.deepseek.com").rstrip("/")
        self.model = model or "deepseek-chat"
        self.timeout = timeout

    def _chat_url(self):
        """兼容两种 base_url 写法：带 /v1、不带 /v1，或直接给到完整路径。"""
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def stream(self, messages, tools, max_tokens=1024):
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            # 流式时也要拿到 usage，用于 token 记录
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        tool_calls = {}
        finish_reason = "stop"
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=10)) as client:
                with client.stream(
                    "POST", self._chat_url(),
                    headers=headers, json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = response.read().decode("utf-8", "replace")[:500]
                        raise ProviderError(
                            f"DeepSeek 返回 HTTP {response.status_code}: {body}"
                        )
                    for line in response.iter_lines():
                        if not line:
                            continue
                        if not line.startswith("data:"):
                            # 忽略 SSE 注释与空行
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except ValueError:
                            continue

                        if chunk.get("usage"):
                            yield {"type": "usage", **_extract_usage(chunk["usage"])}

                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        choice = choices[0]
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            yield {"type": "delta", "text": delta["content"]}
                        for item in delta.get("tool_calls") or []:
                            index = int(item.get("index") or 0)
                            slot = tool_calls.setdefault(
                                index, {"id": "", "name": "", "arguments": ""}
                            )
                            if item.get("id"):
                                slot["id"] = item["id"]
                            function = item.get("function") or {}
                            if function.get("name"):
                                slot["name"] += function["name"]
                            if function.get("arguments"):
                                slot["arguments"] += function["arguments"]
                        if choice.get("finish_reason"):
                            finish_reason = choice["finish_reason"]
        except httpx.HTTPError as exc:
            raise ProviderError(f"连接 DeepSeek 失败: {exc}") from exc

        for index in sorted(tool_calls):
            slot = tool_calls[index]
            if not slot["name"]:
                continue
            try:
                arguments = json.loads(slot["arguments"] or "{}")
            except ValueError:
                arguments = {}
            yield {
                "type": "tool_call",
                "id": slot["id"] or f"call_{index}",
                "name": slot["name"],
                "arguments": arguments,
            }
        yield {
            "type": "done",
            "finishReason": "tool_calls" if tool_calls else finish_reason,
        }


def provider_info():
    """当前 provider 的展示信息（capabilities 接口用）。"""
    provider = getattr(settings, "AGENT_PROVIDER", "mock")
    if provider == "deepseek":
        configured = bool(getattr(settings, "DEEPSEEK_API_KEY", ""))
        return {
            "provider": "deepseek",
            "model": getattr(settings, "AGENT_MODEL", "deepseek-chat"),
            "mock": False,
            "configured": configured,
        }
    return {
        "provider": "mock",
        "model": "mock-agent",
        "mock": True,
        "configured": False,
    }


def get_provider():
    """按配置返回 provider；DeepSeek 未配置密钥时抛 ProviderConfigError。"""
    provider = getattr(settings, "AGENT_PROVIDER", "mock")
    if provider == "deepseek":
        api_key = getattr(settings, "DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ProviderConfigError("尚未配置 DEEPSEEK_API_KEY")
        return DeepSeekProvider(
            api_key=api_key,
            base_url=getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=getattr(settings, "AGENT_MODEL", "deepseek-chat"),
            timeout=int(getattr(settings, "AGENT_REQUEST_TIMEOUT", 120)),
        )
    if provider == "mock":
        return MockProvider()
    raise ProviderConfigError(f"未知的 AGENT_PROVIDER: {provider}")
