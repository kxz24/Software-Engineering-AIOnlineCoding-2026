import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useSelector } from "react-redux";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { CodeEditor } from "../../components/CodeEditor";
import { toast } from "../../components/Toast";
import { Store } from "../../store";
import { Routes } from "../../api/urls";
import { formatDateTime } from "../../api/format";
import { ApiError } from "../../api/client";
import { verdictMeta } from "../../api/judge";
import {
    PracticeComment,
    PracticeProblemDetail,
    PracticeSubmission,
    createPracticeComment,
    deletePracticeComment,
    fetchPracticeComments,
    fetchPracticeProblem,
    fetchPracticeSubmission,
    submitPracticeCode,
} from "../../api/practice";

const DifficultyLabels: Record<string, string> = {
    easy: "简单",
    medium: "中等",
    hard: "困难",
};

const LanguageLabels: Record<string, string> = {
    python: "Python",
    cpp: "C++",
    c: "C",
    java: "Java",
};

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

const CodeBlockStyle: React.CSSProperties = {
    margin: "6px 0 0",
    maxHeight: 260,
    overflow: "auto",
    padding: "8px 10px",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    fontFamily: "\"SFMono-Regular\", Consolas, Menlo, monospace",
    fontSize: 10.5,
    lineHeight: 1.55,
    whiteSpace: "pre",
};

function isPendingSubmission(status: string): boolean {
    return status === "pending" || status === "judging";
}

/**
 * 学生自由练习页：读题、写代码、提交判题、参与评论讨论。
 * 判题结果由后端 Celery + Docker 沙箱异步返回，页面轮询提交状态。
 */
export function PracticePage() {
    const { problemId } = useParams<{ problemId: string }>();
    const numericId = Number(problemId);
    const user = useSelector((s: Store) => s.user);

    const [problem, setProblem] = useState<PracticeProblemDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [code, setCode] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [submission, setSubmission] = useState<PracticeSubmission | null>(null);
    const [submitError, setSubmitError] = useState<string | null>(null);

    const [comments, setComments] = useState<PracticeComment[]>([]);
    const [commentText, setCommentText] = useState("");
    const [attachCode, setAttachCode] = useState(false);
    const [commentCode, setCommentCode] = useState("");
    const [commentLanguage, setCommentLanguage] = useState("python");
    const [posting, setPosting] = useState(false);
    const [commentError, setCommentError] = useState<string | null>(null);
    const [replyTo, setReplyTo] = useState<PracticeComment | null>(null);
    const commentFormRef = useRef<HTMLDivElement>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        setSubmission(null);
        setSubmitError(null);
        setCommentText("");
        setCommentCode("");
        setAttachCode(false);
        setCommentError(null);
        setReplyTo(null);
        fetchPracticeProblem(numericId)
            .then(detail => {
                setProblem(detail);
                setCode(detail.starterCode || "");
                setCommentLanguage(detail.language);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [numericId]);
    useEffect(() => {
        if (!problem) {
            return;
        }
        fetchPracticeComments(problem.id)
            .then(result => setComments(result.comments))
            .catch(() => {
                // 评论区加载失败不阻塞做题
            });
    }, [problem?.id]);

    // 等待判题结果：pending / judging 时每 1.5 秒轮询一次
    const inFlight = !!submission && isPendingSubmission(submission.status);
    useEffect(() => {
        if (!inFlight || !submission) {
            return;
        }
        const timer = window.setInterval(() => {
            fetchPracticeSubmission(submission.id)
                .then(result => setSubmission(result.submission))
                .catch(() => {
                    // 网络抖动不打断页面
                });
        }, 1500);
        return () => window.clearInterval(timer);
    }, [inFlight, submission?.id]);

    const handleSubmit = () => {
        if (!problem || !code.trim() || submitting) {
            return;
        }
        setSubmitting(true);
        setSubmitError(null);
        submitPracticeCode(problem.id, code, problem.language)
            .then(result => {
                setSubmission(result.submission);
                toast("已提交，正在判题", "success");
            })
            .catch((e: ApiError) => setSubmitError(e.message))
            .finally(() => setSubmitting(false));
    };

    const handlePostComment = () => {
        if (!problem || posting) {
            return;
        }
        if (!commentText.trim() && !(attachCode && commentCode.trim())) {
            setCommentError("请填写讨论内容，或勾选并填写附带的代码。");
            return;
        }
        setPosting(true);
        setCommentError(null);
        createPracticeComment(problem.id, {
            content: commentText.trim(),
            code: attachCode ? commentCode : "",
            language: commentLanguage,
            parentId: replyTo ? replyTo.id : undefined,
        })
            .then(result => {
                setComments(current => [result.comment, ...current]);
                setCommentText("");
                setAttachCode(false);
                setCommentCode("");
                setReplyTo(null);
                toast(replyTo ? "回复已发布" : "评论已发布", "success");
            })
            .catch((e: ApiError) => setCommentError(e.message))
            .finally(() => setPosting(false));
    };

    const handleDeleteComment = (comment: PracticeComment) => {
        if (!window.confirm("确认删除这条评论？")) {
            return;
        }
        deletePracticeComment(comment.id)
            .then(() => {
                setComments(current => current.filter(item =>
                    item.id !== comment.id && item.parentId !== comment.id));
                toast("评论已删除", "success");
            })
            .catch((e: ApiError) => toast(e.message, "warning"));
    };

    const sampleItems = useMemo(() => problem?.samples || [], [problem]);

    const topComments = useMemo(
        () => comments.filter(comment => !comment.parentId),
        [comments]
    );
    const repliesByParent = useMemo(() => {
        const map = new Map<number, PracticeComment[]>();
        comments.forEach(comment => {
            if (comment.parentId) {
                const list = map.get(comment.parentId) || [];
                list.push(comment);
                map.set(comment.parentId, list);
            }
        });
        map.forEach(list => list.sort((a, b) => a.created.localeCompare(b.created)));
        return map;
    }, [comments]);

    const startReply = (comment: PracticeComment) => {
        setReplyTo(comment);
        setCommentError(null);
        window.setTimeout(() => {
            commentFormRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 0);
    };

    const renderComment = (comment: PracticeComment, isReply = false) => (
        <div key={comment.id}
             style={{
                 borderTop: "1px solid #eef2f7",
                 padding: "10px 0",
                 marginLeft: isReply ? 24 : 0,
                 borderLeft: isReply ? "2px solid #e2e8f0" : undefined,
                 paddingLeft: isReply ? 10 : 0,
             }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div className="mini-avatar">{comment.nickname.slice(0, 1)}</div>
                <span className="strong" style={{ fontSize: 11.5 }}>
                    {comment.nickname}
                </span>
                <span className="muted" style={{ fontSize: 10 }}>
                    {comment.username} · {formatDateTime(comment.created)}
                </span>
                <span className="link"
                      style={{ marginLeft: "auto", fontSize: 10 }}
                      onClick={() => startReply(comment)}>
                    回复
                </span>
                {user && user.username === comment.username && (
                    <span className="link"
                          style={{ fontSize: 10, color: "#dc2626" }}
                          onClick={() => handleDeleteComment(comment)}>
                        删除
                    </span>
                )}
            </div>
            {isReply && comment.parentId && (
                <div className="muted" style={{ fontSize: 10, marginTop: 3 }}>
                    回复 @{comments.find(item => item.id === comment.parentId)?.nickname || "该评论"}
                </div>
            )}
            {comment.content && (
                <div style={{ whiteSpace: "pre-wrap", fontSize: 11.5, lineHeight: 1.65, color: "#334155", marginTop: 6 }}>
                    {comment.content}
                </div>
            )}
            {comment.code && (
                <div style={{ marginTop: 6 }}>
                    <span className="badge gray" style={{ marginBottom: 4 }}>
                        代码 · {LanguageLabels[comment.language] || comment.language}
                    </span>
                    <pre style={CodeBlockStyle}>{comment.code}</pre>
                </div>
            )}
        </div>
    );

    if (loading) {
        return <StudentLayout active="practice">
            <div className="card"><div className="card-body muted">加载中…</div></div>
        </StudentLayout>;
    }

    if (error || !problem) {
        return (
            <StudentLayout active="practice">
                <div className="card" style={{ borderColor: "#fecaca" }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error || "题目不存在"}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                        <Link className="link" style={{ marginLeft: 10 }} to={Routes.practice}>返回题目列表</Link>
                    </div>
                </div>
            </StudentLayout>
        );
    }

    return (
        <StudentLayout active="practice">
            <div className="page-head">
                <div>
                    <div className="page-title">{problem.title}</div>
                    <div className="page-sub">
                        自由练习 · {DifficultyLabels[problem.difficulty] || problem.difficulty}
                        {" · "}{LanguageLabels[problem.language] || problem.language}
                        {" · "}单用例限时 {problem.timeLimitMs} ms
                    </div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.practice}>
                        <Icon name="arrow-left" size={14}/>返回题目列表
                    </Link>
                </div>
            </div>

            <div className="practice-grid">
                <div className="card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">题目说明</div>
                            <div className="card-sub">
                                公开样例 {problem.sampleCount} 个 · 共 {problem.testCount} 个测试用例
                            </div>
                        </div>
                        <span className="badge blue">练习不计分</span>
                    </div>
                    <div className="card-body">
                        <div style={{ whiteSpace: "pre-wrap", fontSize: 12, lineHeight: 1.7, color: "#475569" }}>
                            {problem.description || "（本题没有题面）"}
                        </div>
                        <div className="card-head" style={{ padding: "14px 0 8px" }}>
                            <div className="card-title" style={{ fontSize: 12.5 }}>公开样例</div>
                        </div>
                        {sampleItems.length === 0 && (
                            <div className="muted" style={{ fontSize: 11.5 }}>本题没有公开样例</div>
                        )}
                        {sampleItems.map(sample => (
                            <div key={sample.name} style={{ marginBottom: 12 }}>
                                <div className="muted" style={{ fontSize: 10.5, marginBottom: 4 }}>{sample.name}</div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                                    <div>
                                        <div className="muted" style={{ fontSize: 10, marginBottom: 3 }}>输入</div>
                                        <pre style={SampleBoxStyle}>{sample.input}</pre>
                                    </div>
                                    <div>
                                        <div className="muted" style={{ fontSize: 10, marginBottom: 3 }}>期望输出</div>
                                        <pre style={SampleBoxStyle}>{sample.expected}</pre>
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div className="muted" style={{ fontSize: 10.5, marginTop: 6 }}>
                            隐藏用例不会展示输入输出，提交后只反馈通过情况。
                        </div>
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
                    <div className="card">
                        <div className="card-head">
                            <div>
                                <div className="card-title">你的代码</div>
                                <div className="card-sub">{LanguageLabels[problem.language] || problem.language}</div>
                            </div>
                            <span className="badge gray">Ctrl+S 不影响提交</span>
                        </div>
                        <div className="practice-editor" style={{ height: 380 }}>
                            <CodeEditor path={`practice-${problem.id}.${problem.language}`}
                                        initialValue={code}
                                        language={problem.language}
                                        onChange={(_path, value) => setCode(value)}/>
                        </div>
                        <div className="card-body" style={{ paddingTop: 10, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <span className="muted" style={{ fontSize: 10.5 }}>
                                提交后使用判题沙箱运行全部测试用例
                            </span>
                            <button type="button" className="btn btn-primary"
                                    disabled={submitting || !code.trim()}
                                    onClick={handleSubmit}>
                                <Icon name="send" size={13}/>{submitting ? "提交中…" : "提交判题"}
                            </button>
                        </div>
                    </div>

                    {submitError && (
                        <div className="card" style={{ borderColor: "#fecaca" }}>
                            <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                                <Icon name="alert-triangle" size={13}/> {submitError}
                            </div>
                        </div>
                    )}

                    {submission && (
                        <div className="card">
                            <div className="card-head">
                                <div>
                                    <div className="card-title">判题结果</div>
                                    <div className="card-sub">
                                        提交 #{submission.id} · {formatDateTime(submission.created)}
                                    </div>
                                </div>
                                <span className={"badge " + (isPendingSubmission(submission.status) ? "amber" : verdictMeta(submission.verdict).tone)}>
                                    {isPendingSubmission(submission.status)
                                        ? (submission.status === "judging" ? "判题中" : "排队中")
                                        : verdictMeta(submission.verdict).label}
                                </span>
                            </div>
                            <div className="card-body">
                                {submission.status === "failed" && (
                                    <div className="muted" style={{ color: "#b91c1c", whiteSpace: "pre-wrap", fontSize: 11 }}>
                                        {submission.judgeError || "判题失败，请稍后重试"}
                                    </div>
                                )}
                                {!isPendingSubmission(submission.status) && submission.totalCount > 0 && (
                                    <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>
                                        通过 {submission.passedCount}/{submission.totalCount}
                                        {" · "}样例 {submission.samplePassed}/{submission.sampleTotal}
                                        {" · "}隐藏 {submission.hiddenPassed}/{submission.hiddenTotal}
                                        {" · "}最大耗时 {submission.timeMs} ms
                                    </div>
                                )}
                                {submission.compileOutput && (
                                    <pre style={{ ...CodeBlockStyle, color: "#b91c1c" }}>{submission.compileOutput}</pre>
                                )}
                                {submission.results.map(item => (
                                    <div key={item.index} style={{ marginBottom: 8 }}>
                                        <div className={"badge " + verdictMeta(item.verdict).tone}>
                                            {verdictMeta(item.verdict).label}
                                        </div>
                                        <span style={{ marginLeft: 6, fontSize: 11.5 }}>{item.name}</span>
                                        <span className="muted" style={{ marginLeft: 6, fontSize: 10 }}>
                                            {item.timeMs} ms
                                        </span>
                                        {item.isSample && (item.outputExcerpt || item.errorExcerpt) && (
                                            <pre style={{ ...CodeBlockStyle, marginTop: 4 }}>
                                                {item.errorExcerpt || item.outputExcerpt}
                                            </pre>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 评论区 */}
            <div className="card" style={{ marginTop: 14 }}>
                <div className="card-head">
                    <div>
                        <div className="card-title">题目讨论</div>
                        <div className="card-sub">{comments.length} 条评论 · 可以讨论思路并附上代码</div>
                    </div>
                </div>
                <div className="card-body">
                    <div ref={commentFormRef}
                         style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 10, marginBottom: 14 }}>
                        {replyTo && (
                            <div className="muted"
                                 style={{ fontSize: 11, marginBottom: 6, display: "flex", alignItems: "center", gap: 8 }}>
                                <span>正在回复 @{replyTo.nickname}</span>
                                <span className="link" style={{ fontSize: 10 }}
                                      onClick={() => setReplyTo(null)}>取消回复</span>
                            </div>
                        )}
                        <textarea className="input"
                                  style={{ minHeight: 76, fontSize: 11.5, lineHeight: 1.55 }}
                                  placeholder={replyTo
                                      ? `回复 @${replyTo.nickname}：写下你的回复…`
                                      : "说说你的思路、遇到的问题，或回答其他同学…"}
                                  value={commentText}
                                  onChange={event => setCommentText(event.target.value)}/>
                        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
                            <label className="muted" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 5 }}>
                                <input type="checkbox" checked={attachCode}
                                       onChange={event => {
                                           setAttachCode(event.target.checked);
                                           if (event.target.checked && !commentCode) {
                                               setCommentCode(code);
                                           }
                                       }}/>
                                附上代码
                            </label>
                            {attachCode && (
                                <select className="select"
                                        style={{ height: 26, fontSize: 10.5 }}
                                        value={commentLanguage}
                                        onChange={event => setCommentLanguage(event.target.value)}>
                                    {Object.keys(LanguageLabels).map(key => (
                                        <option key={key} value={key}>{LanguageLabels[key]}</option>
                                    ))}
                                </select>
                            )}
                            <button type="button" className="btn btn-primary btn-sm"
                                    style={{ marginLeft: "auto" }}
                                    disabled={posting}
                                    onClick={handlePostComment}>
                                <Icon name="send" size={12}/>{posting ? "发布中…" : (replyTo ? "发布回复" : "发布讨论")}
                            </button>
                        </div>
                        {attachCode && (
                            <textarea className="input"
                                      style={{ ...CodeBlockStyle, width: "100%", minHeight: 100, marginTop: 8 }}
                                      value={commentCode}
                                      placeholder="粘贴与题目相关的代码…"
                                      onChange={event => setCommentCode(event.target.value)}/>
                        )}
                        {commentError && (
                            <div style={{ color: "#b91c1c", fontSize: 11, marginTop: 6 }}>{commentError}</div>
                        )}
                    </div>

                    {topComments.length === 0 && (
                        <div className="muted" style={{ fontSize: 11.5 }}>还没有讨论，来发第一条吧。</div>
                    )}
                    {topComments.map(comment => (
                        <div key={comment.id}>
                            {renderComment(comment)}
                            {(repliesByParent.get(comment.id) || []).map(reply => renderComment(reply, true))}
                        </div>
                    ))}
                </div>
            </div>
        </StudentLayout>
    );
}
