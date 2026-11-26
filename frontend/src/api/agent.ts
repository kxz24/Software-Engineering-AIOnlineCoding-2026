/**
 * AI 助教接口与 SSE 客户端。
 *
 * 后端接口见 backend/agent/views.py：
 *   GET  /api/v1/agent/capabilities
 *   POST /api/v1/agent/sessions
 *   GET/POST /api/v1/agent/sessions/:id/messages
 *   GET  /api/v1/agent/sessions/:id/changes
 *   POST /api/v1/agent/changes/:id/revert
 *   GET/PUT /api/v1/agent/workspace
 */
import { ApiError, getToken } from "./client";

const AgentBase = "/api/v1/agent";

export type AgentLevel = "none" | "advise" | "edit";

export interface AgentQuota {
    limit: number;
    used: number;
    remaining: number | null;
}

export interface AgentCapabilities {
    enabled: boolean;
    level: AgentLevel;
    levelLabel: string;
    canEditCode: boolean;
    tools: string[];
    provider: string;
    model: string;
    mock: boolean;
    ready: boolean;
    promptVersion: string;
    quota: AgentQuota;
}

export interface AgentSessionInfo {
    sessionId: number;
    level: AgentLevel;
    levelLabel: string;
    provider: string;
    model: string;
    canEditCode: boolean;
    createdAt: string;
    quota: AgentQuota;
}

export interface AgentChatMessage {
    seq: number;
    role: "user" | "assistant" | "tool" | "system";
    content: string;
    toolCalls?: unknown;
    toolCallId?: string;
    name?: string;
    usage?: unknown;
    inputTokens: number;
    outputTokens: number;
    finishReason?: string;
    created: string;
}

export interface AgentWorkspaceFile {
    path: string;
    content: string;
    revision: number;
    updatedAt: string;
}

export interface AgentChangeRecord {
    changeId: number;
    path: string;
    revisionBefore: number;
    revisionAfter: number;
    diff: string;
    status: "applied" | "reverted";
    created: string;
    revertedAt: string | null;
}

/** SSE 事件；字段名与后端保持一致 */
export type AgentStreamEvent =
    | { type: "meta"; sessionId: number; userSeq: number }
    | { type: "delta"; text: string }
    | { type: "tool_call"; callId: string; name: string; arguments: Record<string, unknown> }
    | { type: "tool_result"; callId: string; name: string; ok: boolean; result: string }
    | { type: "change"; changeId: number; path: string; status: string; revisionAfter: number; additions: number; deletions: number; diff: string }
    | { type: "usage"; inputTokens: number; outputTokens: number; cacheHitTokens: number; cacheMissTokens: number }
    | { type: "done"; finishReason: string; assistantSeq?: number | null }
    | { type: "error"; code: string; message: string };

async function request<T>(path: string, options: {
    method?: string;
    body?: unknown;
} = {}): Promise<T> {
    let response: Response;
    try {
        // 以 /api 开头的绝对路径（教师端按考试查询）不拼接前缀
        const url = path.startsWith("/api") ? path : AgentBase + path;
        response = await fetch(url, {
            method: options.method || "GET",
            headers: {
                "Content-Type": "application/json",
                "Authorization": getToken() || "",
            },
            body: options.body === undefined ? undefined : JSON.stringify(options.body),
        });
    } catch (e) {
        throw new ApiError("无法连接后端服务，请确认已启动后端。", 0);
    }
    const json = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new ApiError((json as { message?: string }).message || "请求失败。", response.status);
    }
    return json as T;
}

/** 当前考试的 AI 级别与可用工具；未开启 AI 时后端返回 403 */
export function fetchAgentCapabilities(examId: number, problemId: number): Promise<AgentCapabilities> {
    return request(`/capabilities?examId=${examId}&problemId=${problemId}`);
}

/** 创建或取回会话（每场考试每道题一个） */
export function createAgentSession(examId: number, problemId: number): Promise<AgentSessionInfo> {
    return request("/sessions", {
        method: "POST",
        body: { examId, problemId },
    });
}

/** 会话历史（afterSeq 增量拉取） */
export function fetchAgentMessages(
    sessionId: number,
    afterSeq = 0
): Promise<{ messages: AgentChatMessage[] }> {
    const suffix = afterSeq > 0 ? `?afterSeq=${afterSeq}` : "";
    return request(`/sessions/${sessionId}/messages${suffix}`);
}

export function fetchAgentChanges(sessionId: number): Promise<{ changes: AgentChangeRecord[] }> {
    return request(`/sessions/${sessionId}/changes`);
}

export function revertAgentChange(
    changeId: number
): Promise<{ path: string; revision: number; content: string }> {
    return request(`/changes/${changeId}/revert`, { method: "POST", body: {} });
}

export interface AgentSessionListItem {
    sessionId: number;
    student: string;
    nickname: string;
    problemId: number;
    problemTitle: string;
    level: AgentLevel;
    levelLabel: string;
    provider: string;
    model: string;
    status: string;
    inputTokens: number;
    outputTokens: number;
    cacheHitTokens: number;
    messageCount: number;
    changeCount: number;
    created: string | null;
    lastActiveAt: string | null;
}

export interface AgentToolCallRecord {
    callId: string;
    name: string;
    arguments: Record<string, unknown>;
    ok: boolean;
    resultExcerpt: string;
    durationMs: number;
    created: string | null;
}

export interface AgentTranscript {
    session: {
        id: number;
        examId: number;
        problemId: number;
        problemTitle: string;
        student: string;
        level: AgentLevel;
        levelLabel: string;
        provider: string;
        model: string;
        promptVersion: string;
        status: string;
        inputTokens: number;
        outputTokens: number;
        cacheHitTokens: number;
        cacheMissTokens: number;
        created: string | null;
        lastActiveAt: string | null;
        endedAt: string | null;
    };
    messages: AgentChatMessage[];
    toolCalls: AgentToolCallRecord[];
    changes: AgentChangeRecord[];
}

/** 教师端：本场考试的全部 AI 会话（用量 + 消息数 + 修改次数） */
export function fetchAgentExamSessions(
    examId: number
): Promise<{ sessions: AgentSessionListItem[] }> {
    return request(`/api/v1/exams/${examId}/agent/sessions`);
}

/** 教师端：单条会话的完整转录（对话 + 工具调用 + 代码修改） */
export function fetchAgentTranscript(sessionId: number): Promise<AgentTranscript> {
    return request(`/sessions/${sessionId}/transcript`);
}

export function fetchAgentWorkspace(
    examId: number,
    problemId: number
): Promise<{ files: AgentWorkspaceFile[] }> {
    return request(`/workspace?examId=${examId}&problemId=${problemId}`);
}

function parseEventBlock(raw: string): AgentStreamEvent | null {
    const lines = raw.split("\n");
    let event = "";
    const dataLines: string[] = [];
    lines.forEach(line => {
        if (line.startsWith("event:")) {
            event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
        }
    });
    if (!event || dataLines.length === 0) {
        return null;
    }
    try {
        return { type: event, ...JSON.parse(dataLines.join("\n")) } as AgentStreamEvent;
    } catch (e) {
        return null;
    }
}

/**
 * 发送一条消息并消费 SSE 流。
 *
 * 浏览器用 fetch + ReadableStream 解析（EventSource 无法携带 Authorization 头）；
 * signal 用于切换题目或离开页面时取消。
 */
export async function streamAgentMessage(
    sessionId: number,
    payload: {
        content: string;
        action?: "answer" | "run" | "edit";
        activeFile?: string;
        code?: string;
        workspaceRevision?: number;
        workspaceFiles?: Record<string, string>;
        workspaceRevisions?: Record<string, number>;
        clientMessageId?: string;
    },
    onEvent: (event: AgentStreamEvent) => void,
    signal?: AbortSignal
): Promise<void> {
    let response: Response;
    try {
        response = await fetch(`${AgentBase}/sessions/${sessionId}/messages`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Authorization": getToken() || "",
            },
            body: JSON.stringify(payload),
            signal,
        });
    } catch (e) {
        if ((e as Error).name === "AbortError") {
            return;
        }
        throw new ApiError("无法连接后端服务，请确认已启动后端。", 0);
    }
    if (!response.ok) {
        const json = await response.json().catch(() => ({}));
        throw new ApiError((json as { message?: string }).message || "发送失败。", response.status);
    }
    if (!response.body) {
        throw new ApiError("当前浏览器不支持流式响应。", 0);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            buffer = buffer.replace(/\r\n/g, "\n");
            let index = buffer.indexOf("\n\n");
            while (index >= 0) {
                const block = buffer.slice(0, index);
                buffer = buffer.slice(index + 2);
                const event = parseEventBlock(block);
                if (event) {
                    onEvent(event);
                }
                index = buffer.indexOf("\n\n");
            }
        }
        const tail = parseEventBlock(buffer);
        if (tail) {
            onEvent(tail);
        }
    } catch (e) {
        if ((e as Error).name === "AbortError") {
            return;
        }
        throw e;
    } finally {
        reader.releaseLock();
    }
}
