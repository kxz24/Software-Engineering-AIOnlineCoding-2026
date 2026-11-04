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
import { AgentPlaceholder, CannedReplies, TerminalLines, formatClock } from "../../mock/workbench";

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

interface AgentMessage {
    id: string;
    role: "user" | "agent";
    text?: string;
    time?: string;
    paragraphs?: string[];
}

/**
 * 04 做题工作台：满屏工作区（题目 / 编辑器 / 终端 / Coding Agent）。
 *
 * 数据来自 /api/v1/my/exams/:id：题面、样例与初始代码由后端下发
 * （隐藏测试不会下发）；提交当前只收卷存档，判定结果随判题服务接入。
 * Agent 对话与终端为本地演示。
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
    const [modified, setModified] = useState<Record<string, boolean>>({});
    /** 各文件显式选择过的语言（'' / 缺省 = 按扩展名自动推断） */
    const [languages, setLanguages] = useState<Record<string, string>>(() => ({
        ...(savedDraft ? savedDraft.languages : {}),
    }));
    const [edited, setEdited] = useState(false);
    const [savedClock, setSavedClock] = useState<string | null>(null);

    // 题目加载后初始化每道题的代码内容（本地草稿优先，其次初始代码）
    useEffect(() => {
        if (!detail) {
            return;
        }
        setContents(current => {
            const next = { ...current };
            detail.problems.forEach(item => {
                const path = problemPath(item);
                if (next[path] == null) {
                    next[path] = (savedDraft && savedDraft.contents[path]) || item.starterCode || "";
                }
            });
            return next;
        });
        if (currentProblemId == null && detail.problems.length > 0) {
            setCurrentProblemId(detail.problems[0].problemId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [detail]);

    const currentPath = problem ? problemPath(problem) : "";
    const currentLanguage = (currentPath && languages[currentPath]) ||
        (problem ? (LanguageExtensions[problem.language] ? problem.language : languageForPath(currentPath)) : "plaintext");

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

    // 终端演示：页签切换与清屏
    const [termTab, setTermTab] = useState<"test" | "output" | "problem">("test");
    const [termCleared, setTermCleared] = useState(false);

    // Agent 对话：本地演示（服务随后续迭代接入）
    const [messages, setMessages] = useState<AgentMessage[]>([
        {
            id: "agent-intro",
            role: "agent",
            time: formatClock(new Date()),
            paragraphs: [
                "你好，我是本场考试的 Coding Agent（演示）。",
                "Agent 服务将在下一迭代接入；当前的回复为本地演示，不会修改你的代码。",
            ],
        },
    ]);
    const [draft, setDraft] = useState("");
    const messageSeed = useRef(0);

    const chatRef = useRef<HTMLDivElement>(null);

    // 追加消息后滚动到会话底部
    useEffect(() => {
        const chat = chatRef.current;
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    }, [messages.length]);

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

    /** 发送 Agent 消息：追加用户气泡与一条模拟回复（本地状态） */
    const handleSend = () => {
        const text = draft.trim();
        if (!text) {
            return;
        }
        const seed = ++messageSeed.current;
        const time = formatClock(new Date());
        setMessages(current => [
            ...current,
            { id: "local-user-" + seed, role: "user", text },
            {
                id: "local-agent-" + seed,
                role: "agent",
                time,
                paragraphs: [CannedReplies[seed % CannedReplies.length]],
            },
        ]);
        setDraft("");
    };

    /** 提交答卷：只收卷存档（status=pending），判定随判题服务接入 */
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
            `评测服务接入前仅收卷存档；提交后本题剩余 ${remaining - 1} 次机会。`
        );
        if (!confirmed) {
            return;
        }
        setSubmitting(true);
        submitCode(detail.id, problem.problemId, currentCode, problem.language)
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
                toast(`已提交（待判定），本题剩余 ${result.remaining} 次`, "success");
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
                            提交答卷
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
                            </>
                        )}
                        <span className="meta-chip">{detail.submitLimit} 次提交 / 题</span>
                        <span className="meta-chip green"><span className="status-dot"/>提交后待判定</span>
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
                                const path = problemPath(item);
                                const isActive = !!problem && item.problemId === problem.problemId;
                                return (
                                    <div key={item.problemId}
                                         className={"tree-row lv1" + (isActive ? " active" : "")}
                                         onClick={() => setCurrentProblemId(item.problemId)}>
                                        <Icon name="file" size={13} strokeWidth={1.7} className="file-ico"/>
                                        <span>{path}</span>
                                        {modified[path] && <span className="modified-dot"/>}
                                    </div>
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
                                        <div className="tl-time">{timeOf(item.created)} · 待判定</div>
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
                                            {" · 对话留痕将计入过程报告（Agent 服务下一迭代接入）"}
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
                                        隐藏测试不会下发到浏览器，仅在判题时使用（判题服务接入后生效）。
                                    </p>
                                </div>
                            )}

                            {problem && problemTab === "submissions" && (
                                <div className="problem-body">
                                    <p className="rule-line">
                                        <span className="label">已用次数：</span>
                                        {used} / {detail.submitLimit}（每次提交覆盖保存，判定随判题服务接入）
                                    </p>
                                    {mySubmissions.length === 0 && (
                                        <p className="rule-line"><span className="label">暂无提交</span></p>
                                    )}
                                    {mySubmissions.map(item => (
                                        <details key={item.id} style={{ marginBottom: 8 }}>
                                            <summary style={{ cursor: "pointer", fontSize: 11.5 }}>
                                                #{item.id} · {new Date(item.created).toLocaleString()} ·{" "}
                                                <span className="badge gray">待判定</span>
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
                                    {currentPath || "—"}
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
                                    <CodeEditor path={currentPath}
                                                initialValue={currentCode}
                                                language={currentLanguage}
                                                onChange={handleCodeChange}/>
                                ) : (
                                    <div className="muted" style={{ padding: 12, fontSize: 12 }}>没有可编辑的文件</div>
                                )}
                            </div>
                        </div>

                        <div className="terminal">
                            <div className="terminal-head">
                                <div className="terminal-title">
                                    <Icon name="terminal" size={13} stroke="#475569"/>
                                    终端
                                </div>
                                <div className={"terminal-tab" + (termTab === "test" ? " active" : "")}
                                     title="演示数据，运行环境随判题容器接入"
                                     onClick={() => setTermTab("test")}>测试</div>
                                <div className={"terminal-tab" + (termTab === "output" ? " active" : "")}
                                     title="运行输出随判题容器接入"
                                     onClick={() => setTermTab("output")}>输出</div>
                                <div className={"terminal-tab" + (termTab === "problem" ? " active" : "")}
                                     title="运行问题随判题容器接入"
                                     onClick={() => setTermTab("problem")}>问题</div>
                                <div className="terminal-tab terminal-clear"
                                     title="清空当前页签内容"
                                     onClick={() => setTermCleared(true)}>清屏</div>
                            </div>
                            <div className="terminal-body">
                                {termTab === "test" && !termCleared && TerminalLines.map((line, lineIndex) => (
                                    <div className="term-line" key={lineIndex}>
                                        {line.map((segment, index) => (
                                            <span key={index}
                                                  className={segment.tone ? "term-" + segment.tone : undefined}>
                                                {segment.text}
                                            </span>
                                        ))}
                                    </div>
                                ))}
                                {termTab !== "test" && !termCleared && (
                                    <div className="term-line muted">
                                        {termTab === "output" ? "尚无运行输出。" : "没有运行问题。"}
                                        运行环境随判题容器接入（下一迭代）。
                                    </div>
                                )}
                                {termCleared && (
                                    <div className="term-line muted">已清屏；切回「测试」页签可重新载入演示数据。</div>
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
                                    <div className="agent-sub">演示 · 服务下一迭代接入</div>
                                </div>
                            </div>
                            <div className="agent-head-actions">
                                <span className="mode-chip">
                                    <Icon name="lock" size={10} strokeWidth={2}/>
                                    {AiModeLabels[detail.aiMode] || detail.aiMode}
                                </span>
                            </div>
                        </div>

                        <div className="context-bar">
                            <span className="ctx-label">上下文</span>
                            <span className="ctx-chip">
                                <Icon name="file" size={10}/>
                                {currentPath || "—"}
                            </span>
                        </div>

                        <div className="chat" ref={chatRef}>
                            {messages.map(message => message.role === "user" ? (
                                <div className="msg-user" key={message.id}>
                                    <div className="bubble">{message.text}</div>
                                </div>
                            ) : (
                                <div className="msg-agent" key={message.id}>
                                    <div className="agent-meta">
                                        <span className="name">Coding Agent</span>
                                        <span className="time">{message.time}</span>
                                    </div>
                                    <div className="agent-card">
                                        {(message.paragraphs || []).map((paragraph, index) => (
                                            <p key={index}>{renderInlineCode(paragraph)}</p>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="agent-input-wrap">
                            <div className="agent-input">
                                <textarea style={AgentInputStyle}
                                          value={draft}
                                          placeholder={AgentPlaceholder}
                                          spellCheck={false}
                                          onChange={event => setDraft(event.target.value)}
                                          onKeyDown={event => {
                                              if (event.key === "Enter" && !event.shiftKey) {
                                                  event.preventDefault();
                                                  handleSend();
                                              }
                                          }}/>
                                <div className="input-toolbar">
                                    <div className="input-tools">
                                        <span className="input-hint">Enter 发送 · Shift+Enter 换行</span>
                                    </div>
                                    <button className="send-btn" type="button" onClick={handleSend}>
                                        <Icon name="send" size={14} strokeWidth={1.9}/>
                                    </button>
                                </div>
                            </div>
                            <div className="agent-foot">
                                <Icon name="lock" size={10} strokeWidth={2}/>
                                对话将随试卷冻结，并计入过程评分
                            </div>
                        </div>
                    </aside>
                </div>

                {/* 底部状态栏 */}
                <footer className="statusbar">
                    <div className="status-left">
                        <span className="status-item"><span className="status-dot"/>本地作答模式</span>
                        <span className="status-item">提交后待判定</span>
                    </div>
                    <div className="status-right">
                        <span className="status-item">{savedClock ? `草稿 ${savedClock}` : "自动保存已开启"}</span>
                        <span className="status-item">判题容器随下一迭代接入</span>
                    </div>
                </footer>
            </div>
        </div>
    );
}
