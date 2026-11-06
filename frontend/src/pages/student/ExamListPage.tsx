import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { formatCountdown, formatPeriod, formatToday, secondsUntil } from "../../api/format";
import { ApiError, fetchMyExams, MyExamSummary } from "../../api/client";

type Filter = "all" | "upcoming" | "finished";

const Filters: { key: Filter; label: string }[] = [
    { key: "all", label: "全部" },
    { key: "upcoming", label: "待考" },
    { key: "finished", label: "已完成" },
];

const AiModeLabels: Record<string, string> = {
    limited: "受限",
    open: "开放",
    closed: "关闭",
};

const Rules = [
    { title: "提前完成自检", desc: "建议提前 15 分钟检查浏览器、网络与编辑器环境。" },
    { title: "AI 使用策略", desc: "按每场考试配置：开放 / 受限 / 关闭，全程留痕。" },
    { title: "网络与数据", desc: "考试期间遵守考场纪律；平台不录屏、不采集摄像头。" },
    { title: "申诉时限", desc: "成绩发布后 48 小时内可发起申诉，逾期不再受理。" },
];

/** 英雄区展示的考试：进行中优先，其次最近一场待考 */
function pickFeatured(exams: MyExamSummary[]): MyExamSummary | null {
    const ongoing = exams.find(exam => exam.studentStatus === "ongoing");
    if (ongoing) {
        return ongoing;
    }
    const upcoming = exams
        .filter(exam => exam.studentStatus === "upcoming" && exam.startTime)
        .sort((a, b) => (a.startTime! < b.startTime! ? -1 : 1));
    return upcoming[0] || null;
}

/** 02 我的考试：真实数据。成绩列待判题服务接入后开放 */
export function ExamListPage() {
    const [filter, setFilter] = useState<Filter>("all");
    const [exams, setExams] = useState<MyExamSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [, setTick] = useState(0);

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

    // 英雄区倒计时：每秒重渲染一次
    useEffect(() => {
        const timer = window.setInterval(() => setTick(value => value + 1), 1000);
        return () => window.clearInterval(timer);
    }, []);

    const visible = useMemo(() => {
        if (filter === "all") {
            return exams;
        }
        return exams.filter(exam => exam.studentStatus === filter);
    }, [exams, filter]);

    const featured = pickFeatured(exams);
    const upcomingCount = exams.filter(e => e.studentStatus === "upcoming").length;
    const finishedCount = exams.filter(e => e.studentStatus === "finished").length;
    const submissionTotal = exams.reduce((sum, e) => sum + e.mySubmissions, 0);

    // 进行中 → 距结束；待考 → 距开始
    const featuredOngoing = featured?.studentStatus === "ongoing";
    const featuredSeconds = featured
        ? secondsUntil(featuredOngoing ? featured.endTime : featured.startTime)
        : 0;

    const statusBadge = (status: MyExamSummary["studentStatus"]) => {
        if (status === "upcoming") {
            return <span className="badge blue">待考</span>;
        }
        if (status === "ongoing") {
            return <span className="badge green">进行中</span>;
        }
        return <span className="badge gray">已完成</span>;
    };

    return (
        <StudentLayout active="exams">
            <div className="page-head">
                <div>
                    <div className="page-title">我的考试</div>
                    <div className="page-sub">查看考试安排、进入考场与历史记录</div>
                </div>
                <div className="page-actions">
                    <span className="date-text">
                        <Icon name="calendar" size={13}/>{formatToday()}
                    </span>
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

            {/* 进行中 / 即将开始的考试 */}
            {featured && !error && (
                <div className="exam-hero">
                    <div className="exam-hero-left">
                        <div className="hero-label">
                            <span className="live-dot"/>{featuredOngoing ? "正在进行" : "即将开始"}
                        </div>
                        <div className="hero-title">{featured.title}</div>
                        <div className="hero-meta">
                            <span><Icon name="calendar" size={13}/>{formatPeriod(featured.startTime, featured.endTime)}</span>
                            <span><Icon name="clock" size={13}/>{featured.durationMinutes} 分钟</span>
                            <span><Icon name="shield-check" size={13}/>AI {AiModeLabels[featured.aiMode] || featured.aiMode}模式</span>
                            <span><Icon name="file-text" size={13}/>{featured.problemCount} 道题</span>
                        </div>
                        <div className="hero-note">建议提前 15 分钟完成环境自检；开考 15 分钟后禁止入场。</div>
                    </div>
                    <div className="exam-hero-right">
                        <div className="countdown-label">{featuredOngoing ? "距结束" : "距开始"}</div>
                        <div className="countdown">{formatCountdown(featuredSeconds)}</div>
                        <Link className="btn btn-primary" to={Routes.examPrecheck(featured.id)}>
                            <Icon name="arrow-right" size={14}/>进入考场
                        </Link>
                    </div>
                </div>
            )}

            {/* 概览数据 */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon"><Icon name="calendar" size={17}/></div>
                    <div>
                        <div className="stat-value">{upcomingCount}</div>
                        <div className="stat-label">待考考试</div>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon green"><Icon name="check-circle" size={17}/></div>
                    <div>
                        <div className="stat-value">{finishedCount}</div>
                        <div className="stat-label">已完成考试</div>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon purple"><Icon name="bar-chart" size={17}/></div>
                    <div>
                        <div className="stat-value">{submissionTotal}</div>
                        <div className="stat-label">我的提交</div>
                    </div>
                    <span className="stat-trend">判题服务接入前不计分</span>
                </div>
            </div>

            <div className="exam-main">
                <div className="card exam-list-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">全部考试</div>
                            <div className="card-sub">共 {exams.length} 场考试</div>
                        </div>
                        <div className="tabs-inline">
                            {Filters.map(item => (
                                <span key={item.key}
                                      className={"tab-pill" + (filter === item.key ? " active" : "")}
                                      onClick={() => setFilter(item.key)}>
                                    {item.label}
                                </span>
                            ))}
                        </div>
                    </div>
                    <table className="table">
                        <thead>
                        <tr>
                            <th>考试</th>
                            <th>时间</th>
                            <th>时长</th>
                            <th>AI 模式</th>
                            <th>状态</th>
                            <th>成绩</th>
                            <th/>
                        </tr>
                        </thead>
                        <tbody>
                        {loading && (
                            <tr><td colSpan={7} className="muted">加载中…</td></tr>
                        )}
                        {!loading && visible.length === 0 && (
                            <tr>
                                <td colSpan={7} className="muted" style={{ textAlign: "center" }}>
                                    {exams.length === 0 ? "暂无考试，请等待老师发布" : "该状态下暂无考试"}
                                </td>
                            </tr>
                        )}
                        {visible.map(exam => (
                            <tr key={exam.id}>
                                <td>
                                    <div className="strong">{exam.title}</div>
                                    <div className="sub">{exam.course || "未指定课程"}</div>
                                </td>
                                <td>{formatPeriod(exam.startTime, exam.endTime)}</td>
                                <td>{exam.durationMinutes} 分钟</td>
                                <td>{AiModeLabels[exam.aiMode] || exam.aiMode}</td>
                                <td>{statusBadge(exam.studentStatus)}</td>
                                <td className="muted">—</td>
                                <td>
                                    {exam.studentStatus === "finished"
                                        ? <Link className="link" to={Routes.examReport(exam.id)}>查看报告</Link>
                                        : <Link className="link" to={Routes.examPrecheck(exam.id)}>进入考场</Link>}
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    <div className="table-footer">
                        <span>当前显示 {visible.length} / {exams.length} 场</span>
                        <span className="muted">成绩统计随判题服务接入后开放</span>
                    </div>
                </div>

                <div className="side-col">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">考试须知</div>
                            <span className="badge amber">请提前阅读</span>
                        </div>
                        <div className="card-body">
                            {Rules.map((rule, index) => (
                                <div className="rule-item" key={rule.title}>
                                    <span className="rule-num">{index + 1}</span>
                                    <div>
                                        <div className="rule-title">{rule.title}</div>
                                        <div className="rule-desc">{rule.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </StudentLayout>
    );
}
