# -*- coding: utf-8 -*-
"""AI 助教接口与分级权限的测试。

模型调用全部用本地 provider 替身，不访问 DeepSeek；判题沙箱相关的
工具不在这里跑（需要 Docker），只验证权限与落库。
"""
from datetime import timedelta

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from exam.models import Exam, ExamProblem
from problem.models import Problem
from user.models import User
from utils.jwt import encrypt_password

from . import service, tools
from .levels import TOOLS_BY_LEVEL
from .policy import CODE_BLOCK_PLACEHOLDER, sanitize_advise_text
from .providers import DeepSeekProvider, _extract_usage
from .models import AgentMessage, AgentSession, CodeChange, WorkspaceFile


class RoundProvider:
    """按轮次返回预设事件的 provider 替身。"""

    def __init__(self, rounds):
        self.rounds = list(rounds)
        self.calls = 0

    def stream(self, messages, tools, max_tokens=1024):
        events = self.rounds[min(self.calls, len(self.rounds) - 1)]
        self.calls += 1
        yield from events


def text_round(text="好的。", usage=120):
    return [
        {"type": "delta", "text": text},
        {"type": "usage", "usage": {"prompt_tokens": usage, "completion_tokens": 20},
         "inputTokens": usage, "outputTokens": 20,
         "cacheHitTokens": 0, "cacheMissTokens": usage},
        {"type": "done", "finishReason": "stop"},
    ]


class ProviderTests(SimpleTestCase):
    """provider 的地址拼接与用量字段解析（不联网）。"""

    def test_chat_url_handles_base_variants(self):
        provider = DeepSeekProvider("k", base_url="https://llmapi.paratera.com")
        self.assertEqual(provider._chat_url(),
                         "https://llmapi.paratera.com/v1/chat/completions")
        provider = DeepSeekProvider("k", base_url="https://llmapi.paratera.com/v1")
        self.assertEqual(provider._chat_url(),
                         "https://llmapi.paratera.com/v1/chat/completions")
        provider = DeepSeekProvider("k", base_url="https://x.example/v1/chat/completions")
        self.assertEqual(provider._chat_url(),
                         "https://x.example/v1/chat/completions")

    def test_usage_reads_openai_style_cached_tokens(self):
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 50,
            "prompt_tokens_details": {"cached_tokens": 768},
        }
        parsed = _extract_usage(usage)
        self.assertEqual(parsed["inputTokens"], 1000)
        self.assertEqual(parsed["outputTokens"], 50)
        self.assertEqual(parsed["cacheHitTokens"], 768)
        self.assertEqual(parsed["cacheMissTokens"], 232)

    def test_usage_reads_deepseek_native_cache_fields(self):
        usage = {"prompt_tokens": 500, "completion_tokens": 10,
                 "prompt_cache_hit_tokens": 300, "prompt_cache_miss_tokens": 200}
        parsed = _extract_usage(usage)
        self.assertEqual(parsed["cacheHitTokens"], 300)
        self.assertEqual(parsed["cacheMissTokens"], 200)


class AdviseGuardTests(SimpleTestCase):
    """二级回复过滤：完整代码不能出现在建议里。"""

    def test_fenced_block_is_removed(self):
        text = "先检查输入解析。\n```python\nprint(a + b)\n```\n再对比样例。"
        cleaned = sanitize_advise_text(text)
        self.assertNotIn("print(a + b)", cleaned)
        self.assertIn("先检查输入解析", cleaned)
        self.assertIn(CODE_BLOCK_PLACEHOLDER, cleaned)

    def test_unclosed_fence_is_removed(self):
        text = "思路如下：\n```python\nprint(a + b)"
        cleaned = sanitize_advise_text(text)
        self.assertNotIn("print(a + b)", cleaned)
        self.assertIn("思路如下", cleaned)

    def test_consecutive_code_lines_are_removed(self):
        text = "可以参考：\nfor i in range(n):\n    total += i\nreturn total\n然后自己实现。"
        cleaned = sanitize_advise_text(text)
        self.assertNotIn("for i in range", cleaned)
        self.assertIn("然后自己实现", cleaned)
        self.assertIn(CODE_BLOCK_PLACEHOLDER, cleaned)

    def test_prose_and_short_inline_code_are_kept(self):
        text = "可以用 `input()` 读取一行，注意还要处理空行。"
        self.assertEqual(sanitize_advise_text(text), text)


class AgentBaseTestCase(TestCase):
    def setUp(self):
        # 测试一律走本地 mock，避免读取 backend/.env 里的真实密钥
        self._override = override_settings(AGENT_PROVIDER="mock", DEEPSEEK_API_KEY="")
        self._override.enable()
        self.addCleanup(self._override.disable)

        self.client = APIClient()
        self.teacher = User.objects.create(
            username="teacher1", password=encrypt_password("secret6"),
            nickname="刘老师", role=User.ROLE_TEACHER,
        )
        self.student = User.objects.create(
            username="2023012345", password=encrypt_password("secret6"),
            nickname="李同学", role=User.ROLE_STUDENT,
        )
        self.other_student = User.objects.create(
            username="2023019999", password=encrypt_password("secret6"),
            nickname="王同学", role=User.ROLE_STUDENT,
        )
        self.teacher_token = self.login("teacher1")
        self.student_token = self.login("2023012345")
        self.other_token = self.login("2023019999")

        self.problem = Problem.objects.create(
            title="A + B", type=Problem.TYPE_ALGORITHM,
            language=Problem.LANGUAGE_PYTHON, created_by=self.teacher,
            description="读入两个整数，输出和。",
            time_limit_ms=1000, memory_limit_mb=128, output_limit_kb=64,
        )
        self.problem.samples.create(
            name="样例 1", input_data="1 2\n", expected_output="3\n", is_sample=True
        )
        self.problem.samples.create(
            name="隐藏 1", input_data="9 9\n", expected_output="18\n", is_sample=False
        )
        self.exam = self.create_exam(Exam.AI_LIMITED)

    def login(self, username):
        resp = self.client.patch(
            "/api/v1/login", {"username": username, "password": "secret6"}, format="json"
        )
        return resp.json()["jwt"]

    def auth(self, token=None):
        self.client.credentials(HTTP_AUTHORIZATION=token or self.student_token)

    def create_exam(self, ai_mode, **overrides):
        now = timezone.now()
        exam = Exam.objects.create(
            title="AI 测试考试", course="软件工程",
            start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1),
            status=Exam.STATUS_PUBLISHED, ai_mode=ai_mode, created_by=self.teacher,
            **overrides,
        )
        ExamProblem.objects.create(exam=exam, problem=self.problem, order=0, score=100)
        return exam

    def create_session(self, exam=None):
        exam = exam or self.exam
        return AgentSession.objects.create(
            exam=exam, student=self.student, problem=self.problem,
            level=service.level_for_exam(exam), provider="mock", model="mock-agent",
        )


class LevelTests(AgentBaseTestCase):
    def test_ai_mode_mapping(self):
        cases = {
            Exam.AI_CLOSED: AgentSession.LEVEL_NONE,
            Exam.AI_LIMITED: AgentSession.LEVEL_ADVISE,
            Exam.AI_OPEN: AgentSession.LEVEL_EDIT,
        }
        for mode, level in cases.items():
            exam = Exam(ai_mode=mode)
            self.assertEqual(service.level_for_exam(exam), level)

    def test_tools_by_level(self):
        self.assertNotIn("write_file", TOOLS_BY_LEVEL[AgentSession.LEVEL_ADVISE])
        self.assertIn("write_file", TOOLS_BY_LEVEL[AgentSession.LEVEL_EDIT])
        self.assertEqual(TOOLS_BY_LEVEL[AgentSession.LEVEL_NONE], ())

    def test_capabilities_closed_forbidden(self):
        exam = self.create_exam(Exam.AI_CLOSED)
        self.auth()
        resp = self.client.get(
            "/api/v1/agent/capabilities",
            {"examId": exam.id, "problemId": self.problem.id},
        )
        self.assertEqual(resp.status_code, 403)

    def test_capabilities_advise_and_edit(self):
        self.auth()
        resp = self.client.get(
            "/api/v1/agent/capabilities",
            {"examId": self.exam.id, "problemId": self.problem.id},
        )
        body = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["level"], AgentSession.LEVEL_ADVISE)
        self.assertFalse(body["canEditCode"])
        self.assertNotIn("write_file", body["tools"])
        self.assertIn("read_workspace", body["tools"])

        exam = self.create_exam(Exam.AI_OPEN)
        resp = self.client.get(
            "/api/v1/agent/capabilities",
            {"examId": exam.id, "problemId": self.problem.id},
        )
        body = resp.json()
        self.assertEqual(body["level"], AgentSession.LEVEL_EDIT)
        self.assertTrue(body["canEditCode"])
        self.assertIn("write_file", body["tools"])

    def test_non_candidate_forbidden(self):
        self.exam.candidates.add(self.student)   # 名单只有本人
        self.auth(self.other_token)
        resp = self.client.get(
            "/api/v1/agent/capabilities",
            {"examId": self.exam.id, "problemId": self.problem.id},
        )
        self.assertEqual(resp.status_code, 403)


class SessionAndMessageTests(AgentBaseTestCase):
    def test_session_is_idempotent(self):
        self.auth()
        first = self.client.post(
            "/api/v1/agent/sessions",
            {"examId": self.exam.id, "problemId": self.problem.id}, format="json",
        ).json()
        second = self.client.post(
            "/api/v1/agent/sessions",
            {"examId": self.exam.id, "problemId": self.problem.id}, format="json",
        ).json()
        self.assertEqual(first["sessionId"], second["sessionId"])
        self.assertEqual(AgentSession.objects.count(), 1)

    def test_closed_exam_cannot_create_session(self):
        exam = self.create_exam(Exam.AI_CLOSED)
        self.auth()
        resp = self.client.post(
            "/api/v1/agent/sessions",
            {"examId": exam.id, "problemId": self.problem.id}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_send_message_streams_and_persists(self):
        self.auth()
        session_id = self.client.post(
            "/api/v1/agent/sessions",
            {"examId": self.exam.id, "problemId": self.problem.id}, format="json",
        ).json()["sessionId"]

        resp = self.client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            {"content": "帮我看看这段代码", "activeFile": "p1_a.py",
             "code": "a, b = map(int, input().split())\nprint(a + b)\n"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn("event: meta", body)
        self.assertIn("event: delta", body)
        self.assertIn("event: usage", body)
        self.assertIn("event: done", body)

        session = AgentSession.objects.get(id=session_id)
        self.assertEqual(session.messages.filter(role=AgentMessage.ROLE_USER).count(), 1)
        self.assertEqual(
            session.messages.filter(role=AgentMessage.ROLE_ASSISTANT).count(), 1
        )
        self.assertGreater(session.input_tokens, 0)
        self.assertGreater(session.output_tokens, 0)
        self.assertTrue(WorkspaceFile.objects.filter(
            exam=self.exam, student=self.student, path="p1_a.py"
        ).exists())

        history = self.client.get(
            f"/api/v1/agent/sessions/{session_id}/messages"
        ).json()["messages"]
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[-1]["role"], "assistant")

    def test_sse_accept_header(self):
        """浏览器带 Accept: text/event-stream 时不能被 DRF 协商成 406"""
        self.auth()
        session_id = self.client.post(
            "/api/v1/agent/sessions",
            {"examId": self.exam.id, "problemId": self.problem.id}, format="json",
        ).json()["sessionId"]
        resp = self.client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            {"content": "你好"}, format="json", HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(resp.status_code, 200)
        body = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn("event: delta", body)

    def test_quota_exceeded(self):
        self.exam.agent_token_quota = 1
        self.exam.save(update_fields=["agent_token_quota"])
        self.auth()
        session_id = self.client.post(
            "/api/v1/agent/sessions",
            {"examId": self.exam.id, "problemId": self.problem.id}, format="json",
        ).json()["sessionId"]
        first = self.client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            {"content": "第一问", "activeFile": "p1_a.py", "code": "print(1)"},
            format="json",
        )
        b"".join(first.streaming_content)
        second = self.client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            {"content": "第二问"}, format="json",
        )
        self.assertEqual(second.status_code, 429)

    def test_other_student_cannot_read_session(self):
        session = self.create_session()
        self.auth(self.other_token)
        resp = self.client.get(f"/api/v1/agent/sessions/{session.id}/messages")
        self.assertEqual(resp.status_code, 404)


class ToolPermissionTests(AgentBaseTestCase):
    def test_hidden_sample_not_in_prompt(self):
        session = self.create_session()
        messages = service.build_messages(session)
        system = messages[0]["content"]
        self.assertIn("1 2", system)          # 公开样例
        self.assertNotIn("9 9", system)       # 隐藏用例不能出现
        self.assertIn("样例 1", system)

    def test_advise_redacts_complete_code(self):
        session = self.create_session()   # limited → advise
        provider = RoundProvider([
            text_round("先检查输入解析。\n```python\nprint(a + b)\n```\n再对比样例。"),
        ])
        events = list(service.generate_events(session, provider=provider))
        streamed = "".join(event.get("text", "") for event in events
                           if event["type"] == "delta")
        self.assertIn("先检查输入解析", streamed)
        self.assertNotIn("print(a + b)", streamed)
        assistant = (
            session.messages.filter(role=AgentMessage.ROLE_ASSISTANT)
            .order_by("-seq").first()
        )
        self.assertNotIn("print(a + b)", assistant.content)

    def test_edit_mode_keeps_code(self):
        exam = self.create_exam(Exam.AI_OPEN)
        session = self.create_session(exam)
        provider = RoundProvider([text_round("修改如下：\n```python\nprint(a + b)\n```")])
        events = list(service.generate_events(session, provider=provider))
        streamed = "".join(event.get("text", "") for event in events
                           if event["type"] == "delta")
        self.assertIn("print(a + b)", streamed)

    def test_advise_cannot_write_file(self):
        session = self.create_session()       # limited → advise
        provider = RoundProvider([
            [
                {"type": "tool_call", "id": "call_1", "name": "write_file",
                 "arguments": {"path": "p1_a.py", "content": "print(2)"}},
                {"type": "usage", "usage": {}, "inputTokens": 10, "outputTokens": 5,
                 "cacheHitTokens": 0, "cacheMissTokens": 10},
                {"type": "done", "finishReason": "tool_calls"},
            ],
            text_round("当前级别不能直接修改代码。"),
        ])
        events = list(service.generate_events(session, provider=provider))
        tool_results = [e for e in events if e["type"] == "tool_result"]
        self.assertEqual(tool_results[0]["ok"], False)
        self.assertIn("不可用工具", tool_results[0]["result"])
        self.assertEqual(CodeChange.objects.count(), 0)
        self.assertFalse(WorkspaceFile.objects.exists())

    def test_edit_can_write_file_and_revert(self):
        exam = self.create_exam(Exam.AI_OPEN)
        session = self.create_session(exam)
        WorkspaceFile.objects.create(
            exam=exam, student=self.student, problem=self.problem,
            path="p1_a.py", content="print(1)\n", revision=1,
        )
        provider = RoundProvider([
            [
                {"type": "tool_call", "id": "call_1", "name": "write_file",
                 "arguments": {"path": "p1_a.py", "content": "print(2)\n",
                               "expected_revision": 1}},
                {"type": "usage", "usage": {}, "inputTokens": 10, "outputTokens": 5,
                 "cacheHitTokens": 0, "cacheMissTokens": 10},
                {"type": "done", "finishReason": "tool_calls"},
            ],
            text_round("已经改好了。"),
        ])
        events = list(service.generate_events(session, provider=provider))
        self.assertTrue(any(e["type"] == "change" for e in events))
        change = CodeChange.objects.get(session=session)
        self.assertEqual(change.before_text, "print(1)\n")
        self.assertEqual(change.after_text, "print(2)\n")
        file = WorkspaceFile.objects.get(exam=exam, student=self.student, path="p1_a.py")
        self.assertEqual(file.content, "print(2)\n")

        # 学生撤销
        self.auth()
        resp = self.client.post(
            f"/api/v1/agent/changes/{change.id}/revert",
            {"expectedRevision": file.revision}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        file.refresh_from_db()
        self.assertEqual(file.content, "print(1)\n")
        change.refresh_from_db()
        self.assertEqual(change.status, CodeChange.STATUS_REVERTED)

    def test_tool_call_requires_allowed_tool(self):
        session = self.create_session()
        emitted = []
        context = tools.ToolContext(session, lambda name, data: emitted.append((name, data)))
        ok, result = tools.execute_tool(
            "write_file", {"path": "x.py", "content": "print(1)"}, context, session,
        )
        self.assertFalse(ok)
        self.assertIn("不可用工具", result)
        self.assertEqual(CodeChange.objects.count(), 0)


class WorkspaceAndSummaryTests(AgentBaseTestCase):
    def test_workspace_optimistic_lock(self):
        self.auth()
        first = self.client.put(
            "/api/v1/agent/workspace",
            {"examId": self.exam.id, "problemId": self.problem.id,
             "path": "p1_a.py", "content": "print(1)\n", "expectedRevision": 1},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        revision = first.json()["revision"]

        stale = self.client.put(
            "/api/v1/agent/workspace",
            {"examId": self.exam.id, "problemId": self.problem.id,
             "path": "p1_a.py", "content": "print(2)\n", "expectedRevision": 1},
            format="json",
        )
        self.assertEqual(stale.status_code, 409)
        fresh = self.client.put(
            "/api/v1/agent/workspace",
            {"examId": self.exam.id, "problemId": self.problem.id,
             "path": "p1_a.py", "content": "print(3)\n",
             "expectedRevision": revision},
            format="json",
        )
        self.assertEqual(fresh.status_code, 200)

    def test_teacher_summary(self):
        session = self.create_session()
        service.add_user_message(session, "你好")
        list(service.generate_events(session, provider=RoundProvider([text_round()])))

        self.auth(self.teacher_token)
        resp = self.client.get(f"/api/v1/exams/{self.exam.id}/agent/summary")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"]["students"], 1)
        self.assertGreater(body["total"]["inputTokens"], 0)

        self.auth()
        self.assertEqual(
            self.client.get(f"/api/v1/exams/{self.exam.id}/agent/summary").status_code, 403
        )

    def test_transcript_visible_to_teacher(self):
        session = self.create_session()
        service.add_user_message(session, "你好")
        list(service.generate_events(session, provider=RoundProvider([text_round()])))

        self.auth(self.teacher_token)
        resp = self.client.get(f"/api/v1/agent/sessions/{session.id}/transcript")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["session"]["student"], "2023012345")
        self.assertGreaterEqual(len(body["messages"]), 2)

        self.auth(self.other_token)
        self.assertEqual(
            self.client.get(f"/api/v1/agent/sessions/{session.id}/transcript").status_code,
            404,
        )
