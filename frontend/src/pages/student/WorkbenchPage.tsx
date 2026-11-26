import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useHistory, useParams } from "react-router-dom";
import { useSelector } from "react-redux";
import { Icon } from "../../components/Icon";
import { CodeEditor, LanguageOptions, languageForPath } from "../../components/CodeEditor";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { formatCountdown, secondsUntil } from "../../api/format";
import { Store } from "../../store";
import {
    ApiError,
    fetchMyExam,
    fetchMyExamSubmissions,
    MySubmission,
    StudentExamDetail,
    StudentProblem,
    submitCode,
} from "../../api/client";
import {
    AgentCapabilities,
    AgentChangeRecord,
    AgentChatMessage,
    AgentSessionInfo,
    AgentStreamEvent,
    AgentWorkspaceFile,
    createAgentSession,
    fetchAgentCapabilities,
    fetchAgentChanges,
    fetchAgentMessages,
    fetchAgentWorkspace,
    revertAgentChange,
    streamAgentMessage,
} from "../../api/agent";
import { formatClock } from "../../mock/workbench";
import { submissionLabel } from "../../api/judge";

type ProblemTabKey = "statement" | "samples" | "submissions";

/** 题目区顶部标签（数量按当前题目动态计算） */
const ProblemTabs: { key: ProblemTabKey; label: string }[] = [
    { key: "statement", label: "题目说明" },
    { key: "samples", label: "样例测试" },
    { key: "submissions", label: "提交记录" },
];

const TypeLabels: Record<string, string> = { engineering: "工程题", algorithm: "算法题" };
const DifficultyLabels: Record<string, string> = { easy: "简单", medium: "中等", hard: "困难" };
const AiModeLabels: Record<string, string> = { limited: "受限", open: "开放", closed: "关闭" };

/** 判题语言 → 文件扩展名（与 problem 模型的 LANGUAGE_CHOICES 对应） */
const LanguageExtensions: Record<string, string> = { python: "py", cpp: "cpp", c: "c", java: "java" };

/** 一道题在工作区里的文件名：p1_标题短语.py */
function problemPath(problem: StudentProblem): string {
    const extension = LanguageExtensions[problem.language] || "txt";
    const slug = problem.title.replace(/[\\/:*?"<>|\s]+/g, "_").slice(0, 24);
    return `p${problem.order + 1}_${slug}.${extension}`;
}

function filesForProblem(problem: StudentProblem): { label: string; path: string; content: string }[] {
    if (problem.publicFiles) {
        return Object.entries(problem.publicFiles).map(([label, content]) => ({
            label, path: `p${problem.problemId}/${label}`, content,
        }));
    }
    return [{ label: problemPath(problem), path: problemPath(problem), content: problem.starterCode || "" }];
}

/** ISO 时间 → HH:MM:SS（时间线 / 提交记录用） */
function timeOf(iso: string): string {
    const date = new Date(iso);
    if (isNaN(date.getTime())) {
        return "--:--:--";
    }
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

/** 本地草稿的结构：按考试维度存到 localStorage，刷新页面不丢代码 */
interface DraftPayload {
    version: 2;
    contents: Record<string, string>;
    languages: Record<string, string>;
}

/** 读取并校验本地草稿，损坏或旧版本时当作没有 */
function loadDraft(key: string): DraftPayload | null {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) {
            return null;
        }
        const data = JSON.parse(raw);
        if (data && data.version === 2 && typeof data.contents === "object") {
            return data as DraftPayload;
        }
    } catch (e) {
        // JSON 损坏等情况直接忽略
    }
    return null;
}

/** Agent 输入框：一行可输入的 textarea */
const AgentInputStyle: React.CSSProperties = {
    display: "block",
    width: "100%",
    height: 44,
    margin: 0,
    padding: 0,
    border: "none",
    outline: "none",
    resize: "none",
    background: "transparent",
    color: "#334155",
    fontFamily: "inherit",
    fontSize: 11.5,
    lineHeight: 1.5,
};

/** 样例测试的输入 / 期望输出展示块 */
const SampleBoxStyle: React.CSSProperties = {
    margin: 0,
    padding: "8px 10px",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    fontFamily: "\"SFMono-Regular\", Consolas, Menlo, monospace",
    fontSize: 11,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
};

/** 把 `反引号` 包住的片段渲染成行内 <code> */
function renderInlineCode(text: string): React.ReactNode {
    return text.split("`").map((part, index) =>
        index % 2 === 1
            ? <code key={index}>{part}</code>
            : <React.Fragment key={index}>{part}</React.Fragment>
    );
}

interface AgentToolView {
    callId: string;
    name: string;
    arguments: Record<string, unknown>;
    ok?: boolean;
    result?: string;
}

/** AI 回复：按 ``` 代码块拆开渲染，文本保留换行 */
function renderAgentText(text: string): React.ReactNode {
    const parts = text.split("```");
    return parts.map((part, index) => {
        if (index % 2 === 1) {
            const code = part.replace(/^[A-Za-z0-9_+#.-]*\n/, "");
            return <pre className="agent-code" key={index}>{code}</pre>;
        }
        return <div className="agent-text" key={index}>{renderInlineCode(part)}</div>;
    });
}

/** 历史消息渲染：用户气泡 / AI 卡片 / 工具结果 */
function renderAgentMessage(message: AgentChatMessage): React.ReactNode {
    if (message.role === "user") {
        return (
            <div className="msg-user" key={message.seq}>
                <div className="bubble">{message.content}</div>
            </div>
        );
    }
    if (message.role === "assistant") {
        return (
            <div className="msg-agent" key={message.seq}>
                <div className="agent-meta">
                    <span className="name">Coding Agent</span>
                    <span className="time">{formatClock(new Date(message.created))}</span>
                </div>
                {message.content && (
                    <div className="agent-card">{renderAgentText(message.content)}</div>
                )}
            </div>
        );
    }
    if (message.role === "tool") {
        return (
            <div className="agent-tool" key={message.seq}>
                <span className="agent-tool-name">工具 · {message.name || "tool"}</span>
                <span className="agent-tool-result">
                    {(message.content || "").slice(0, 160)}
                </span>
            </div>
        );
    }
    return null;
}

/**
 * 04 做题工作台：满屏工作区（题目 / 编辑器 / 终端 / Coding Agent）。
 *
 * 数据来自 /api/v1/my/exams/:id：题面、样例与初始代码由后端下发
 * （隐藏测试不会下发）；提交后在后台异步判题。
 * Coding Agent 已接入 /api/v1/agent/：按考试级别只读或可写，
 * SSE 流式展示回复、工具调用与代码修改。
 */
export function WorkbenchPage() {
    const { examId } = useParams<{ examId: string }>();
    const history = useHistory();
    const user = useSelector((s: Store) => s.user);

    const [detail, setDetail] = useState<StudentExamDetail | null>(null);
    const [submissions, setSubmissions] = useState<MySubmission[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        Promise.all([fetchMyExam(Number(examId)), fetchMyExamSubmissions(Number(examId))])
            .then(([exam, result]) => {
                setDetail(exam);
                setSubmissions(result.submissions);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [examId]);

    // 倒计时按秒真实递减
    const [seconds, setSeconds] = useState(0);
    useEffect(() => {
        if (!detail) {
            return;
        }
        setSeconds(secondsUntil(detail.endTime));
        const timer = window.setInterval(() => setSeconds(secondsUntil(detail.endTime)), 1000);
        return () => window.clearInterval(timer);
    }, [detail]);

    const problems = detail?.problems || [];
    const [currentProblemId, setCurrentProblemId] = useState<number | null>(null);
    const problem = useMemo(
        () => problems.find(item => item.problemId === currentProblemId) || problems[0] || null,
        [problems, currentProblemId]
    );

    // 工作区：按题目（文件路径）组织的代码内容与「未保存」标记。
    // 代码是学生的实际作答内容，按考试存为本地草稿，刷新 / 断网不丢失
    const draftKey = `workbench-draft-${examId}`;
    const [savedDraft] = useState(() => loadDraft(draftKey));
    const [contents, setContents] = useState<Record<string, string>>({});
    const [selectedProjectFile, setSelectedProjectFile] = useState<Record<number, string>>({});
    const [modified, setModified] = useState<Record<string, boolean>>({});
    /** 各文件显式选择过的语言（'' / 缺省 = 按扩展名自动推断） */
    const [languages, setLanguages] = useState<Record<string, string>>(() => ({
        ...(savedDraft ? savedDraft.languages : {}),
    }));
    const [edited, setEdited] = useState(false);
    // AI 改动工作区后重建编辑器 model，让 Monaco 显示服务端内容
    const [editorEpoch, setEditorEpoch] = useState(0);
    const [savedClock, setSavedClock] = useState<string | null>(null);

    // 题目加载后初始化每道题的代码内容（本地草稿优先，其次初始代码）
    useEffect(() => {
        if (!detail) {
            return;
        }
        setContents(current => {
            const next = { ...current };
            detail.problems.forEach(item => {
                filesForProblem(item).forEach(file => {
                    if (next[file.path] == null) {
                        next[file.path] = savedDraft?.contents[file.path] ?? file.content;
                    }
                });
            });
            return next;
        });
        if (currentProblemId == null && detail.problems.length > 0) {
            setCurrentProblemId(detail.problems[0].problemId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [detail]);

    const currentPath = problem ? (
        selectedProjectFile[problem.problemId] || filesForProblem(problem)[0]?.path || ""
    ) : "";
    const currentFileLabel = problem?.publicFiles && currentPath.includes("/") ?
        currentPath.slice(currentPath.indexOf("/") + 1) : currentPath;
    const currentLanguage = (currentPath && languages[currentPath]) ||
        (problem ? (problem.publicFiles ? languageForPath(currentPath) :
            (LanguageExtensions[problem.language] ? problem.language : languageForPath(currentPath))) : "plaintext");

    /** 把当前工作区写入本地草稿（自动保存与手动保存共用） */
    const writeDraft = () => {
        try {
            const payload: DraftPayload = { version: 2, contents, languages };
            localStorage.setItem(draftKey, JSON.stringify(payload));
        } catch (e) {
            // 存储失败（隐私模式 / 空间不足）不影响继续作答
        }
        setEdited(false);
        setSavedClock(formatClock(new Date()));
    };

    // 自动保存：工作区状态变化后延迟 800ms 写入本地草稿（debounce 掉连续击键）
    useEffect(() => {
        if (!detail) {
            return;
        }
        const timer = window.setTimeout(writeDraft, 800);
        return () => window.clearTimeout(timer);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [draftKey, detail, contents, languages]);

    /** 手动保存草稿 */
    const handleSaveDraft = () => {
        writeDraft();
        toast("草稿已保存", "success");
    };

    const [problemTab, setProblemTab] = useState<ProblemTabKey>("statement");
    const [submitting, setSubmitting] = useState(false);

    // AI 助教：级别 / 会话 / 消息 / 修改记录（接口见 api/agent.ts）
    const [agentCaps, setAgentCaps] = useState<AgentCapabilities | null>(null);
    const [agentSession, setAgentSession] = useState<AgentSessionInfo | null>(null);
    const [agentMessages, setAgentMessages] = useState<AgentChatMessage[]>([]);
    const [agentChanges, setAgentChanges] = useState<AgentChangeRecord[]>([]);
    const [agentDisabledReason, setAgentDisabledReason] = useState("");
    const [agentError, setAgentError] = useState<string | null>(null);
    const [agentLoading, setAgentLoading] = useState(false);
    const [agentStreaming, setAgentStreaming] = useState(false);
    const [agentStream, setAgentStream] = useState<{ text: string; tools: AgentToolView[] } | null>(null);
    const [agentUsage, setAgentUsage] = useState<{ input: number; output: number } | null>(null);
    // 回复因达到输出上限被截断时提示考生可以「继续」
    const [agentTruncated, setAgentTruncated] = useState(false);
    // path -> 服务端工作区版本号；发送消息时带上，后端据此决定是否用编辑器内容覆盖
    const [agentRevisions, setAgentRevisions] = useState<Record<string, number>>({});
    const [agentDraft, setAgentDraft] = useState("");
    const [agentTab, setAgentTab] = useState<"chat" | "changes">("chat");
    const agentAbortRef = useRef<AbortController | null>(null);

    const chatRef = useRef<HTMLDivElement>(null);
    const agentStreamText = agentStream ? agentStream.text : "";

    // 追加消息 / 流式输出时滚动到会话底部
    useEffect(() => {
        const chat = chatRef.current;
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    }, [agentMessages.length, agentStreamText, agentStreaming]);

    /** 当前题目的提交次数 */
    const mySubmissions = useMemo(
        () => (problem ? submissions.filter(item => item.problemId === problem.problemId) : []),
        [submissions, problem]
    );
    const used = mySubmissions.length;
    const remaining = detail ? Math.max(0, detail.submitLimit - used) : 0;
    const finished = !!detail && (detail.status === "finished" || seconds <= 0);
    const currentCode = (currentPath && contents[currentPath]) || "";

    /** 编辑代码：写入内容、打上未保存标记 */
    const handleCodeChange = (path: string, value: string) => {
        setContents(current => (current[path] === value ? current : { ...current, [path]: value }));
        setModified(current => ({ ...current, [path]: true }));
        setEdited(true);
    };

    /** 把服务端工作区覆盖到编辑器（三级模式下 AI 已写入的内容） */
    const applyWorkspaceFiles = (files: AgentWorkspaceFile[]) => {
        if (!files.length) {
            return;
        }
        const changed = files.some(file => contents[file.path] !== file.content &&
            !(problem?.publicFiles && file.revision === 1 && contents[file.path] != null));
        if (changed) {
            setContents(current => {
                const next = { ...current };
                files.forEach(file => {
                    if (!(problem?.publicFiles && file.revision === 1 && next[file.path] != null)) {
                        next[file.path] = file.content;
                    }
                });
                return next;
            });
            setModified(current => {
                const next = { ...current };
                files.forEach(file => {
                    next[file.path] = false;
                });
                return next;
            });
            setEditorEpoch(value => value + 1);
        }
        setAgentRevisions(current => {
            const next = { ...current };
            files.forEach(file => {
                next[file.path] = file.revision;
            });
            return next;
        });
    };

    const refreshWorkspace = () => {
        if (!detail || !problem) {
            return Promise.resolve();
        }
        return fetchAgentWorkspace(detail.id, problem.problemId)
            .then(result => applyWorkspaceFiles(result.files))
            .catch(() => {
                // 工作区刷新失败不影响对话继续
            });
    };

    /** 加载当前题目的 AI 能力、会话与历史 */
    const loadAgent = () => {
        if (!detail || !problem) {
            return;
        }
        const examIdValue = detail.id;
        const problemIdValue = problem.problemId;
        setAgentLoading(true);
        setAgentError(null);
        setAgentDisabledReason("");
        fetchAgentCapabilities(examIdValue, problemIdValue)
            .then(caps => {
                setAgentCaps(caps);
                return createAgentSession(examIdValue, problemIdValue).then(session => {
                    setAgentSession(session);
                    return Promise.all([
                        fetchAgentMessages(session.sessionId),
                        fetchAgentChanges(session.sessionId),
                        fetchAgentWorkspace(examIdValue, problemIdValue),
                    ]).then(([history, changes, workspace]) => {
                        setAgentMessages(history.messages);
                        setAgentChanges(changes.changes);
                        setAgentRevisions(current => {
                            const next = { ...current };
                            workspace.files.forEach(file => {
                                next[file.path] = file.revision;
                            });
                            return next;
                        });
                        if (caps.canEditCode) {
                            applyWorkspaceFiles(workspace.files);
                        }
                    });
                });
            })
            .catch((e: ApiError) => {
                setAgentCaps(null);
                setAgentSession(null);
                if (e.status === 403) {
                    setAgentDisabledReason(e.message || "本场考试未开启 AI");
                } else {
                    setAgentError(e.message);
                }
            })
            .finally(() => setAgentLoading(false));
    };

    // 切换题目时重新加载该题的会话；离开页面时取消进行中的流
    useEffect(() => {
        agentAbortRef.current?.abort();
        setAgentCaps(null);
        setAgentSession(null);
        setAgentMessages([]);
        setAgentChanges([]);
        setAgentStream(null);
        setAgentStreaming(false);
        setAgentError(null);
        setAgentDisabledReason("");
        setAgentTab("chat");
        setAgentRevisions({});
        if (detail && problem) {
            loadAgent();
        }
        return () => {
            agentAbortRef.current?.abort();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [detail?.id, problem?.problemId]);

    /** 发送 Agent 消息：消费 SSE 流并同步回复、工具调用与代码修改 */
    const handleSend = () => {
        const text = agentDraft.trim();
        if (!text || !agentSession || !agentCaps || !agentCaps.ready || agentStreaming) {
            return;
        }
        const controller = new AbortController();
        agentAbortRef.current = controller;
        const sessionIdValue = agentSession.sessionId;
        setAgentStreaming(true);
        setAgentTruncated(false);
        setAgentError(null);
        setAgentTab("chat");
        setAgentDraft("");
        setAgentMessages(current => [...current, {
            seq: -Date.now(),
            role: "user",
            content: text,
            inputTokens: 0,
            outputTokens: 0,
            created: new Date().toISOString(),
        }]);
        setAgentStream({ text: "", tools: [] });

        const handleEvent = (event: AgentStreamEvent) => {
            switch (event.type) {
                case "delta":
                    setAgentStream(current => current
                        ? { ...current, text: current.text + event.text }
                        : { text: event.text, tools: [] });
                    break;
                case "tool_call":
                    setAgentStream(current => current ? {
                        ...current,
                        tools: [...current.tools, {
                            callId: event.callId,
                            name: event.name,
                            arguments: event.arguments,
                        }],
                    } : current);
                    break;
                case "tool_result":
                    setAgentStream(current => current ? {
                        ...current,
                        tools: current.tools.map(tool => tool.callId === event.callId
                            ? { ...tool, ok: event.ok, result: event.result }
                            : tool),
                    } : current);
                    break;
                case "change":
                    setAgentChanges(current => [{
                        changeId: event.changeId,
                        path: event.path,
                        revisionBefore: Math.max(0, event.revisionAfter - 1),
                        revisionAfter: event.revisionAfter,
                        diff: event.diff,
                        status: "applied",
                        created: new Date().toISOString(),
                        revertedAt: null,
                    }, ...current.filter(item => item.changeId !== event.changeId)]);
                    if (agentCaps.canEditCode) {
                        refreshWorkspace();
                    }
                    break;
                case "usage":
                    setAgentUsage({ input: event.inputTokens, output: event.outputTokens });
                    setAgentCaps(current => {
                        if (!current) {
                            return current;
                        }
                        const used = current.quota.used + event.inputTokens + event.outputTokens;
                        return {
                            ...current,
                            quota: {
                                ...current.quota,
                                used,
                                remaining: current.quota.limit
                                    ? Math.max(0, current.quota.limit - used)
                                    : null,
                            },
                        };
                    });
                    break;
                case "done":
                    if (event.finishReason === "length") {
                        setAgentTruncated(true);
                    }
                    break;
                case "error":
                    setAgentError(event.message);
                    break;
                default:
                    break;
            }
        };

        streamAgentMessage(sessionIdValue, {
            content: text,
            activeFile: currentPath,
            code: currentCode,
            workspaceRevision: currentPath ? agentRevisions[currentPath] : undefined,
            workspaceFiles: problem?.publicFiles ? Object.fromEntries(
                filesForProblem(problem).map(file => [file.path, contents[file.path] ?? file.content])
            ) : undefined,
            workspaceRevisions: problem?.publicFiles ? agentRevisions : undefined,
            clientMessageId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        }, handleEvent, controller.signal)
            .then(() => {
                if (controller.signal.aborted) {
                    return;
                }
                return fetchAgentMessages(sessionIdValue).then(result => {
                    if (!controller.signal.aborted) {
                        setAgentMessages(result.messages);
                    }
                });
            })
            .then(() => {
                if (controller.signal.aborted) {
                    return;
                }
                return Promise.all([
                    refreshWorkspace(),
                    fetchAgentChanges(sessionIdValue).then(result => {
                        if (!controller.signal.aborted) {
                            setAgentChanges(result.changes);
                        }
                    }),
                ]);
            })
            .catch((e: ApiError) => {
                if (!controller.signal.aborted) {
                    setAgentError(e.message);
                }
            })
            .finally(() => {
                if (agentAbortRef.current === controller) {
                    setAgentStreaming(false);
                    setAgentStream(null);
                }
            });
    };

    /** 撤销一次 AI 修改并同步编辑器 */
    const handleRevert = (change: AgentChangeRecord) => {
        if (change.status !== "applied") {
            return;
        }
        revertAgentChange(change.changeId)
            .then(result => {
                setContents(current => ({ ...current, [result.path]: result.content }));
                setModified(current => ({ ...current, [result.path]: false }));
                setAgentRevisions(current => ({ ...current, [result.path]: result.revision }));
                setEditorEpoch(value => value + 1);
                toast("已撤销这次 AI 修改", "success");
                if (agentSession) {
                    return fetchAgentChanges(agentSession.sessionId)
                        .then(response => setAgentChanges(response.changes));
                }
                return undefined;
            })
            .catch((e: ApiError) => toast(e.message, "warning"));
    };

    /** 提交答卷：入队异步判题，结果在结果页轮询 */
    const handleSubmit = () => {
        if (!detail || !problem) {
            return;
        }
        if (remaining <= 0) {
            toast(`本题提交次数已用完（上限 ${detail.submitLimit} 次）`, "warning");
            return;
        }
        const confirmed = window.confirm(
            `确认提交「任务 ${problem.order + 1}：${problem.title}」？\n` +
            (problem.publicFiles ? `本次将一并提交 ${Object.keys(problem.publicFiles).length} 个文件。\n` : "") +
            `提交后在后台自动判题，本题剩余 ${remaining - 1} 次机会。`
        );
        if (!confirmed) {
            return;
        }
        setSubmitting(true);
        const projectFiles = problem.publicFiles ? Object.fromEntries(
            Object.keys(problem.publicFiles).map(name => [name, contents[`p${problem.problemId}/${name}`] ?? ""])
        ) : undefined;
        submitCode(detail.id, problem.problemId, currentCode, problem.language, projectFiles)
            .then(result => {
                setSubmitting(false);
                setSubmissions(current => [
                    {
                        id: result.submission.id,
                        examId: detail.id,
                        problemId: problem.problemId,
                        problemTitle: problem.title,
                        language: problem.language,
                        status: result.submission.status,
                        created: result.submission.created,
                        code: currentCode,
                    },
                    ...current,
                ]);
                setProblemTab("submissions");
                toast(`已提交，正在判题，本题剩余 ${result.remaining} 次`, "success");
                // 提交成功后进入 05 提交结果页查看收卷状态
                history.push(Routes.examResult(detail.id));
            })
            .catch((e: ApiError) => {
                setSubmitting(false);
                toast(e.message, "warning");
            });
    };

    if (loading || (!detail && !error)) {
        return (
            <div className="wb-root">
                <div className="canvas">
                    <header className="topbar">
                        <div className="topbar-left">
                            <div className="brand">
                                <div className="logo">
                                    <Icon name="code" size={17} stroke="#ffffff" strokeWidth={2.2}/>
                                </div>
                                <div className="brand-name">AI Coding 考试平台</div>
                            </div>
                            <div className="divider-v"/>
                            <div className="exam-name">加载中…</div>
                        </div>
                        <div className="topbar-right">
                            <div className="avatar">{(user?.nickname || "生").slice(0, 1)}</div>
                        </div>
                    </header>
                    <div className="main" style={{ alignItems: "center", justifyContent: "center" }}>
                        <div className="muted" style={{ fontSize: 12 }}>正在加载考试与题目…</div>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !detail) {
        return (
            <div className="wb-root">
                <div className="canvas">
                    <header className="topbar">
                        <div className="topbar-left">
                            <div className="brand">
                                <div className="logo">
                                    <Icon name="code" size={17} stroke="#ffffff" strokeWidth={2.2}/>
                                </div>
                                <div className="brand-name">AI Coding 考试平台</div>
                            </div>
                            <div className="divider-v"/>
                            <div className="exam-name">无法进入考场</div>
                        </div>
                        <div className="topbar-right">
                            <div className="avatar">{(user?.nickname || "生").slice(0, 1)}</div>
                        </div>
                    </header>
                    <div className="main" style={{ alignItems: "center", justifyContent: "center" }}>
                        <div style={{ textAlign: "center" }}>
                            <div style={{ color: "#b91c1c", fontSize: 12.5, marginBottom: 10 }}>
                                <Icon name="alert-triangle" size={14}/> {error || "考试不存在"}
                            </div>
                            <div style={{ fontSize: 11.5, color: "#64748b", marginBottom: 12 }}>
                                可能原因：不在考生名单 / 考试未发布 / 后端未启动
                            </div>
                            <Link className="btn btn-secondary" to={Routes.examList}>返回我的考试</Link>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="wb-root">
            <div className="canvas">
                {/* 顶部栏 */}
                <header className="topbar">
                    <div className="topbar-left">
                        <div className="brand">
                            <div className="logo">
                                <Icon name="code" size={17} stroke="#ffffff" strokeWidth={2.2}/>
                            </div>
                            <div className="brand-name">AI Coding 考试平台</div>
                        </div>
                        <div className="divider-v"/>
                        <div className="exam-name">{detail.title}</div>
                    </div>
                    <div className="topbar-right">
                        <div className="chip chip-ai">
                            <Icon name="shield-check" size={13} strokeWidth={1.9}/>
                            AI {AiModeLabels[detail.aiMode] || detail.aiMode}模式
                        </div>
                        <div className="chip chip-timer">
                            <Icon name="clock" size={14}/>
                            {finished ? "考试已结束" : `剩余 ${formatCountdown(seconds)}`}
                        </div>
                        <div className="save-status">
                            <span className="dot" style={edited ? { background: "#f59e0b" } : undefined}/>
                            {edited ? "有未保存修改" : (savedClock ? `已自动保存 ${savedClock}` : "自动保存已开启")}
                        </div>
                        <button className="btn-submit" type="button"
                                onClick={handleSubmit}
                                disabled={submitting || finished || remaining <= 0}
                                title={finished ? "考试已结束" : remaining <= 0 ? "本题提交次数已用完" : undefined}>
                            <Icon name="arrow-up" size={14} strokeWidth={1.9}/>
                            提交本题
                            <span className="sub">剩余 {remaining} 次</span>
                        </button>
                        <div className="avatar">{(user?.nickname || "生").slice(0, 1)}</div>
                    </div>
                </header>

                {/* 考试信息条 */}
                <div className="metabar">
                    <div className="metabar-left">
                        {problem && (
                            <>
                                <span className="task-name">
                                    任务 {problem.order + 1} / {problems.length} · {problem.title}
                                </span>
                                <span className="meta-chip blue">{TypeLabels[problem.type] || problem.type}</span>
                                <span className="meta-chip">{problem.language}</span>
                                {problem.publicFiles && (
                                    <span className="meta-chip blue">
                                        {Object.keys(problem.publicFiles).length} 个文件一并提交
                                    </span>
                                )}
                            </>
                        )}
                        <span className="meta-chip">{detail.submitLimit} 次提交 / 题</span>
                        <span className="meta-chip green"><span className="status-dot"/>提交后自动判题</span>
                    </div>
                    <div className="metabar-right">
                        <span>本地草稿自动保存</span>
                        <span className="divider-dot">·</span>
                        <span className="link" onClick={() => history.push(Routes.examPrecheck(examId))}>
                            查看考试须知
                        </span>
                    </div>
                </div>

                <div className="main">
                    {/* 左侧：题目文件树 + 提交时间线 */}
                    <aside className="sidebar-left">
                        <div className="panel-head">
                            <div className="panel-title">工作区</div>
                            <button type="button"
                                    className="link"
                                    style={{ fontSize: 11 }}
                                    title="立即把当前代码写入本地草稿"
                                    onClick={handleSaveDraft}>
                                保存草稿
                            </button>
                        </div>
                        <div className="section-label">{detail.course || "EXAM"}</div>
                        <div className="tree">
                            {problems.map(item => {
                                const files = filesForProblem(item);
                                return (
                                    <React.Fragment key={item.problemId}>
                                        <div className="tree-row root" title={item.title}
                                             onClick={() => setCurrentProblemId(item.problemId)}>
                                            <Icon name="folder" size={13} strokeWidth={1.7} className="folder-ico"/>
                                            <span className="tree-filename">任务 {item.order + 1} · {item.title}</span>
                                            <span className="tree-count">{files.length}</span>
                                        </div>
                                        {files.map(file => {
                                            const isActive = !!problem && item.problemId === problem.problemId && currentPath === file.path;
                                            return (
                                                <div key={file.path}
                                                     className={"tree-row lv2" + (isActive ? " active" : "")}
                                                     title={file.label}
                                                     onClick={() => {
                                                         setCurrentProblemId(item.problemId);
                                                         setSelectedProjectFile(current => ({ ...current, [item.problemId]: file.path }));
                                                     }}>
                                                    <Icon name="file" size={13} strokeWidth={1.7} className="file-ico"/>
                                                    <span className="tree-filename">{file.label}</span>
                                                    {modified[file.path] && <span className="modified-dot"/>}
                                                </div>
                                            );
                                        })}
                                    </React.Fragment>
                                );
                            })}
                            {problems.length === 0 && (
                                <div className="tree-row lv1 muted">本场考试没有题目</div>
                            )}
                        </div>

                        <div className="left-bottom">
                            <div className="timeline-head">
                                <div className="timeline-title">提交时间线</div>
                                <div className="timeline-link"
                                     onClick={() => history.push(Routes.examReport(examId))}>
                                    查看全部
                                </div>
                            </div>
                            {submissions.length === 0 && (
                                <div className="timeline-item">
                                    <span className="tl-dot"/>
                                    <div>
                                        <div className="tl-text">暂无提交记录</div>
                                    </div>
                                </div>
                            )}
                            {submissions.slice(0, 6).map(item => (
                                <div className="timeline-item" key={item.id}>
                                    <span className="tl-dot green"/>
                                    <div>
                                        <div className="tl-text">提交 #{item.id} · {item.problemTitle}</div>
                                        <div className="tl-time">
                                            {timeOf(item.created)} · {submissionLabel(item).label}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </aside>

                    {/* 中间：题目 / 编辑器 / 终端 */}
                    <section className="center">
                        <div className="problem">
                            <div className="tabs">
                                {ProblemTabs.map(tab => (
                                    <div key={tab.key}
                                         className={"tab" + (problemTab === tab.key ? " active" : "")}
                                         onClick={() => setProblemTab(tab.key)}>
                                        {tab.label}
                                        {tab.key === "samples" && problem && (
                                            <span className="tab-count">{problem.samples.length}</span>
                                        )}
                                        {tab.key === "submissions" && (
                                            <span className="tab-count">{used}</span>
                                        )}
                                    </div>
                                ))}
                                <div className="tabs-right">
                                    {problem ? `当前任务 ${problem.order + 1} / ${problems.length}` : ""}
                                </div>
                            </div>

                            {problem && problemTab === "statement" && (
                                <div className="problem-body">
                                    <div className="problem-title-row">
                                        <div className="problem-title">任务 {problem.order + 1}：{problem.title}</div>
                                        <div className="badges">
                                            <span className="badge gray">{DifficultyLabels[problem.difficulty] || problem.difficulty}</span>
                                            <span className="badge blue">{problem.score} 分</span>
                                        </div>
                                    </div>
                                    <p className="problem-desc" style={{ whiteSpace: "pre-wrap" }}>
                                        {renderInlineCode(problem.description || "（本题没有题面描述）")}
                                    </p>
                                    <div className="ai-note">
                                        <Icon name="sparkles" size={13}/>
                                        <span>
                                            <strong>AI 使用策略：{AiModeLabels[detail.aiMode] || detail.aiMode}模式</strong>
                                            {" · AI 对话会留痕，可用于学习过程分析"}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {problem && problemTab === "samples" && (
                                <div className="problem-body">
                                    {problem.samples.length === 0 && (
                                        <p className="rule-line"><span className="label">样例：</span>本题没有公开样例</p>
                                    )}
                                    {problem.samples.map(sample => (
                                        <div key={sample.name} style={{ marginBottom: 12 }}>
                                            <p className="rule-line" style={{ marginBottom: 6 }}>
                                                <span className="label">{sample.name}</span>
                                            </p>
                                            <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <div className="muted" style={{ fontSize: 10.5, marginBottom: 3 }}>输入</div>
                                                    <pre style={SampleBoxStyle}>{sample.input}</pre>
                                                </div>
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <div className="muted" style={{ fontSize: 10.5, marginBottom: 3 }}>期望输出</div>
                                                    <pre style={SampleBoxStyle}>{sample.expected}</pre>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                    <p className="rule-line">
                                        <span className="label">提示：</span>
                                        隐藏测试不会下发到浏览器，仅在独立判题容器中运行。
                                    </p>
                                </div>
                            )}

                            {problem && problemTab === "submissions" && (
                                <div className="problem-body">
                                    <p className="rule-line">
                                        <span className="label">已用次数：</span>
                                        {used} / {detail.submitLimit}（每次提交自动判题，同一题取最高分）
                                    </p>
                                    {mySubmissions.length === 0 && (
                                        <p className="rule-line"><span className="label">暂无提交</span></p>
                                    )}
                                    {mySubmissions.map(item => (
                                        <details key={item.id} style={{ marginBottom: 8 }}>
                                            <summary style={{ cursor: "pointer", fontSize: 11.5 }}>
                                                #{item.id} · {new Date(item.created).toLocaleString()} ·{" "}
                                                {(() => {
                                                    const meta = submissionLabel(item);
                                                    return <span className={"badge " + meta.tone}>{meta.label}</span>;
                                                })()}
                                            </summary>
                                            <pre style={{ ...SampleBoxStyle, marginTop: 6 }}>{item.code}</pre>
                                        </details>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="editor">
                            <div className="editor-tabs">
                                <div className={"editor-tab active"}>
                                    <Icon name="file" size={12} stroke="#2563eb"/>
                                    {currentFileLabel || "—"}
                                    {modified[currentPath] && <span className="modified-dot"/>}
                                </div>
                                <div className="editor-actions">
                                    <select className="lang-select"
                                            title="当前文件的语法高亮语言"
                                            value={(currentPath && languages[currentPath]) || ""}
                                            onChange={event => setLanguages(current => ({
                                                ...current,
                                                [currentPath]: event.target.value,
                                            }))}>
                                        {LanguageOptions.map(option => (
                                            <option key={option.id} value={option.id}>{option.label}</option>
                                        ))}
                                    </select>
                                    <span className="ok">● 本地草稿已开启</span>
                                </div>
                            </div>
                            <div className="editor-body">
                                {currentPath ? (
                                    <CodeEditor key={"editor-" + editorEpoch}
                                                path={currentPath}
                                                initialValue={currentCode}
                                                language={currentLanguage}
                                                onChange={handleCodeChange}/>
                                ) : (
                                    <div className="muted" style={{ padding: 12, fontSize: 12 }}>没有可编辑的文件</div>
                                )}
                            </div>
                        </div>

                    </section>

                    {/* 右侧：Coding Agent（演示） */}
                    <aside className="agent">
                        <div className="agent-head">
                            <div className="agent-brand">
                                <div className="agent-logo">
                                    <Icon name="sparkles" size={15}/>
                                </div>
                                <div>
                                    <div className="agent-name">Coding Agent</div>
                                    <div className="agent-sub">
                                        {agentCaps
                                            ? `${agentCaps.levelLabel} · ${agentCaps.model}${agentCaps.mock ? " · 本地模拟" : ""}`
                                            : agentDisabledReason || (agentLoading ? "正在加载…" : "未接入")}
                                    </div>
                                </div>
                            </div>
                            <div className="agent-head-actions">
                                {agentCaps && (
                                    <span className="mode-chip">
                                        <Icon name="lock" size={10} strokeWidth={2}/>
                                        {agentCaps.canEditCode ? "可改代码" : "按需答疑"}
                                    </span>
                                )}
                                <span className="mode-chip">
                                    <Icon name="lock" size={10} strokeWidth={2}/>
                                    {AiModeLabels[detail.aiMode] || detail.aiMode}
                                </span>
                            </div>
                        </div>

                        {agentCaps && (
                            <div className="agent-tabs">
                                <span className={"agent-tab" + (agentTab === "chat" ? " active" : "")}
                                      onClick={() => setAgentTab("chat")}>对话</span>
                                <span className={"agent-tab" + (agentTab === "changes" ? " active" : "")}
                                      onClick={() => setAgentTab("changes")}>
                                    修改{agentChanges.length > 0 ? ` ${agentChanges.length}` : ""}
                                </span>
                                <span className="agent-tab-hint">
                                    {agentCaps.canEditCode ? "AI 可以直接修改工作区" : "AI 按提问范围回答，不修改工作区"}
                                </span>
                            </div>
                        )}

                        <div className="context-bar">
                            <span className="ctx-label">上下文</span>
                            <span className="ctx-chip">
                                <Icon name="file" size={10}/>
                                {currentPath || "—"}
                            </span>
                        </div>

                        {agentTab === "chat" ? (
                            <div className="chat" ref={chatRef}>
                                {agentLoading && <div className="agent-notice">正在加载 AI 会话…</div>}
                                {!agentLoading && agentDisabledReason && (
                                    <div className="agent-notice">{agentDisabledReason}</div>
                                )}
                                {agentError && <div className="agent-notice error">{agentError}</div>}
                                {agentTruncated && (
                                    <div className="agent-notice">
                                        回复达到输出上限被截断；发送「继续」可以让 AI 接着说。
                                    </div>
                                )}
                                {agentCaps && !agentCaps.ready && (
                                    <div className="agent-notice">
                                        模型尚未配置（缺少 API Key），当前只能查看历史记录。
                                    </div>
                                )}
                                {agentMessages.map(renderAgentMessage)}
                                {agentStream && (
                                    <div className="msg-agent">
                                        <div className="agent-meta">
                                            <span className="name">Coding Agent</span>
                                            <span className="time">回答处理中…</span>
                                        </div>
                                        {agentStream.text && (
                                            <div className="agent-card">{renderAgentText(agentStream.text)}</div>
                                        )}
                                        {agentStream.tools.map(tool => (
                                            <div className="agent-tool" key={tool.callId}>
                                                <span className="agent-tool-name">
                                                    工具 · {tool.name}
                                                    {tool.ok === false ? " · 失败" : tool.ok ? " · 完成" : " · 运行中"}
                                                </span>
                                                <span className="agent-tool-result">
                                                    {(tool.result || JSON.stringify(tool.arguments)).slice(0, 160)}
                                                </span>
                                            </div>
                                        ))}
                                        {!agentStream.text && agentStream.tools.length === 0 && (
                                            <div className="agent-card">
                                                <div className="agent-text muted">正在生成并审核回复…</div>
                                            </div>
                                        )}
                                    </div>
                                )}
                                {!agentLoading && !agentDisabledReason && !agentError && agentCaps
                                    && agentMessages.length === 0 && !agentStream && (
                                        <div className="agent-notice">
                                            可以问我题目思路、帮你看代码或分析 bug。
                                            {agentCaps.canEditCode
                                                ? "当前级别允许我直接修改工作区。"
                                                : "我会针对你的具体问题回答，不提供整题代码，也不会改动工作区。"}
                                        </div>
                                    )}
                            </div>
                        ) : (
                            <div className="chat">
                                {agentChanges.length === 0 && (
                                    <div className="agent-notice">还没有 AI 代码修改记录。</div>
                                )}
                                {agentChanges.map(change => (
                                    <div className="agent-change" key={change.changeId}>
                                        <div className="agent-change-head">
                                            <span className={"badge " + (change.status === "applied" ? "green" : "gray")}>
                                                {change.status === "applied" ? "已应用" : "已撤销"}
                                            </span>
                                            <span className="agent-change-path">{change.path}</span>
                                            <span className="muted" style={{ fontSize: 10 }}>
                                                v{change.revisionBefore} → v{change.revisionAfter}
                                            </span>
                                        </div>
                                        <pre className="agent-diff">{change.diff || "（无差异）"}</pre>
                                        {change.status === "applied" && (
                                            <span className="link"
                                                  style={{ fontSize: 10.5 }}
                                                  onClick={() => handleRevert(change)}>
                                                撤销这次修改
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="agent-input-wrap">
                            <div className="agent-input">
                                <textarea style={AgentInputStyle}
                                          value={agentDraft}
                                          disabled={agentStreaming || !agentCaps?.ready}
                                          placeholder={
                                              agentDisabledReason ? "本场考试未开启 AI"
                                                  : !agentCaps ? (agentLoading ? "正在加载 AI…" : "AI 暂不可用")
                                                      : !agentCaps.ready ? "AI 暂不可用：未配置模型密钥"
                                                          : agentCaps.canEditCode ? "描述问题，AI 可以直接修改代码…"
                                                              : "描述你想了解的概念、思路或具体卡住的地方…"
                                          }
                                          spellCheck={false}
                                          onChange={event => setAgentDraft(event.target.value)}
                                          onKeyDown={event => {
                                              if (event.key === "Enter" && !event.shiftKey) {
                                                  event.preventDefault();
                                                  handleSend();
                                              }
                                          }}/>
                                <div className="input-toolbar">
                                    <div className="input-tools">
                                        <span className="input-hint">
                                            {agentStreaming
                                                ? "正在生成，可点击右侧停止"
                                                : "Enter 发送 · Shift+Enter 换行"}
                                        </span>
                                        {agentCaps && (
                                            <span className="input-hint">
                                                {agentUsage
                                                    ? `本次 ${agentUsage.input + agentUsage.output}`
                                                    : `累计 ${agentCaps.quota.used}`} tokens
                                            </span>
                                        )}
                                    </div>
                                    {agentStreaming ? (
                                        <button className="send-btn" type="button"
                                                title="停止生成"
                                                onClick={() => agentAbortRef.current?.abort()}>
                                            停止
                                        </button>
                                    ) : (
                                        <button className="send-btn" type="button"
                                                disabled={!agentCaps?.ready || !agentDraft.trim()}
                                                onClick={handleSend}>
                                            <Icon name="send" size={14} strokeWidth={1.9}/>
                                        </button>
                                    )}
                                </div>
                            </div>
                            <div className="agent-foot">
                                <Icon name="lock" size={10} strokeWidth={2}/>
                                对话会留痕，可供学习过程分析
                            </div>
                        </div>
                    </aside>
                </div>

                {/* 底部状态栏 */}
                <footer className="statusbar">
                    <div className="status-left">
                        <span className="status-item"><span className="status-dot"/>本地作答模式</span>
                        <span className="status-item">提交后自动判题</span>
                    </div>
                    <div className="status-right">
                        <span className="status-item">{savedClock ? `草稿 ${savedClock}` : "自动保存已开启"}</span>
                        <span className="status-item">判题在后台独立容器中执行</span>
                    </div>
                </footer>
            </div>
        </div>
    );
}
