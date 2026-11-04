import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { formatPeriod } from "../../api/format";
import { ApiError, ExamSummary, examAction, deleteExam, fetchExams } from "../../api/client";

const AiModeLabels: Record<string, string> = {
    limited: "受限",
    open: "开放",
    closed: "关闭",
};

/** 状态徽章：草稿 / 待开始 / 进行中 / 已结束 / 已归档 */
function statusMeta(exam: ExamSummary): { label: string; badge: string } {
    if (exam.status === "draft") {
        return { label: "草稿", badge: "gray" };
    }
    if (exam.status === "archived") {
        return { label: "已归档", badge: "gray" };
    }
    if (exam.studentStatus === "ongoing") {
        return { label: "进行中", badge: "green" };
    }
    if (exam.studentStatus === "upcoming") {
        return { label: "待开始", badge: "blue" };
    }
    return { label: "已结束", badge: "gray" };
}

type Tab = "list" | "scores" | "archive";

const Tabs: { key: Tab; label: string }[] = [
    { key: "list", label: "考试列表" },
    { key: "scores", label: "成绩分析" },
    { key: "archive", label: "归档" },
];

/**
 * 07 考试管理：真实数据。
 *
 * 闭环操作：创建（草稿）→ 组卷 → 名单 → 发布 → （结束）归档；
 * 监考与成绩报告仍是原型演示页，随后续迭代接入。
 */
export function ExamManagePage() {
    const [tab, setTab] = useState<Tab>("list");
    const [exams, setExams] = useState<ExamSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchExams()
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

    const runAction = (exam: ExamSummary, action: "publish" | "withdraw" | "archive") => {
        const prompts = {
            publish: `发布「${exam.title}」？发布后学生即可看到这场考试。`,
            withdraw: `撤回「${exam.title}」？撤回后回到草稿，开始前可重新发布。`,
            archive: `归档「${exam.title}」？归档后不能再编辑。`,
        };
        if (!window.confirm(prompts[action])) {
            return;
        }
        examAction(exam.id, action)
            .then(() => {
                toast(action === "publish" ? "考试已发布" : action === "withdraw" ? "已撤回为草稿" : "已归档", "success");
                load();
            })
            .catch((e: ApiError) => toast(e.message, "warning"));
    };

    const handleDelete = (exam: ExamSummary) => {
        if (!window.confirm(`删除草稿「${exam.title}」？`)) {
            return;
        }
        deleteExam(exam.id)
            .then(() => {
                toast("草稿已删除", "success");
                load();
            })
            .catch((e: ApiError) => toast(e.message, "warning"));
    };

    const visible = exams.filter(exam => {
        if (tab === "archive") {
            return exam.status === "archived";
        }
        return exam.status !== "archived";
    });

    const ongoingCount = exams.filter(e => e.status === "published" && e.studentStatus === "ongoing").length;
    const draftCount = exams.filter(e => e.status === "draft").length;
    const archivedCount = exams.filter(e => e.status === "archived").length;
    const submissionTotal = exams.reduce((sum, e) => sum + e.submissionCount, 0);

    const stats = [
        { icon: "play" as const, tone: "green", value: ongoingCount, label: "进行中", trend: `${ongoingCount} 场` },
        { icon: "file-text" as const, tone: "amber", value: draftCount, label: "待发布", trend: "草稿" },
        { icon: "check-circle" as const, tone: "", value: archivedCount, label: "已归档", trend: "本学期" },
        { icon: "arrow-up" as const, tone: "purple", value: submissionTotal, label: "提交总数", trend: "全部考试" },
    ];

    return (
        <TeacherLayout breadcrumb={["工作台", "软件工程 · 2026 秋", "考试管理"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">考试管理</div>
                    <div className="page-sub">创建、组卷、发布与归档课程考试</div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.problemBank}>
                        <Icon name="book-open" size={14}/>题库管理
                    </Link>
                    <Link className="btn btn-primary" to={Routes.examCreate}>
                        <Icon name="plus" size={14}/>创建考试
                    </Link>
                </div>
            </div>

            <div className="stats-grid">
                {stats.map(stat => (
                    <div className="stat-card" key={stat.label}>
                        <div className={"stat-icon" + (stat.tone ? " " + stat.tone : "")}>
                            <Icon name={stat.icon} size={17}/>
                        </div>
                        <div>
                            <div className="stat-value">{stat.value}</div>
                            <div className="stat-label">{stat.label}</div>
                        </div>
                        <span className="stat-trend">{stat.trend}</span>
                    </div>
                ))}
            </div>

            <div className="card manage-card">
                <div className="card-head">
                    <div className="tabs">
                        {Tabs.map(item => (
                            <span key={item.key}
                                  className={"tab" + (tab === item.key ? " active" : "")}
                                  onClick={() => setTab(item.key)}>
                                {item.label}
                            </span>
                        ))}
                    </div>
                    <div className="table-tools">
                        <span className="muted" style={{ fontSize: 11 }}>
                            代码评测接入前，提交记录只收卷存档
                        </span>
                    </div>
                </div>

                {error && (
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                    </div>
                )}

                {tab === "scores" ? (
                    <div className="card-body muted" style={{ textAlign: "center", padding: 32 }}>
                        成绩分析与过程评分随判题服务接入后开放（迭代计划第三、四轮）
                    </div>
                ) : (
                    <table className="table">
                        <thead>
                        <tr>
                            <th>考试名称</th>
                            <th>状态</th>
                            <th>考试时间</th>
                            <th>考生</th>
                            <th>提交</th>
                            <th>AI 模式</th>
                            <th>操作</th>
                        </tr>
                        </thead>
                        <tbody>
                        {loading && (
                            <tr><td colSpan={7} style={{ color: "#94a3b8" }}>加载中…</td></tr>
                        )}
                        {!loading && visible.length === 0 && (
                            <tr>
                                <td colSpan={7} style={{ color: "#94a3b8" }}>
                                    {tab === "archive" ? "还没有归档的考试" : "暂无考试，点击右上角「创建考试」开始"}
                                </td>
                            </tr>
                        )}
                        {visible.map(exam => {
                            const meta = statusMeta(exam);
                            return (
                                <tr key={exam.id}>
                                    <td>
                                        <div className="strong">{exam.title}</div>
                                        <div className="sub">
                                            {exam.course || "未指定课程"} · {exam.problemCount} 道题
                                        </div>
                                    </td>
                                    <td><span className={"badge " + meta.badge}>{meta.label}</span></td>
                                    <td>{formatPeriod(exam.startTime, exam.endTime)}</td>
                                    <td>
                                        {exam.candidateCount}
                                        {exam.openToAll && <span className="muted">（全体）</span>}
                                    </td>
                                    <td>{exam.submissionCount}</td>
                                    <td>{AiModeLabels[exam.aiMode] || exam.aiMode}</td>
                                    <td>
                                        {exam.status === "draft" && (
                                            <>
                                                <Link className="link" to={Routes.examEdit(exam.id)}>编辑</Link>
                                                <span className="muted"> · </span>
                                                <Link className="link" to={Routes.problemConfig(exam.id)}>组卷</Link>
                                                <span className="muted"> · </span>
                                                <span className="link" onClick={() => runAction(exam, "publish")}>发布</span>
                                                <span className="muted"> · </span>
                                                <span className="link" style={{ color: "#dc2626" }}
                                                      onClick={() => handleDelete(exam)}>删除</span>
                                            </>
                                        )}
                                        {exam.status === "published" && exam.studentStatus === "upcoming" && (
                                            <>
                                                <Link className="link" to={Routes.examEdit(exam.id)}>编辑</Link>
                                                <span className="muted"> · </span>
                                                <Link className="link" to={Routes.problemConfig(exam.id)}>组卷</Link>
                                                <span className="muted"> · </span>
                                                <span className="link" onClick={() => runAction(exam, "withdraw")}>撤回</span>
                                                <span className="muted"> · </span>
                                                <Link className="link" to={Routes.proctor(exam.id)}>监考</Link>
                                            </>
                                        )}
                                        {exam.status === "published" && exam.studentStatus === "ongoing" && (
                                            <>
                                                <Link className="link" to={Routes.proctor(exam.id)}>监考</Link>
                                                <span className="muted"> · </span>
                                                <span className="muted" title="考试进行中，配置已冻结">组卷（已冻结）</span>
                                            </>
                                        )}
                                        {exam.status === "published" && exam.studentStatus === "finished" && (
                                            <>
                                                <span className="link" onClick={() => runAction(exam, "archive")}>归档</span>
                                                <span className="muted"> · </span>
                                                <Link className="link" to={Routes.examReport(exam.id)}>报告</Link>
                                            </>
                                        )}
                                        {exam.status === "archived" && (
                                            <Link className="link" to={Routes.examReport(exam.id)}>报告</Link>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        </tbody>
                    </table>
                )}
                <div className="table-footer">
                    <span>共 {exams.length} 场考试 · 当前显示 {visible.length} 场</span>
                    <span className="muted">发布前请完成组卷；开始后配置冻结</span>
                </div>
            </div>
        </TeacherLayout>
    );
}
