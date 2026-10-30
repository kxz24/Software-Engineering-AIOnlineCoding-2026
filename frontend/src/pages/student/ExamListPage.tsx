import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import {
    AiModeLabels,
    averageScore,
    countByStatus,
    featuredExam,
    formatCountdown,
    formatToday,
    mockExams,
    nextExamStart,
} from "../../mock/exams";

type Filter = "all" | "upcoming" | "finished";

const Filters: { key: Filter; label: string }[] = [
    { key: "all", label: "全部" },
    { key: "upcoming", label: "待考" },
    { key: "finished", label: "已完成" },
];

const DeviceChecks = [
    "浏览器 · Chrome 128",
    "网络 · 下行 86 Mbps",
    "终端 · xterm.js 已连接",
    "Coding Agent · 受限模式可用",
];

const Rules = [
    { title: "提前完成自检", desc: "建议提前 15 分钟检查浏览器、网络、终端与 Agent。" },
    { title: "AI 受限模式", desc: "可解释与运行测试，不可直接写入代码；全程留痕。" },
    { title: "网络与数据", desc: "考试期间禁止外部网络；不录屏、不采集摄像头。" },
    { title: "申诉时限", desc: "成绩发布后 48 小时内可发起申诉，逾期不再受理。" },
];

/** 02 我的考试：考试安排、进入考场与历史成绩 */
export function ExamListPage() {
    const [filter, setFilter] = useState<Filter>("all");
    const [seconds, setSeconds] = useState(
        Math.floor((nextExamStart().getTime() - Date.now()) / 1000)
    );

    // 英雄区倒计时
    useEffect(() => {
        const timer = window.setInterval(() => {
            setSeconds(Math.floor((nextExamStart().getTime() - Date.now()) / 1000));
        }, 1000);
        return () => window.clearInterval(timer);
    }, []);

    const exams = useMemo(() => {
        if (filter === "all") {
            return mockExams;
        }
        return mockExams.filter(exam => exam.status === filter);
    }, [filter]);

    const recentScored = mockExams.filter(exam => exam.score != null).slice(0, 3);

    return (
        <StudentLayout active="exams">
            <div className="page-head">
                <div>
                    <div className="page-title">我的考试</div>
                    <div className="page-sub">查看考试安排、进入考场与历史成绩</div>
                </div>
                <div className="page-actions">
                    <span className="date-text">
                        <Icon name="calendar" size={13}/>{formatToday()}
                    </span>
                    <Link className="btn btn-secondary" to={Routes.examPrecheck(featuredExam.id)}>
                        考试须知
                    </Link>
                </div>
            </div>

            {/* 即将开始的考试 */}
            <div className="exam-hero">
                <div className="exam-hero-left">
                    <div className="hero-label"><span className="live-dot"/>即将开始</div>
                    <div className="hero-title">{featuredExam.title}</div>
                    <div className="hero-meta">
                        <span><Icon name="calendar" size={13}/>{featuredExam.periodLabel}</span>
                        <span><Icon name="clock" size={13}/>{featuredExam.durationMinutes} 分钟</span>
                        <span><Icon name="shield-check" size={13}/>AI 受限模式</span>
                        <span><Icon name="file-text" size={13}/>{featuredExam.problemCount} 道工程题</span>
                    </div>
                    <div className="hero-note">建议提前 15 分钟完成环境自检；开考 15 分钟后禁止入场。</div>
                </div>
                <div className="exam-hero-right">
                    <div className="countdown-label">距开始</div>
                    <div className="countdown">{formatCountdown(seconds)}</div>
                    <Link className="btn btn-primary" to={Routes.examPrecheck(featuredExam.id)}>
                        <Icon name="arrow-right" size={14}/>进入考场
                    </Link>
                </div>
            </div>

            {/* 概览数据 */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon"><Icon name="calendar" size={17}/></div>
                    <div>
                        <div className="stat-value">{countByStatus("upcoming")}</div>
                        <div className="stat-label">待考考试</div>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon green"><Icon name="check-circle" size={17}/></div>
                    <div>
                        <div className="stat-value">{countByStatus("finished")}</div>
                        <div className="stat-label">已完成考试</div>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon purple"><Icon name="bar-chart" size={17}/></div>
                    <div>
                        <div className="stat-value">{averageScore()}</div>
                        <div className="stat-label">平均分</div>
                    </div>
                    <span className="stat-trend green">较上次 +4.2</span>
                </div>
            </div>

            <div className="exam-main">
                <div className="card exam-list-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">全部考试</div>
                            <div className="card-sub">共 {mockExams.length} 场考试</div>
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
                        {exams.map(exam => (
                            <tr key={exam.id}>
                                <td>
                                    <div className="strong">{exam.title}</div>
                                    <div className="sub">{exam.sub}</div>
                                </td>
                                <td>{exam.dateLabel}</td>
                                <td>{exam.durationMinutes} 分钟</td>
                                <td>{AiModeLabels[exam.aiMode]}</td>
                                <td>
                                    <span className={"badge " + (exam.status === "upcoming" ? "blue" : "gray")}>
                                        {exam.status === "upcoming" ? "待考" : "已完成"}
                                    </span>
                                </td>
                                <td className={exam.score == null ? "muted" : undefined}>
                                    {exam.score == null ? "—" : <span className="strong">{exam.score}</span>}
                                </td>
                                <td>
                                    {exam.status === "upcoming"
                                        ? <Link className="link" to={Routes.examPrecheck(exam.id)}>进入考场</Link>
                                        : <Link className="link" to={Routes.examReport(exam.id)}>查看报告</Link>}
                                </td>
                            </tr>
                        ))}
                        {exams.length === 0 && (
                            <tr>
                                <td colSpan={7} className="muted" style={{ textAlign: "center" }}>
                                    暂无考试
                                </td>
                            </tr>
                        )}
                        </tbody>
                    </table>
                    <div className="recent-box">
                        <div className="recent-label">最近成绩</div>
                        <div className="recent-chips">
                            {recentScored.map(exam => (
                                <Link key={exam.id} className="recent-chip" to={Routes.examReport(exam.id)}>
                                    {exam.title}<strong>{exam.score}</strong>
                                </Link>
                            ))}
                        </div>
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
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">设备检查</div>
                            <span className="badge green">全部通过</span>
                        </div>
                        <div className="card-body">
                            {DeviceChecks.map(item => (
                                <div className="check-line" key={item}>
                                    <span className="ok"><Icon name="check-circle" size={13} stroke="#059669"/></span>{item}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </StudentLayout>
    );
}
