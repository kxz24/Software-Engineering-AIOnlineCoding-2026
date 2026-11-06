import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useSelector } from "react-redux";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { formatDateTime } from "../../api/format";
import { Store } from "../../store";
import { ApiError, fetchMyExam, fetchMyExamSubmissions, MySubmission, StudentExamDetail } from "../../api/client";

const AiModeLabels: Record<string, string> = { limited: "受限", open: "开放", closed: "关闭" };

/**
 * 06 过程报告：本场考试的提交时间线与各题提交统计。
 * 得分、AI 协作过程评分与申诉入口随评测 / 过程数据服务接入后提供。
 */
export function ReportPage() {
    const { examId } = useParams<{ examId: string }>();
    const user = useSelector((s: Store) => s.user);

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

    /** 各题提交次数（上限为考试的每题限次） */
    const perProblem = useMemo(() => {
        if (!exam) {
            return [];
        }
        return exam.problems.map(problem => ({
            problem,
            used: submissions.filter(item => item.problemId === problem.problemId).length,
        }));
    }, [exam, submissions]);

    const involved = perProblem.filter(item => item.used > 0).length;
    const finished = exam?.status === "finished";

    return (
        <StudentLayout active="reports">
            <div className="page-head">
                <div>
                    <div className="page-title">过程报告</div>
                    <div className="page-sub">
                        {exam
                            ? `${exam.title} · ${user?.nickname || user?.username || ""}`
                            : "加载中…"}
                    </div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.reports}>
                        <Icon name="arrow-left" size={14}/>返回报告列表
                    </Link>
                    <Link className="btn btn-primary" to={Routes.examList}>
                        <Icon name="calendar" size={14}/>我的考试
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
                    {/* 总览：评测接入前没有分数，展示收卷状态 */}
                    <div className="report-summary">
                        <div className="rs-score">
                            <div className="rs-label">当前状态</div>
                            <div className="rs-value">待判定</div>
                            <div className="rs-note">
                                {finished ? "考试已结束，等待评测" : "考试进行中或待开始"}
                            </div>
                        </div>
                        <div className="rs-item">
                            <div className="rs-item-label">提交次数</div>
                            <div className="rs-item-value">{submissions.length}</div>
                        </div>
                        <div className="rs-item">
                            <div className="rs-item-label">已作答题目</div>
                            <div className="rs-item-value">
                                {involved}<span> / {exam.problems.length}</span>
                            </div>
                        </div>
                        <div className="rs-item">
                            <div className="rs-item-label">考试状态</div>
                            <div className="rs-item-value" style={{ fontSize: 15 }}>
                                {finished ? "已结束" : exam.status === "ongoing" ? "进行中" : "待开始"}
                            </div>
                        </div>
                    </div>

                    <div className="report-main">
                        <div className="card report-timeline-card">
                            <div className="card-head">
                                <div>
                                    <div className="card-title">提交时间线</div>
                                    <div className="card-sub">按时间倒序；判定结果随评测服务接入后补充</div>
                                </div>
                                <span className="badge gray">共 {submissions.length} 次提交</span>
                            </div>
                            <div className="card-body">
                                {submissions.length === 0 && (
                                    <div className="muted" style={{ fontSize: 11.5 }}>本场考试还没有提交记录</div>
                                )}
                                {submissions.map(item => (
                                    <div className="tl-item" key={item.id}>
                                        <div className="tl-rail">
                                            <span className="tl-dot green"/>
                                            <span className="tl-line"/>
                                        </div>
                                        <div className="tl-time">{formatDateTime(item.created).slice(11)}</div>
                                        <div className="tl-content">
                                            <div className="tl-title">
                                                提交 #{item.id} · {item.problemTitle}
                                            </div>
                                            <div className="tl-desc">
                                                {item.language} · 已收卷 · 待判定
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="report-side">
                            <div className="card">
                                <div className="card-head">
                                    <div className="card-title">各题提交统计</div>
                                    <span className="badge blue">每题限 {exam.submitLimit} 次</span>
                                </div>
                                <div className="card-body">
                                    {perProblem.map(({ problem, used }, index) => (
                                        <div key={problem.problemId}
                                             className={"rubric-item" + (index === perProblem.length - 1 ? " last" : "")}>
                                            <div className="rubric-row">
                                                <span>任务 {problem.order + 1} · {problem.title}</span>
                                                <strong>{used} / {exam.submitLimit}</strong>
                                            </div>
                                            <div className="bar">
                                                <span className="bar-fill green"
                                                      style={{ width: `${Math.min(100, used / exam.submitLimit * 100)}%` }}/>
                                            </div>
                                            <div className="rubric-ev">
                                                {problem.score} 分 · {problem.type === "algorithm" ? "算法题" : "工程题"} ·{" "}
                                                {problem.language}
                                            </div>
                                        </div>
                                    ))}
                                    {perProblem.length === 0 && (
                                        <div className="muted" style={{ fontSize: 11.5 }}>本场考试没有题目</div>
                                    )}
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
                                        <span>时长</span><strong>{exam.durationMinutes} 分钟</strong>
                                    </div>
                                    <div className="score-rule last">
                                        <span>AI 模式</span><strong>{AiModeLabels[exam.aiMode] || exam.aiMode}</strong>
                                    </div>
                                </div>
                            </div>

                            <div className="card tip-card">
                                <div className="tip-icon"><Icon name="sparkles" size={15}/></div>
                                <div>
                                    <div className="tip-title">评分与申诉随后续迭代开放</div>
                                    <div className="tip-desc">
                                        得分明细、AI 协作过程评分与成绩申诉依赖评测与过程数据服务。
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
