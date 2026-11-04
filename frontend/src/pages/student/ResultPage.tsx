import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { formatDateTime } from "../../api/format";
import { ApiError, fetchMyExam, fetchMyExamSubmissions, MySubmission, StudentExamDetail } from "../../api/client";

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

/**
 * 05 提交结果：最近一次提交的收卷状态与提交历史。
 * 判定结果（得分、用例通过情况）随评测服务接入后展示。
 */
export function ResultPage() {
    const { examId } = useParams<{ examId: string }>();

    const [exam, setExam] = useState<StudentExamDetail | null>(null);
    const [submissions, setSubmissions] = useState<MySubmission[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        Promise.all([fetchMyExam(Number(examId)), fetchMyExamSubmissions(Number(examId))])
            .then(([detail, result]) => {
                setExam(detail);
                setSubmissions(result.submissions);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [examId]);

    const latest = submissions.length > 0 ? submissions[0] : null;
    const totalUsed = submissions.length;
    const totalQuota = exam ? exam.problems.length * exam.submitLimit : 0;
    const finished = exam?.status === "finished";

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
                    {/* 收卷概览：评测服务接入前没有得分，状态为待判定 */}
                    <div className="result-summary">
                        <div className="score-block">
                            <div className="score-label">当前状态</div>
                            <div className="score-value">待判定</div>
                            <div className="score-status">
                                <span className="badge green">已收卷</span>
                                <span className="badge amber">等待评测</span>
                            </div>
                            <div className="score-note">
                                代码已存档（提交 {latest ? `#${latest.id}` : "—"}）；
                                得分与用例结果将在评测服务接入后展示。
                            </div>
                        </div>
                        <div className="score-metrics">
                            {metrics.map((metric, index) => (
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
                                <span className="badge gray">待判定</span>
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
                                    {submissions.map((item, index) => (
                                        <div className={"submit-item" + (index === submissions.length - 1 ? " last" : "")}
                                             key={item.id}>
                                            <div className={index === 0 ? "submit-dot" : "submit-dot gray"}/>
                                            <div>
                                                <div className="submit-title">
                                                    #{item.id} · {item.problemTitle}
                                                </div>
                                                <div className="submit-time">
                                                    {formatDateTime(item.created)} · {item.language} · 待判定
                                                </div>
                                            </div>
                                            {index === 0 && <span className="badge green">最新</span>}
                                        </div>
                                    ))}
                                    <div className="submit-rule">
                                        <Icon name="clock" size={11}/>
                                        每题限交 {exam.submitLimit} 次；评测接入前提交仅收卷存档。
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
                </>
            )}
        </StudentLayout>
    );
}
