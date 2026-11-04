import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { formatCountdown, formatDateTime, formatShort, secondsUntil } from "../../api/format";
import {
    ApiError,
    ExamDetail,
    ExamSubmissionEntry,
    ExamSummary,
    fetchExam,
    fetchExamSubmissions,
    fetchExams,
} from "../../api/client";

/** 每 15 秒自动拉取一次提交动态 */
const RefreshIntervalMs = 15000;

const StatusLabels: Record<string, { label: string; badge: string }> = {
    upcoming: { label: "待开始", badge: "blue" },
    ongoing: { label: "进行中", badge: "green" },
    finished: { label: "已结束", badge: "gray" },
};

/** 把提交记录整理成「每个考生一行」的统计 */
interface CandidateStat {
    username: string;
    nickname: string;
    submitCount: number;
    problemCount: number;
    lastCreated: string;
}

function groupByStudent(submissions: ExamSubmissionEntry[]): CandidateStat[] {
    const map = new Map<string, CandidateStat>();
    const problemsByStudent = new Map<string, Set<number>>();
    submissions.forEach(item => {
        const row = map.get(item.username) || {
            username: item.username,
            nickname: item.nickname || item.username,
            submitCount: 0,
            problemCount: 0,
            lastCreated: item.created,
        };
        row.submitCount += 1;
        if (item.created > row.lastCreated) {
            row.lastCreated = item.created;
        }
        map.set(item.username, row);
        const set = problemsByStudent.get(item.username) || new Set<number>();
        set.add(item.problemId);
        problemsByStudent.set(item.username, set);
    });
    return Array.from(map.values()).map(row => ({
        ...row,
        problemCount: (problemsByStudent.get(row.username) || new Set()).size,
    }));
}

/** 导出提交记录 CSV（带 BOM，Excel 打开中文不乱码） */
function exportCsv(exam: ExamDetail, submissions: ExamSubmissionEntry[]) {
    const header = ["提交ID", "时间", "考生", "学号/工号", "题目", "语言", "状态"];
    const lines = submissions.map(item => [
        String(item.id),
        formatDateTime(item.created),
        item.nickname,
        item.username,
        item.problemTitle,
        item.language,
        "待判定",
    ]);
    const csv = [header, ...lines]
        .map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(","))
        .join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${exam.title}-提交记录.csv`;
    link.click();
    URL.revokeObjectURL(url);
}

/**
 * 10 监考中心。
 *
 * 不带考试 ID 进入时列出可监考的考试；带 ID 时展示本场考情：
 * 考生提交统计与实时提交动态（自动刷新）。异常告警与处置需要
 * 监考探针接入，随后续迭代提供。
 */
export function ProctorPage() {
    const { examId } = useParams<{ examId?: string }>();
    const numeric = examId != null && /^\d+$/.test(examId) ? Number(examId) : null;
    return numeric != null ? <ProctorDashboard examId={numeric}/> : <ProctorPicker/>;
}

/** 监考首页：选择一场考试 */
function ProctorPicker() {
    const [exams, setExams] = useState<ExamSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchExams({ status: "published" })
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

    return (
        <TeacherLayout breadcrumb={["工作台", "监考中心"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">监考中心</div>
                    <div className="page-sub">选择一场考试查看考情与提交动态</div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.examManage}>
                        <Icon name="arrow-left" size={14}/>返回考试管理
                    </Link>
                </div>
            </div>

            <div className="card manage-card">
                <div className="card-head">
                    <div>
                        <div className="card-title">已发布的考试</div>
                        <div className="card-sub">共 {exams.length} 场</div>
                    </div>
                </div>
                {error && (
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                    </div>
                )}
                <table className="table">
                    <thead>
                    <tr>
                        <th>考试名称</th>
                        <th>状态</th>
                        <th>考试时间</th>
                        <th>考生</th>
                        <th>提交</th>
                        <th>操作</th>
                    </tr>
                    </thead>
                    <tbody>
                    {loading && <tr><td colSpan={6} className="muted">加载中…</td></tr>}
                    {!loading && exams.length === 0 && (
                        <tr><td colSpan={6} className="muted">暂无进行中或待开始的考试</td></tr>
                    )}
                    {exams.map(exam => {
                        const meta = StatusLabels[exam.studentStatus] || StatusLabels.upcoming;
                        return (
                            <tr key={exam.id}>
                                <td>
                                    <div className="strong">{exam.title}</div>
                                    <div className="sub">{exam.course || "未指定课程"} · {exam.problemCount} 道题</div>
                                </td>
                                <td><span className={"badge " + meta.badge}>{meta.label}</span></td>
                                <td>{formatShort(exam.startTime)} – {formatShort(exam.endTime)}</td>
                                <td>{exam.candidateCount}{exam.openToAll && <span className="muted">（全体）</span>}</td>
                                <td>{exam.submissionCount}</td>
                                <td><Link className="link" to={Routes.proctor(exam.id)}>进入监考</Link></td>
                            </tr>
                        );
                    })}
                    </tbody>
                </table>
            </div>
        </TeacherLayout>
    );
}

/** 单场考试的考情面板 */
function ProctorDashboard({ examId }: { examId: number }) {
    const [exam, setExam] = useState<ExamDetail | null>(null);
    const [submissions, setSubmissions] = useState<ExamSubmissionEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [keyword, setKeyword] = useState("");
    const [filterStudent, setFilterStudent] = useState<string | null>(null);
    const [updatedClock, setUpdatedClock] = useState<string>("--:--:--");
    const [, setTick] = useState(0);

    const load = () => {
        setLoading(true);
        setError(null);
        Promise.all([fetchExam(examId), fetchExamSubmissions(examId)])
            .then(([detail, result]) => {
                setExam(detail);
                setSubmissions(result.submissions);
                setUpdatedClock(new Date().toTimeString().slice(0, 8));
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [examId]);

    // 自动刷新提交动态；手动刷新共用同一个轻量请求
    useEffect(() => {
        if (!exam || error) {
            return;
        }
        const timer = window.setInterval(() => {
            fetchExamSubmissions(examId)
                .then(result => {
                    setSubmissions(result.submissions);
                    setUpdatedClock(new Date().toTimeString().slice(0, 8));
                })
                .catch(() => {
                    // 网络抖动不打断页面，等下一轮
                });
        }, RefreshIntervalMs);
        return () => window.clearInterval(timer);
    }, [examId, exam, error]);

    // 剩余时间每秒刷新
    useEffect(() => {
        const timer = window.setInterval(() => setTick(value => value + 1), 1000);
        return () => window.clearInterval(timer);
    }, []);

    const refreshSubmissions = () => {
        fetchExamSubmissions(examId)
            .then(result => {
                setSubmissions(result.submissions);
                setUpdatedClock(new Date().toTimeString().slice(0, 8));
                toast("已刷新", "success");
            })
            .catch((e: ApiError) => toast(e.message, "warning"));
    };

    /** 名单内考生（或全体模式下的已提交考生）逐人统计 */
    const stats = useMemo(() => groupByStudent(submissions), [submissions]);
    const rows = useMemo(() => {
        const base = exam && !exam.openToAll
            ? exam.candidates.map(username => {
                const found = stats.find(item => item.username === username);
                return found || {
                    username,
                    nickname: username,
                    submitCount: 0,
                    problemCount: 0,
                    lastCreated: "",
                };
            })
            : stats;
        const query = keyword.trim().toLowerCase();
        const filtered = query
            ? base.filter(row =>
                row.username.toLowerCase().indexOf(query) >= 0 ||
                row.nickname.toLowerCase().indexOf(query) >= 0)
            : base;
        // 有提交的在前，其次按最近提交时间倒序
        return filtered.slice().sort((a, b) => {
            if ((a.submitCount > 0) !== (b.submitCount > 0)) {
                return a.submitCount > 0 ? -1 : 1;
            }
            return a.lastCreated < b.lastCreated ? 1 : -1;
        });
    }, [exam, stats, keyword]);

    const feed = useMemo(
        () => (filterStudent ? submissions.filter(item => item.username === filterStudent) : submissions),
        [submissions, filterStudent]
    );

    const ongoing = exam?.studentStatus === "ongoing";
    const remainingSeconds = exam ? secondsUntil(exam.endTime) : 0;
    const submitters = stats.length;

    const cards = [
        { icon: "users" as const, tone: "green", value: exam ? (exam.openToAll ? "全体" : String(exam.candidateCount)) : "—", label: "考生" },
        { icon: "arrow-up" as const, tone: "purple", value: String(submissions.length), label: "提交总数" },
        { icon: "check-circle" as const, tone: "", value: String(submitters), label: "已提交考生" },
        {
            icon: "clock" as const,
            tone: ongoing ? "amber" : "",
            value: ongoing ? formatCountdown(remainingSeconds) : "已结束",
            label: ongoing ? "距收卷" : "考试状态",
        },
    ];

    return (
        <TeacherLayout breadcrumb={["工作台", "监考中心"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">监考中心</div>
                    <div className="page-sub">
                        {exam ? `${exam.title} · ${StatusLabels[exam.studentStatus]?.label || exam.studentStatus}` : "加载中…"}
                    </div>
                </div>
                <div className="page-actions">
                    <span className="btn btn-secondary" onClick={() => exam && exportCsv(exam, submissions)}>
                        <Icon name="download" size={14}/>导出提交记录
                    </span>
                    <Link className="btn btn-ghost" to={Routes.proctorHome}>
                        <Icon name="arrow-left" size={14}/>切换考试
                    </Link>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                        {" · "}
                        <Link className="link" to={Routes.proctorHome}>返回选择考试</Link>
                    </div>
                </div>
            )}

            {loading && !exam && (
                <div className="card"><div className="card-body muted">加载中…</div></div>
            )}

            {exam && (
                <>
                    <div className="stats-grid">
                        {cards.map(card => (
                            <div className="stat-card" key={card.label}>
                                <div className={"stat-icon" + (card.tone ? " " + card.tone : "")}>
                                    <Icon name={card.icon} size={17}/>
                                </div>
                                <div>
                                    <div className="stat-value">{card.value}</div>
                                    <div className="stat-label">{card.label}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="proctor-main">
                        <div className="card candidate-card">
                            <div className="card-head">
                                <div>
                                    <div className="card-title">考生提交状态</div>
                                    <div className="card-sub">
                                        {exam.openToAll
                                            ? "本场面向全体学生，下表为已有提交的考生"
                                            : "按提交时间倒序；未提交的考生排在后面"}
                                    </div>
                                </div>
                                <div className="table-tools">
                                    <input className="input" placeholder="搜索考生"
                                           style={{ width: 150, height: 28, fontSize: 11.5 }}
                                           value={keyword} onChange={e => setKeyword(e.target.value)}/>
                                </div>
                            </div>
                            <table className="table">
                                <thead>
                                <tr>
                                    <th>考生</th>
                                    <th>提交次数</th>
                                    <th>涉及题目</th>
                                    <th>最近提交</th>
                                    <th>操作</th>
                                </tr>
                                </thead>
                                <tbody>
                                {rows.length === 0 && (
                                    <tr>
                                        <td colSpan={5} className="muted" style={{ textAlign: "center" }}>
                                            {exam.openToAll ? "暂无考生提交" : "没有匹配的考生"}
                                        </td>
                                    </tr>
                                )}
                                {rows.map(row => (
                                    <tr key={row.username}>
                                        <td>
                                            <div className="candidate-name">
                                                <div className="mini-avatar">{row.nickname.slice(0, 1)}</div>
                                                <div>
                                                    <div className="strong">{row.nickname}</div>
                                                    <div className="candidate-sub">{row.username}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            {row.submitCount > 0
                                                ? <span className="strong">{row.submitCount}</span>
                                                : <span className="muted">未提交</span>}
                                        </td>
                                        <td>{row.problemCount > 0 ? `${row.problemCount} / ${exam.problemCount}` : "—"}</td>
                                        <td>{row.lastCreated ? formatDateTime(row.lastCreated) : "—"}</td>
                                        <td>
                                            <span className="link" onClick={() => setFilterStudent(row.username)}>
                                                查看提交
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                            <div className="table-footer">
                                <span>共 {rows.length} 人 · 最近更新 {updatedClock}</span>
                                <span className="muted">每 15 秒自动刷新</span>
                            </div>
                        </div>

                        <div className="alert-side">
                            <div className="card">
                                <div className="card-head">
                                    <div className="card-title">提交动态</div>
                                    <div className="table-tools">
                                        {filterStudent && (
                                            <span className="link" style={{ marginRight: 10 }}
                                                  onClick={() => setFilterStudent(null)}>
                                                清除筛选
                                            </span>
                                        )}
                                        <span className="btn btn-secondary btn-sm" onClick={refreshSubmissions}>
                                            <Icon name="refresh" size={12}/>刷新
                                        </span>
                                    </div>
                                </div>
                                <div className="card-body" style={{ maxHeight: 420, overflowY: "auto" }}>
                                    {filterStudent && (
                                        <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>
                                            只看 {filterStudent} 的提交
                                        </div>
                                    )}
                                    {feed.length === 0 && (
                                        <div className="muted" style={{ fontSize: 11.5 }}>暂无提交记录</div>
                                    )}
                                    {feed.slice(0, 30).map(item => (
                                        <div className="log-item" key={item.id}>
                                            <span className="log-dot green"/>
                                            <div>
                                                <div className="log-text">
                                                    {item.nickname}（{item.username}）提交了「{item.problemTitle}」
                                                </div>
                                                <div className="log-sub">
                                                    {formatDateTime(item.created)} · {item.language} · 待判定
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="card tip-card">
                                <div className="tip-icon"><Icon name="shield-check" size={15}/></div>
                                <div>
                                    <div className="tip-title">异常告警随监考探针接入</div>
                                    <div className="tip-desc">
                                        粘贴检测、窗口切换、断线补时等监考能力依赖考场探针，将在后续迭代提供。
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </TeacherLayout>
    );
}
