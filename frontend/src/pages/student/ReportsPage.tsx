import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { formatPeriod } from "../../api/format";
import { ApiError, fetchMyExams, MyExamSummary } from "../../api/client";

/**
 * 成绩报告首页：列出可查看报告的考试。
 * 评测服务接入前报告展示收卷与提交统计，不展示分数。
 */
export function ReportsPage() {
    const [exams, setExams] = useState<MyExamSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchMyExams()
            .then(result => {
                setExams(result.exams);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, []);

    // 已完成的考试可直接看报告；进行中 / 待考的也可进入查看提交情况
    const finished = exams.filter(exam => exam.studentStatus === "finished");
    const active = exams.filter(exam => exam.studentStatus !== "finished");

    return (
        <StudentLayout active="reports">
            <div className="page-head">
                <div>
                    <div className="page-title">成绩报告</div>
                    <div className="page-sub">按考试查看提交情况；得分与过程评分随评测服务接入后展示</div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.examList}>
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

            <div className="card exam-list-card">
                <div className="card-head">
                    <div>
                        <div className="card-title">已完成的考试</div>
                        <div className="card-sub">共 {finished.length} 场</div>
                    </div>
                </div>
                <table className="table">
                    <thead>
                    <tr>
                        <th>考试</th>
                        <th>时间</th>
                        <th>我的提交</th>
                        <th>成绩</th>
                        <th/>
                    </tr>
                    </thead>
                    <tbody>
                    {loading && <tr><td colSpan={5} className="muted">加载中…</td></tr>}
                    {!loading && finished.length === 0 && (
                        <tr>
                            <td colSpan={5} className="muted" style={{ textAlign: "center" }}>
                                暂无已完成的考试
                            </td>
                        </tr>
                    )}
                    {finished.map(exam => (
                        <tr key={exam.id}>
                            <td>
                                <div className="strong">{exam.title}</div>
                                <div className="sub">{exam.course || "未指定课程"}</div>
                            </td>
                            <td>{formatPeriod(exam.startTime, exam.endTime)}</td>
                            <td>{exam.mySubmissions} 次</td>
                            <td className="muted">待判定</td>
                            <td>
                                <Link className="link" to={Routes.examReport(exam.id)}>查看报告</Link>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
                <div className="table-footer">
                    <span>进行中 / 待考 {active.length} 场（在「我的考试」进入）</span>
                    <span className="muted">评测服务接入前不展示分数</span>
                </div>
            </div>
        </StudentLayout>
    );
}
