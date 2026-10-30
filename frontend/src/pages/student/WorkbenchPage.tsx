import React, { useEffect, useRef, useState } from "react";
import { useHistory, useParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { findExam, formatCountdown } from "../../mock/exams";
import {
    AgentMessages,
    AgentPlaceholder,
    CannedReplies,
    DefaultModifiedPaths,
    DefaultOpenPaths,
    RemainingSeconds,
    SampleTabNotes,
    SubmissionTabNotes,
    TerminalLines,
    TimelineItems,
    WorkspaceEntries,
    WorkspaceFiles,
    formatClock,
    workspaceFileName,
} from "../../mock/workbench";

type ProblemTabKey = "statement" | "samples" | "submissions";

/** 题目区顶部标签（数量取自原型） */
const ProblemTabs: { key: ProblemTabKey; label: string; count?: number }[] = [
    { key: "statement", label: "题目说明" },
    { key: "samples", label: "样例测试", count: 10 },
    { key: "submissions", label: "提交记录", count: 1 },
];

/** 代码编辑区：原型是静态高亮行，这里换成受控 textarea，保留等宽外观但不引入高亮库 */
const CodeInputStyle: React.CSSProperties = {
    display: "block",
    width: "100%",
    height: "100%",
    margin: 0,
    padding: "0 12px 8px 12px",
    border: "none",
    outline: "none",
    resize: "none",
    background: "transparent",
    whiteSpace: "pre",
    overflow: "auto",
    color: "#334155",
    fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", Menlo, monospace",
    fontSize: 11.5,
    lineHeight: "20px",
};

/** Agent 输入框：原型只是一行占位文案，这里换成可输入的 textarea */
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

/** 文件树目录图标：Icon 组件只画描边，原型这里需要浅黄填充 */
function FolderIcon() {
    return (
        <svg className="folder-ico" width={14} height={14} viewBox="0 0 24 24"
             fill="#fef3c7" stroke="currentColor" strokeWidth={1.6} strokeLinejoin="round">
            <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>
        </svg>
    );
}

/** 把 `反引号` 包住的片段渲染成行内 <code>，与原型里的代码标记一致 */
function renderInlineCode(text: string): React.ReactNode {
    return text.split("`").map((part, index) =>
        index % 2 === 1
            ? <code key={index}>{part}</code>
            : <React.Fragment key={index}>{part}</React.Fragment>
    );
}

/**
 * 04 做题工作台：满屏工作区（文件树 / 题目 / 编辑器 / 终端 / Coding Agent）。
 *
 * 做题页在原型里是独立满屏页面，因此不使用 StudentLayout，直接以 .wb-root 作根节点，
 * 内部类名全部沿用原型（workbench.css 的选择器都限定在 .wb-root 之下）。
 */
export function WorkbenchPage() {
    const { examId } = useParams<{ examId: string }>();
    const history = useHistory();
    const exam = findExam(examId);

    // 倒计时按秒真实递减
    const [seconds, setSeconds] = useState(RemainingSeconds);
    useEffect(() => {
        const timer = window.setInterval(() => {
            setSeconds(current => (current <= 1 ? 0 : current - 1));
        }, 1000);
        return () => window.clearInterval(timer);
    }, []);

    // 工作区：打开的文件标签、当前文件、各文件内容与「未保存」标记
    const [openPaths, setOpenPaths] = useState<string[]>(() => DefaultOpenPaths.slice());
    const [currentPath, setCurrentPath] = useState<string>(DefaultOpenPaths[0]);
    const [contents, setContents] = useState<Record<string, string>>(() => ({ ...WorkspaceFiles }));
    const [modified, setModified] = useState<Record<string, boolean>>(() => ({ ...DefaultModifiedPaths }));
    const [edited, setEdited] = useState(false);

    const [problemTab, setProblemTab] = useState<ProblemTabKey>("statement");
    const [messages, setMessages] = useState(AgentMessages);
    const [draft, setDraft] = useState("");
    const messageSeed = useRef(0);

    const chatRef = useRef<HTMLDivElement>(null);

    // 追加消息后滚动到会话底部（.chat 是 overflow: hidden，可编程滚动）
    useEffect(() => {
        const chat = chatRef.current;
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    }, [messages.length]);

    const currentCode = contents[currentPath] || "";
    const lineCount = currentCode.split("\n").length;

    /** 点击文件树或编辑器标签切换当前文件 */
    const openFile = (path: string) => {
        setOpenPaths(current => (current.indexOf(path) >= 0 ? current : [...current, path]));
        setCurrentPath(path);
    };

    /** 关闭编辑器标签；至少保留一个文件，避免编辑区空白 */
    const closeTab = (path: string) => {
        if (openPaths.length <= 1) {
            return;
        }
        const remaining = openPaths.filter(item => item !== path);
        setOpenPaths(remaining);
        if (currentPath === path) {
            setCurrentPath(remaining[remaining.length - 1]);
        }
    };

    /** 编辑代码：写入内容、打上未保存标记 */
    const handleCodeChange = (value: string) => {
        setContents(current => ({ ...current, [currentPath]: value }));
        setModified(current => ({ ...current, [currentPath]: true }));
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
                variant: "plain",
                time,
                paragraphs: [CannedReplies[seed % CannedReplies.length]],
            },
        ]);
        setDraft("");
    };

    /** 提交判分：二次确认后进入结果页 */
    const handleSubmit = () => {
        const confirmed = window.confirm("确认提交判分？提交后立即判分，本次考试还剩 2 次机会。");
        if (confirmed) {
            history.push(Routes.examResult(examId));
        }
    };

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
                        <div className="exam-name">{exam.title}</div>
                    </div>
                    <div className="topbar-right">
                        <div className="chip chip-ai">
                            <Icon name="shield-check" size={13} strokeWidth={1.9}/>
                            AI 受限模式
                        </div>
                        <div className="chip chip-timer">
                            <Icon name="clock" size={14}/>
                            剩余 {formatCountdown(seconds)}
                        </div>
                        <div className="save-status">
                            <span className="dot" style={edited ? { background: "#f59e0b" } : undefined}/>
                            {edited ? "有未保存修改" : "已自动保存 14:32:05"}
                        </div>
                        <button className="btn-submit" type="button" onClick={handleSubmit}>
                            <Icon name="arrow-up" size={14} strokeWidth={1.9}/>
                            提交判分
                            <span className="sub">剩余 2 次</span>
                        </button>
                        <div className="avatar">李</div>
                    </div>
                </header>

                {/* 考试信息条 */}
                <div className="metabar">
                    <div className="metabar-left">
                        <span className="task-name">任务 1 / 3 · 订单排序修复</span>
                        <span className="meta-chip blue">工程题</span>
                        <span className="meta-chip">Python 3.11</span>
                        <span className="meta-chip green"><span className="status-dot"/>容器运行中</span>
                        <span className="meta-chip">网络已隔离</span>
                    </div>
                    <div className="metabar-right">
                        <span>自动保存已开启</span>
                        <span className="divider-dot">·</span>
                        <span className="link" onClick={() => history.push(Routes.examPrecheck(examId))}>
                            查看考试须知
                        </span>
                    </div>
                </div>

                <div className="main">
                    {/* 左侧：工作区文件树 + 时间线 */}
                    <aside className="sidebar-left">
                        <div className="panel-head">
                            <div className="panel-title">工作区</div>
                            <div className="icon-btn">
                                <Icon name="refresh" size={14}/>
                            </div>
                        </div>
                        <div className="section-label">EXAM-PROJECT</div>
                        <div className="tree">
                            {WorkspaceEntries.map(entry => {
                                const isActive = entry.kind === "file" && entry.path === currentPath;
                                const rowClass = "tree-row " + (entry.depth === 1 ? "root" : "lv" + entry.depth) +
                                    (isActive ? " active" : "");
                                return (
                                    <div key={entry.path}
                                         className={rowClass}
                                         onClick={entry.kind === "file" ? () => openFile(entry.path) : undefined}>
                                        {entry.kind === "folder" && (
                                            <Icon name="chevron-down" size={13} stroke="#64748b" strokeWidth={2}/>
                                        )}
                                        {entry.kind === "folder"
                                            ? <FolderIcon/>
                                            : <Icon name="file" size={13} strokeWidth={1.7} className="file-ico"/>}
                                        <span>{entry.name}</span>
                                        {entry.kind === "file" && modified[entry.path] && <span className="modified-dot"/>}
                                    </div>
                                );
                            })}
                        </div>

                        <div className="left-bottom">
                            <div className="timeline-head">
                                <div className="timeline-title">时间线</div>
                                <div className="timeline-link" onClick={() => history.push(Routes.examReport(examId))}>
                                    查看全部
                                </div>
                            </div>
                            {TimelineItems.map(item => (
                                <div className="timeline-item" key={item.text}>
                                    <span className={"tl-dot" + (item.tone ? " " + item.tone : "")}/>
                                    <div>
                                        <div className="tl-text">{item.text}</div>
                                        <div className="tl-time">{item.time}</div>
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
                                        {tab.count != null && <span className="tab-count">{tab.count}</span>}
                                    </div>
                                ))}
                                <div className="tabs-right">当前任务 1 / 3</div>
                            </div>

                            {problemTab === "statement" && (
                                <div className="problem-body">
                                    <div className="problem-title-row">
                                        <div className="problem-title">任务 1：修复订单排序并补充测试</div>
                                        <div className="badges">
                                            <span className="badge gray">中等</span>
                                            <span className="badge blue">40 分</span>
                                            <span className="badge green">必过 8 / 10</span>
                                        </div>
                                    </div>
                                    <p className="problem-desc">
                                        订单服务从 CSV 导入订单后按金额排序展示。当前金额相同的订单顺序不稳定，部分时间格式也无法解析。
                                        请修复 <code>src/buggy_sort.py</code>，并在 <code>tests/test_sort.py</code> 中补充边界用例。
                                    </p>
                                    <p className="rule-line">
                                        <span className="label">验收：</span>金额相同按 <code>created_at</code> 升序；兼容 ISO 与空格两种时间格式；样例测试全部通过；不得修改 <code>tests/conftest.py</code>。
                                    </p>
                                    <div className="ai-note">
                                        <Icon name="sparkles" size={13}/>
                                        <span><strong>AI 使用策略：受限模式</strong> · 可解释与运行测试，不可直接写入代码。对话、采纳/拒绝与运行记录将计入过程报告。</span>
                                    </div>
                                </div>
                            )}

                            {/* 原型只展开「题目说明」，另外两个标签给只读摘要，保证切换有实际反馈 */}
                            {problemTab === "samples" && (
                                <div className="problem-body">
                                    {SampleTabNotes.map(note => (
                                        <p className="rule-line" key={note.label}>
                                            <span className="label">{note.label}</span>{note.text}
                                        </p>
                                    ))}
                                </div>
                            )}

                            {problemTab === "submissions" && (
                                <div className="problem-body">
                                    {SubmissionTabNotes.map(note => (
                                        <p className="rule-line" key={note.label}>
                                            <span className="label">{note.label}</span>{note.text}
                                        </p>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="editor">
                            <div className="editor-tabs">
                                {openPaths.map(path => {
                                    const active = path === currentPath;
                                    return (
                                        <div key={path}
                                             className={"editor-tab" + (active ? " active" : "")}
                                             onClick={() => setCurrentPath(path)}>
                                            <Icon name="file" size={12} stroke={active ? "#2563eb" : "#94a3b8"}/>
                                            {workspaceFileName(path)}
                                            {modified[path] && <span className="modified-dot"/>}
                                            <span className="close"
                                                  onClick={event => {
                                                      event.stopPropagation();
                                                      closeTab(path);
                                                  }}>×</span>
                                        </div>
                                    );
                                })}
                                <div className="editor-actions">
                                    <span>Python 3.11</span>
                                    <span className="ok">● 自动保存已开启</span>
                                </div>
                            </div>
                            <div className="editor-body">
                                <div className="gutter">
                                    {Array.from({ length: lineCount }, (_unused, index) => (
                                        <div key={index}>{index + 1}</div>
                                    ))}
                                </div>
                                <div className="code-area">
                                    <textarea style={CodeInputStyle}
                                              value={currentCode}
                                              spellCheck={false}
                                              wrap="off"
                                              onChange={event => handleCodeChange(event.target.value)}/>
                                </div>
                            </div>
                        </div>

                        <div className="terminal">
                            <div className="terminal-head">
                                <div className="terminal-title">
                                    <Icon name="terminal" size={13} stroke="#475569"/>
                                    终端
                                </div>
                                <div className="terminal-tab active">测试</div>
                                <div className="terminal-tab">输出</div>
                                <div className="terminal-tab">问题</div>
                                <div className="terminal-tab terminal-clear">清屏</div>
                            </div>
                            <div className="terminal-body">
                                {TerminalLines.map((line, lineIndex) => (
                                    <div className="term-line" key={lineIndex}>
                                        {line.map((segment, index) => (
                                            <span key={index}
                                                  className={segment.tone ? "term-" + segment.tone : undefined}>
                                                {segment.text}
                                            </span>
                                        ))}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>

                    {/* 右侧：Coding Agent */}
                    <aside className="agent">
                        <div className="agent-head">
                            <div className="agent-brand">
                                <div className="agent-logo">
                                    <Icon name="sparkles" size={15}/>
                                </div>
                                <div>
                                    <div className="agent-name">Coding Agent</div>
                                    <div className="agent-sub">对话与操作全程留痕</div>
                                </div>
                            </div>
                            <div className="agent-head-actions">
                                <span className="mode-chip">
                                    <Icon name="lock" size={10} strokeWidth={2}/>
                                    受限
                                </span>
                                <div className="icon-btn">
                                    <Icon name="history" size={14}/>
                                </div>
                                <div className="icon-btn">
                                    <Icon name="more-horizontal" size={14} strokeWidth={2}/>
                                </div>
                            </div>
                        </div>

                        <div className="context-bar">
                            <span className="ctx-label">上下文</span>
                            <span className="ctx-chip">
                                <Icon name="file" size={10}/>
                                {currentPath}
                            </span>
                            <span className="ctx-add">+ 添加</span>
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
                                        {message.paragraphs.map((paragraph, index) => (
                                            <p key={index}>{renderInlineCode(paragraph)}</p>
                                        ))}
                                        {message.variant === "diff" && (
                                            <div className="diff-box">
                                                <span className="diff-del">- key=lambda o: o.amount</span>
                                                <span className="diff-add">+ key=lambda o: (o.amount, parse_time(o.created_at))</span>
                                            </div>
                                        )}
                                        {message.variant === "code" && (
                                            <div className="code-box">{message.code}</div>
                                        )}
                                        {message.variant === "diff" && (
                                            <div className="card-actions">
                                                <span className="btn-mini primary">
                                                    <Icon name="copy" size={10} strokeWidth={1.9}/>
                                                    复制建议
                                                </span>
                                                <span className="btn-mini">查看相关文件</span>
                                                <span className="btn-mini disabled">
                                                    <Icon name="lock" size={10} strokeWidth={2}/>
                                                    应用到编辑器
                                                </span>
                                            </div>
                                        )}
                                        {message.variant === "diff" && (
                                            <div className="card-foot">
                                                <Icon name="shield" size={10} strokeWidth={2}/>
                                                受限模式：仅提供解释与建议，不会直接写入代码
                                            </div>
                                        )}
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
                                        <Icon name="at-sign" size={14}/>
                                        <Icon name="paperclip" size={14}/>
                                        <span className="input-hint">Enter 发送 · Shift+Enter 换行</span>
                                    </div>
                                    <button className="send-btn" type="button" onClick={handleSend}>
                                        <Icon name="send" size={14} strokeWidth={1.9}/>
                                    </button>
                                </div>
                            </div>
                            <div className="agent-foot">
                                <Icon name="lock" size={10} strokeWidth={2}/>
                                受限模式 · 对话将随试卷冻结，并计入过程评分
                            </div>
                        </div>
                    </aside>
                </div>

                {/* 底部状态栏 */}
                <footer className="statusbar">
                    <div className="status-left">
                        <span className="status-item"><span className="status-dot"/>容器正常</span>
                        <span className="status-item">CPU 12%</span>
                        <span className="status-item">内存 1.2 / 4 GB</span>
                    </div>
                    <div className="status-right">
                        <span className="status-item">快照 #18 · 14:32:05</span>
                        <span className="status-item">网络隔离已开启</span>
                        <span className="status-item">自动保存 30s</span>
                    </div>
                </footer>
            </div>
        </div>
    );
}
