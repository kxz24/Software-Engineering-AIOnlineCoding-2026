import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { formatDateTime } from "../../api/format";
import {
    ApiError,
    fetchMyExam,
    fetchMyExamSubmissions,
    fetchSubmission,
    MySubmission,
    StudentExamDetail,
    SubmissionDetail,
} from "../../api/client";
import { isPending, submissionLabel, verdictMeta } from "../../api/judge";

/** 代码正文展示块 */
const CodeBoxStyle: React.CSSProperties = {
    margin: 0,
    padding: "10px 12px",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    fontFamily: "\"SFMono-Regular\", Consolas, Menlo, monospace",
    fontSize: 11,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
};

function formatMs(value: number): string {
    return `${((value || 0) / 1000).toFixed(2)}s`;
}

function formatMemory(value: number): string {
    return `${Math.round((value || 0) / 1024)} MB`;
}

/**
 * 05 提交结果：最近一次提交的判题状态、得分与用例结果。
 * 判题异步执行，页面在 pending / judging 时每 2 秒轮询一次。
 */
export function ResultPage() {
    const { examId } = useParams<{ examId: string }>();

    const [exam, setExam] = useState<StudentExamDetail | null>(null);
    const [submissions, setSubmissions] = useState<MySubmission[]>([]);
    const [detail, setDetail] = useState<SubmissionDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        Promise.all([fetchMyExam(Number(examId)), fetchMyExamSubmissions(Number(examId))])
            .then(([examDetail, result]) => {
                setExam(examDetail);
                setSubmissions(result.submissions);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [examId]);

    // 轮询最新提交的判题结果：pending / judging 时继续，最多约 2 分钟
    useEffect(() => {
        if (submissions.length === 0) {
            setDetail(null);
            return;
        }
        const latestId = submissions[0].id;
        let cancelled = false;
        let attempts = 0;
        let timer: number | undefined;

        setDetail(current => (current && current.id === latestId ? current : null));

        const tick = () => {
            fetchSubmission(latestId)
                .then(result => {
                    if (cancelled) {
                        return;
                    }
                    setDetail(result);
                    if (isPending(result.status) && attempts < 60) {
                        attempts += 1;
                        timer = window.setTimeout(tick, 2000);
                    }
                })
                .catch((e: ApiError) => {
                    if (cancelled) {
                        return;
                    }
                    // 提交被删除 / 无权查看时不再重试，避免无意义轮询
                    if (e.status === 401 || e.status === 403 || e.status === 404) {
                        return;
                    }
                    if (attempts < 60) {
                        attempts += 1;
                        timer = window.setTimeout(tick, 3000);
                    }
                });
        };
        tick();

        return () => {
            cancelled = true;
            if (timer) {
                window.clearTimeout(timer);
            }
        };
    }, [submissions]);

    const latest = submissions.length > 0 ? submissions[0] : null;
    const totalUsed = submissions.length;
    const totalQuota = exam ? exam.problems.length * exam.submitLimit : 0;
    const finished = exam?.status === "finished";

    const problemScore = exam && detail
        ? (exam.problems.find(item => item.problemId === detail.problemId)?.score || 0)
        : 0;
    const judged = detail?.status === "judged";
    const failed = detail?.status === "failed";
    const pending = detail ? isPending(detail.status) : !!latest && isPending(latest.status);
    const verdict = detail ? submissionLabel(detail) : null;

    const scoreText = judged
        ? String(detail?.score ?? 0)
        : failed ? "—" : (latest ? "判题中" : "—");

    const metrics = exam ? [
        { value: latest ? `#${latest.id}` : "—", label: "本次提交" },
        { value: latest ? formatDateTime(latest.created).slice(11) : "—", label: "提交时间" },
        { value: `${totalUsed} / ${totalQuota}`, label: "已用次数（全部题目）" },
        { value: finished ? "已结束" : "进行中", label: "考试状态", tone: finished ? undefined : ("green" as const) },
    ] : [];

    return (
        <StudentLayout active="reports">
            <div className="page-head">
                <div>
                    <div className="page-title">提交结果</div>
                    <div className="page-sub">
                        {exam ? `${exam.title}${latest ? ` · 提交 #${latest.id}` : " · 尚未提交"}` : "加载中…"}
                    </div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.examList}>
                        <Icon name="arrow-left" size={14}/>返回我的考试
                    </Link>
                    <Link className="btn btn-primary" to={Routes.examWorkbench(examId)}>
                        <Icon name="code" size={14}/>返回工作台
                    </Link>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                    </div>
                </div>
            )}

            {loading && (
                <div className="card"><div className="card-body muted">加载中…</div></div>
            )}

            {exam && !loading && (
                <>
                    <div className="result-summary">
                        <div className="score-block">
                            <div className="score-label">当前状态</div>
                            <div className="score-value">
                                {scoreText}
                                {judged && <span style={{ fontSize: 14, color: "#94a3b8" }}> / {problemScore}</span>}
                            </div>
                            <div className="score-status">
                                {verdict && <span className={"badge " + verdict.tone}>{verdict.label}</span>}
                                {judged && detail && (
                                    <span className="badge gray">
                                        用例 {detail.passedCount}/{detail.totalCount}
                                    </span>
                                )}
                                {detail?.needsReview && <span className="badge amber">需人工复核</span>}
                            </div>
                            <div className="score-note">
                                {latest
                                    ? `提交 #${latest.id}${judged ? ` · 得分 ${detail?.score ?? 0} 分` : pending ? " · 正在判题…" : ""}`
                                    : "还没有提交记录"}
                                {detail?.judgeError ? ` · ${detail.judgeError}` : ""}
                            </div>
                        </div>
                        <div className="score-metrics">
                            {judged && detail ? (
                                <>
                                    <div className="metric first">
                                        <div className="metric-value">
                                            {detail.samplePassed}/{detail.sampleTotal}
                                        </div>
                                        <div className="metric-label">样例测试</div>
                                    </div>
                                    <div className="metric">
                                        <div className="metric-value">
                                            {detail.hiddenPassed}/{detail.hiddenTotal}
                                        </div>
                                        <div className="metric-label">隐藏测试</div>
                                    </div>
                                    <div className="metric">
                                        <div className="metric-value">{formatMs(detail.timeMs)}</div>
                                        <div className="metric-label">最大耗时</div>
                                    </div>
                                    <div className="metric">
                                        <div className="metric-value">{formatMemory(detail.memoryKb)}</div>
                                        <div className="metric-label">峰值内存</div>
                                    </div>
                                </>
                            ) : metrics.map((metric, index) => (
                                <div className={"metric" + (index === 0 ? " first" : "")} key={metric.label}>
                                    <div className={"metric-value" + (metric.tone ? " " + metric.tone : "")}>
                                        {metric.value}
                                    </div>
                                    <div className="metric-label">{metric.label}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="result-main">
                        <div className="card result-table-card">
                            <div className="card-head">
                                <div>
                                    <div className="card-title">本次提交的代码</div>
                                    <div className="card-sub">
                                        {latest
                                            ? `${latest.problemTitle} · ${latest.language} · ${formatDateTime(latest.created)}`
                                            : "还没有提交记录"}
                                    </div>
                                </div>
                                {verdict && <span className={"badge " + verdict.tone}>{verdict.label}</span>}
                            </div>
                            {latest ? (
                                <div className="card-body">
                                    <pre style={CodeBoxStyle}>{latest.code || "（空提交）"}</pre>
                                </div>
                            ) : (
                                <div className="card-body muted">
                                    尚未提交，可返回工作台作答后提交（每题限 {exam.submitLimit} 次）。
                                </div>
                            )}
                        </div>

                        <div className="result-side">
                            <div className="card">
                                <div className="card-head">
                                    <div className="card-title">提交记录</div>
                                    <span className="badge blue">共 {totalUsed} 次</span>
                                </div>
                                <div className="card-body">
                                    {submissions.length === 0 && (
                                        <div className="muted" style={{ fontSize: 11.5 }}>暂无提交</div>
                                    )}
                                    {submissions.map((item, index) => {
                                        const meta = submissionLabel(item);
                                        return (
                                            <div className={"submit-item" + (index === submissions.length - 1 ? " last" : "")}
                                                 key={item.id}>
                                                <div className={index === 0 ? "submit-dot" : "submit-dot gray"}/>
                                                <div>
                                                    <div className="submit-title">
                                                        #{item.id} · {item.problemTitle}
                                                    </div>
                                                    <div className="submit-time">
                                                        {formatDateTime(item.created)} · {item.language} · {meta.label}
                                                        {item.status === "judged" ? ` · ${item.score ?? 0} 分` : ""}
                                                    </div>
                                                </div>
                                                {index === 0 && <span className="badge green">最新</span>}
                                            </div>
                                        );
                                    })}
                                    <div className="submit-rule">
                                        <Icon name="clock" size={11}/>
                                        每题限交 {exam.submitLimit} 次；同一题取最高分。
                                    </div>
                                </div>
                            </div>

                            <div className="card">
                                <div className="card-head">
                                    <div className="card-title">考试信息</div>
                                </div>
                                <div className="card-body">
                                    <div className="score-rule">
                                        <span>开始时间</span><strong>{formatDateTime(exam.startTime)}</strong>
                                    </div>
                                    <div className="score-rule">
                                        <span>结束时间</span><strong>{formatDateTime(exam.endTime)}</strong>
                                    </div>
                                    <div className="score-rule">
                                        <span>题目数量</span><strong>{exam.problems.length} 道</strong>
                                    </div>
                                    <div className="score-rule last">
                                        <span>AI 模式</span><strong>{exam.aiMode}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {detail && detail.cases.length > 0 && (
                        <div className="card result-table-card" style={{ marginTop: 14 }}>
                            <div className="card-head">
                                <div>
                                    <div className="card-title">用例结果</div>
                                    <div className="card-sub">
                                        隐藏用例仅显示汇总结果，不展示输入与预期输出
                                    </div>
                                </div>
                                <span className="badge blue">共 {detail.cases.length} 个用例</span>
                            </div>
                            <table className="table">
                                <thead>
                                <tr>
                                    <th>用例</th>
                                    <th>类型</th>
                                    <th>结果</th>
                                    <th>耗时</th>
                                    <th>内存</th>
                                </tr>
                                </thead>
                                <tbody>
                                {detail.cases.map((item, index) => {
                                    const meta = verdictMeta(item.verdict);
                                    return (
                                        <tr key={index}>
                                            <td>{item.name}</td>
                                            <td>{item.isSample ? "样例" : "隐藏"}</td>
                                            <td><span className={"badge " + meta.tone}>{meta.label}</span></td>
                                            <td>{formatMs(item.timeMs)}</td>
                                            <td>{formatMemory(item.memoryKb)}</td>
                                        </tr>
                                    );
                                })}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {detail?.compileOutput && (
                        <div className="card" style={{ marginTop: 14 }}>
                            <div className="card-head">
                                <div className="card-title">编译输出</div>
                            </div>
                            <div className="card-body">
                                <pre style={CodeBoxStyle}>{detail.compileOutput}</pre>
                            </div>
                        </div>
                    )}
                </>
            )}
        </StudentLayout>
    );
}
