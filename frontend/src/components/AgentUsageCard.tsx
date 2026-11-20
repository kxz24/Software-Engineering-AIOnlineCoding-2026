import React, { useEffect, useMemo, useState } from "react";
import { Icon } from "./Icon";
import { ApiError } from "../api/client";
import {
    AgentSessionListItem,
    AgentTranscript,
    fetchAgentExamSessions,
    fetchAgentTranscript,
} from "../api/agent";

/** 教师端「AI 使用」卡片：按学生汇总 token，点开看对话与 AI 修改记录。 */

interface StudentRow {
    username: string;
    nickname: string;
    sessions: AgentSessionListItem[];
    inputTokens: number;
    outputTokens: number;
    cacheHitTokens: number;
    messageCount: number;
    changeCount: number;
    lastActiveAt: string | null;
}

const OverlayStyle: React.CSSProperties = {
    position: "fixed",
    inset: 0,
    background: "rgba(15, 23, 42, 0.45)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1200,
    padding: 24,
};

const ModalStyle: React.CSSProperties = {
    width: "min(1080px, 100%)",
    height: "min(760px, 100%)",
    background: "#ffffff",
    borderRadius: 10,
    boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
};

const BubbleUserStyle: React.CSSProperties = {
    alignSelf: "flex-end",
    maxWidth: "88%",
    background: "#eff6ff",
    color: "#1e3a8a",
    border: "1px solid #dbeafe",
    borderRadius: "10px 10px 3px 10px",
    padding: "7px 10px",
    fontSize: 11.5,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    marginBottom: 9,
};

const BubbleAiStyle: React.CSSProperties = {
    background: "#fbfbfe",
    border: "1px solid #ede9fe",
    borderRadius: 9,
    padding: "8px 10px",
    fontSize: 11.5,
    lineHeight: 1.6,
    color: "#334155",
    whiteSpace: "pre-wrap",
    marginBottom: 9,
};

const ToolRowStyle: React.CSSProperties = {
    fontSize: 10.5,
    color: "#64748b",
    background: "#f8fafc",
    borderLeft: "2px solid #ddd6fe",
    padding: "4px 8px",
    marginBottom: 9,
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
};

const DiffStyle: React.CSSProperties = {
    margin: "4px 0 10px",
    maxHeight: 220,
    overflow: "auto",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    padding: "6px 8px",
    fontFamily: "\"SFMono-Regular\", Consolas, Menlo, monospace",
    fontSize: 9.5,
    lineHeight: 1.5,
    whiteSpace: "pre",
    color: "#334155",
};

function formatTime(iso: string | null): string {
    if (!iso) {
        return "—";
    }
    const date = new Date(iso);
    return isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

export function AgentUsageCard({ examId, candidates = [] }: {
    examId: number;
    /** 名单内的考生账号；用于把未使用 AI 的同学也列出来（0 token） */
    candidates?: string[];
}) {
    const [sessions, setSessions] = useState<AgentSessionListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [student, setStudent] = useState<StudentRow | null>(null);
    const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
    const [transcript, setTranscript] = useState<AgentTranscript | null>(null);
    const [transcriptLoading, setTranscriptLoading] = useState(false);
    const [transcriptError, setTranscriptError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchAgentExamSessions(examId)
            .then(result => {
                setSessions(result.sessions);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [examId]);

    const rows = useMemo(() => {
        const map = new Map<string, StudentRow>();
        sessions.forEach(session => {
            const row = map.get(session.student) || {
                username: session.student,
                nickname: session.nickname || session.student,
                sessions: [],
                inputTokens: 0,
                outputTokens: 0,
                cacheHitTokens: 0,
                messageCount: 0,
                changeCount: 0,
                lastActiveAt: null,
            };
            row.sessions.push(session);
            row.inputTokens += session.inputTokens;
            row.outputTokens += session.outputTokens;
            row.cacheHitTokens += session.cacheHitTokens;
            row.messageCount += session.messageCount;
            row.changeCount += session.changeCount;
            if (session.lastActiveAt && (!row.lastActiveAt || session.lastActiveAt > row.lastActiveAt)) {
                row.lastActiveAt = session.lastActiveAt;
            }
            map.set(session.student, row);
        });
        candidates.forEach(username => {
            if (!map.has(username)) {
                map.set(username, {
                    username,
                    nickname: username,
                    sessions: [],
                    inputTokens: 0,
                    outputTokens: 0,
                    cacheHitTokens: 0,
                    messageCount: 0,
                    changeCount: 0,
                    lastActiveAt: null,
                });
            }
        });
        return Array.from(map.values()).sort((a, b) => {
            const diff = (b.inputTokens + b.outputTokens) - (a.inputTokens + a.outputTokens);
            return diff !== 0 ? diff : a.username.localeCompare(b.username);
        });
    }, [sessions, candidates]);

    const loadTranscript = (sessionId: number) => {
        setActiveSessionId(sessionId);
        setTranscript(null);
        setTranscriptLoading(true);
        setTranscriptError(null);
        fetchAgentTranscript(sessionId)
            .then(setTranscript)
            .catch((e: ApiError) => setTranscriptError(e.message))
            .finally(() => setTranscriptLoading(false));
    };

    const openStudent = (row: StudentRow) => {
        setStudent(row);
        setTranscript(null);
        if (row.sessions.length > 0) {
            loadTranscript(row.sessions[0].sessionId);
        }
    };

    const close = () => {
        setStudent(null);
        setTranscript(null);
        setActiveSessionId(null);
        setTranscriptError(null);
    };

    const totalTokens = rows.reduce((sum, row) => sum + row.inputTokens + row.outputTokens, 0);

    return (
        <>
            <div className="card">
                <div className="card-head">
                    <div>
                        <div className="card-title">AI 使用</div>
                        <div className="card-sub">token 用量、对话记录与 AI 代码修改</div>
                    </div>
                    <div className="table-tools">
                        <span className="badge blue">
                            {rows.length} 人 · {sessions.length} 会话 · {totalTokens.toLocaleString()} tokens
                        </span>
                        <span className="btn btn-secondary btn-sm" onClick={load}>
                            <Icon name="refresh" size={12}/>刷新
                        </span>
                    </div>
                </div>
                <div className="card-body" style={{ maxHeight: 340, overflowY: "auto" }}>
                    {loading && <div className="muted" style={{ fontSize: 11.5 }}>加载中…</div>}
                    {error && !loading && (
                        <div className="muted" style={{ fontSize: 11.5 }}>
                            {error}
                            <span className="link" style={{ marginLeft: 8 }} onClick={load}>重试</span>
                        </div>
                    )}
                    {!loading && !error && rows.length === 0 && (
                        <div className="muted" style={{ fontSize: 11.5 }}>本场考试还没有 AI 使用记录</div>
                    )}
                    {rows.map(row => (
                        <div className="log-item" key={row.username}
                             style={{ alignItems: "flex-start" }}>
                            <span className="log-dot green"/>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div className="log-text">
                                    <strong>{row.nickname}</strong>（{row.username}） · {row.sessions.length} 个会话
                                </div>
                                <div className="log-sub">
                                    token {(row.inputTokens + row.outputTokens).toLocaleString()}
                                    （入 {row.inputTokens.toLocaleString()} / 出 {row.outputTokens.toLocaleString()}）
                                    · 消息 {row.messageCount} · AI 修改 {row.changeCount} 次
                                    · 缓存命中 {row.cacheHitTokens.toLocaleString()}
                                </div>
                                <div className="log-sub" style={{ whiteSpace: "normal", marginTop: 2 }}>
                                    {row.sessions.length === 0 && (
                                        <span className="muted">本场未使用 AI</span>
                                    )}
                                    {row.sessions.slice(0, 4).map(session => (
                                        <span key={session.sessionId}
                                              className="link"
                                              style={{ marginRight: 10, fontSize: 10.5 }}
                                              onClick={() => {
                                                  setStudent(row);
                                                  setTranscript(null);
                                                  loadTranscript(session.sessionId);
                                              }}>
                                            {session.problemTitle}（{session.inputTokens + session.outputTokens} token）
                                        </span>
                                    ))}
                                </div>
                            </div>
                            {row.sessions.length > 0 ? (
                                <span className="link" style={{ whiteSpace: "nowrap" }}
                                      onClick={() => openStudent(row)}>
                                    查看记录
                                </span>
                            ) : (
                                <span className="muted" style={{ whiteSpace: "nowrap", fontSize: 10.5 }}>
                                    未使用
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {student && (
                <div style={OverlayStyle} onClick={close}>
                    <div style={ModalStyle} onClick={event => event.stopPropagation()}>
                        <div className="card-head" style={{ flexShrink: 0 }}>
                            <div>
                                <div className="card-title">
                                    AI 记录 · {student.nickname}（{student.username}）
                                </div>
                                <div className="card-sub">
                                    {transcript
                                        ? `${transcript.session.problemTitle} · ${transcript.session.levelLabel} · 输入 ${transcript.session.inputTokens} / 输出 ${transcript.session.outputTokens} tokens · 缓存命中 ${transcript.session.cacheHitTokens}`
                                        : "加载中…"}
                                </div>
                            </div>
                            <div className="table-tools" style={{ flexWrap: "wrap" }}>
                                {student.sessions.map(session => (
                                    <span key={session.sessionId}
                                          className={"badge " + (activeSessionId === session.sessionId ? "blue" : "gray")}
                                          style={{ cursor: "pointer" }}
                                          onClick={() => loadTranscript(session.sessionId)}>
                                        {session.problemTitle}
                                    </span>
                                ))}
                                <span className="btn btn-secondary btn-sm" onClick={close}>关闭</span>
                            </div>
                        </div>
                        <div style={{
                            display: "grid",
                            gridTemplateColumns: "minmax(0, 1fr) 330px",
                            gap: 14,
                            padding: 14,
                            flex: 1,
                            minHeight: 0,
                        }}>
                            <div style={{ overflowY: "auto", minHeight: 0, display: "flex", flexDirection: "column" }}>
                                {transcriptLoading && (
                                    <div className="muted" style={{ fontSize: 11.5 }}>加载对话…</div>
                                )}
                                {transcriptError && (
                                    <div className="muted" style={{ fontSize: 11.5, color: "#b91c1c" }}>
                                        {transcriptError}
                                    </div>
                                )}
                                {transcript && transcript.messages.length === 0 && (
                                    <div className="muted" style={{ fontSize: 11.5 }}>该会话没有消息</div>
                                )}
                                {transcript && transcript.messages.map(message => {
                                    if (message.role === "user") {
                                        return (
                                            <div key={message.seq} style={BubbleUserStyle}>
                                                {message.content}
                                            </div>
                                        );
                                    }
                                    if (message.role === "assistant") {
                                        return (
                                            <div key={message.seq} style={BubbleAiStyle}>
                                                <div style={{ fontSize: 9.5, color: "#6d28d9", marginBottom: 3 }}>
                                                    AI · {formatTime(message.created)}
                                                    {message.outputTokens > 0 && ` · 输出 ${message.outputTokens} tokens`}
                                                </div>
                                                {message.content || "（本轮仅调用工具）"}
                                            </div>
                                        );
                                    }
                                    if (message.role === "tool") {
                                        return (
                                            <div key={message.seq} style={ToolRowStyle}>
                                                工具 · {message.name || "tool"}
                                                <div style={{ marginTop: 2 }}>
                                                    {(message.content || "").slice(0, 1200)}
                                                    {(message.content || "").length > 1200 ? "…（已截断）" : ""}
                                                </div>
                                            </div>
                                        );
                                    }
                                    return null;
                                })}
                            </div>
                            <div style={{ overflowY: "auto", minHeight: 0 }}>
                                <div className="card-title" style={{ fontSize: 12, marginBottom: 8 }}>
                                    AI 代码修改
                                    <span className="badge blue" style={{ marginLeft: 6 }}>
                                        {transcript ? transcript.changes.length : 0}
                                    </span>
                                </div>
                                {transcript && transcript.changes.length === 0 && (
                                    <div className="muted" style={{ fontSize: 11 }}>本次会话没有修改代码</div>
                                )}
                                {transcript && transcript.changes.map(change => (
                                    <div key={change.changeId}
                                         style={{ border: "1px solid #e2e8f0", borderRadius: 7, padding: 8, marginBottom: 8 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                                            <span className={"badge " + (change.status === "applied" ? "green" : "gray")}>
                                                {change.status === "applied" ? "已应用" : "已撤销"}
                                            </span>
                                            <span style={{ fontSize: 10.5, fontWeight: 600 }}>
                                                {change.path}
                                            </span>
                                            <span className="muted" style={{ fontSize: 9.5 }}>
                                                v{change.revisionBefore} → v{change.revisionAfter}
                                            </span>
                                        </div>
                                        <pre style={DiffStyle}>{change.diff || "（无差异）"}</pre>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
