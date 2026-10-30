import React from "react";
import { Link, useParams } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon, IconName } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { findExam } from "../../mock/exams";

interface ProctorStat {
    icon: IconName;
    /** 图标底色修饰类，空字符串为默认蓝色 */
    tone: "" | "green" | "amber" | "red";
    value: string;
    label: string;
    /** 右侧补充说明，仅告警卡片有 */
    trend?: string;
    trendTone?: "green" | "red";
}

const ProctorStats: ProctorStat[] = [
    { icon: "users", tone: "green", value: "42 / 45", label: "在线考生" },
    { icon: "check-circle", tone: "", value: "38", label: "已提交" },
    { icon: "alert-triangle", tone: "red", value: "3", label: "异常告警", trend: "1 高 · 1 中 · 1 低", trendTone: "red" },
    { icon: "clock", tone: "amber", value: "01:27:34", label: "剩余时间" },
];

interface CandidateRow {
    name: string;
    studentNo: string;
    /** 状态文案与配色，沿用原型的 badge 修饰类 */
    status: string;
    statusTone: "blue" | "green" | "amber";
    progress: string;
    submitCount: number;
    aiRounds: string;
    /** 有告警的考生才显示「处置」入口，无告警显示「查看」 */
    alert?: { text: string; tone: "red" | "amber" };
}

const Candidates: CandidateRow[] = [
    { name: "李同学", studentNo: "2023012345", status: "作答中", statusTone: "blue", progress: "任务 1 / 3", submitCount: 1, aiRounds: "6 轮" },
    {
        name: "王同学", studentNo: "2023012388", status: "作答中", statusTone: "blue", progress: "任务 1 / 3",
        submitCount: 0, aiRounds: "2 轮", alert: { text: "高 1", tone: "red" },
    },
    { name: "陈同学", studentNo: "2023012301", status: "已提交", statusTone: "green", progress: "3 / 3", submitCount: 2, aiRounds: "12 轮" },
    {
        name: "赵同学", studentNo: "2023012322", status: "断线重连", statusTone: "amber", progress: "任务 2 / 3",
        submitCount: 1, aiRounds: "4 轮", alert: { text: "低 1", tone: "amber" },
    },
    {
        name: "孙同学", studentNo: "2023012340", status: "作答中", statusTone: "blue", progress: "任务 1 / 3",
        submitCount: 0, aiRounds: "0 轮", alert: { text: "中 1", tone: "amber" },
    },
    { name: "周同学", studentNo: "2023012356", status: "作答中", statusTone: "blue", progress: "任务 2 / 3", submitCount: 1, aiRounds: "8 轮" },
    { name: "吴同学", studentNo: "2023012367", status: "作答中", statusTone: "blue", progress: "任务 1 / 3", submitCount: 0, aiRounds: "3 轮" },
    { name: "郑同学", studentNo: "2023012379", status: "已提交", statusTone: "green", progress: "3 / 3", submitCount: 2, aiRounds: "10 轮" },
    { name: "冯同学", studentNo: "2023012384", status: "作答中", statusTone: "blue", progress: "任务 2 / 3", submitCount: 1, aiRounds: "5 轮" },
    { name: "褚同学", studentNo: "2023012391", status: "作答中", statusTone: "blue", progress: "任务 1 / 3", submitCount: 0, aiRounds: "1 轮" },
];

interface AlertButton {
    label: string;
    /** 红色按钮用于不可逆操作 */
    danger?: boolean;
    /** 点击前的二次确认文案，为空则直接执行 */
    confirm?: string;
    /** 执行后的轻提示 */
    message: string;
}

interface AlertItem {
    level: "high" | "medium" | "low";
    badge: string;
    badgeTone: "red" | "amber" | "gray";
    time: string;
    title: string;
    desc: string;
    buttons: AlertButton[];
}

const AlertItems: AlertItem[] = [
    {
        level: "high",
        badge: "高",
        badgeTone: "red",
        time: "14:41:08",
        title: "王同学 · 粘贴大段代码",
        desc: "检测到 120 行剪贴板内容，已生成代码快照 #17。",
        buttons: [
            { label: "查看证据", message: "已打开代码快照 #17 的剪贴板证据" },
            {
                label: "终止考试",
                danger: true,
                confirm: "终止后王同学将无法继续作答，确定终止其考试吗？",
                message: "已终止王同学的考试",
            },
        ],
    },
    {
        level: "medium",
        badge: "中",
        badgeTone: "amber",
        time: "14:36:20",
        title: "赵同学 · 网络中断 42s",
        desc: "已自动重连并恢复到快照 #14；可考虑补时。",
        buttons: [
            { label: "补时 2 分钟", message: "已为赵同学补时 2 分钟" },
            { label: "查看", message: "已打开赵同学的告警详情" },
        ],
    },
    {
        level: "low",
        badge: "低",
        badgeTone: "gray",
        time: "14:28:05",
        title: "孙同学 · 窗口切换 3 次",
        desc: "切出考试页面 3 次，每次不足 5 秒；暂无外部模型调用。",
        buttons: [
            { label: "忽略", message: "已忽略孙同学的窗口切换告警" },
            { label: "查看", message: "已打开孙同学的告警详情" },
        ],
    },
];

const HandleLogs: { text: string; sub: string }[] = [
    { text: "14:36 为赵同学补时 2 分钟", sub: "理由：网络中断 42 秒 · 助教 张" },
    { text: "14:30 警告王同学：请勿粘贴外部代码", sub: "处置人：监考 刘" },
    { text: "14:10 重新分配容器给陈同学", sub: "原因：容器启动超时 · 自动恢复" },
];

/** 10 监考中心：在线考生状态、异常告警与处置记录 */
export function ProctorPage() {
    const { examId } = useParams<{ examId: string }>();
    const exam = findExam(examId);

    // 结束考试是不可逆操作，先在浏览器里二次确认，取消时拦下跳转
    const handleEndExam = (event: React.MouseEvent<HTMLAnchorElement>) => {
        if (!window.confirm("结束后考生将无法继续作答，确定结束本场考试吗？")) {
            event.preventDefault();
        }
    };

    // 告警处置按钮：需要确认的先弹窗，确认后给出轻提示
    const handleAlertButton = (button: AlertButton) => {
        if (button.confirm && !window.confirm(button.confirm)) {
            return;
        }
        toast(button.message, button.danger ? "warning" : "info");
    };

    return (
        <TeacherLayout breadcrumb={["工作台", "软件工程 · 2026 秋", "监考中心"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">监考中心</div>
                    <div className="page-sub">{exam.title} · 进行中 · 14:32:26</div>
                </div>
                <div className="page-actions">
                    <span className="btn btn-secondary" onClick={() => toast("异常记录已导出")}>
                        <Icon name="download" size={14}/>导出异常记录
                    </span>
                    <Link className="btn btn-danger" to={Routes.examManage} onClick={handleEndExam}>
                        结束考试
                    </Link>
                </div>
            </div>

            {/* 本场考试的四项实时指标 */}
            <div className="stats-grid">
                {ProctorStats.map(stat => (
                    <div className="stat-card" key={stat.label}>
                        <div className={"stat-icon" + (stat.tone ? " " + stat.tone : "")}>
                            <Icon name={stat.icon} size={17}/>
                        </div>
                        <div>
                            <div className="stat-value">{stat.value}</div>
                            <div className="stat-label">{stat.label}</div>
                        </div>
                        {stat.trend && (
                            <span className={"stat-trend " + (stat.trendTone || "")}>{stat.trend}</span>
                        )}
                    </div>
                ))}
            </div>

            <div className="proctor-main">
                <div className="card candidate-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">考生状态</div>
                            <div className="card-sub">按告警级别与进度排序</div>
                        </div>
                        <div className="table-tools">
                            <span className="search-box"><Icon name="search" size={13}/>搜索考生</span>
                            <span className="btn btn-secondary btn-sm" onClick={() => toast("筛选面板尚未接入")}>
                                <Icon name="filter" size={12}/>筛选
                            </span>
                        </div>
                    </div>
                    <table className="table">
                        <thead>
                        <tr>
                            <th>考生</th>
                            <th>状态</th>
                            <th>进度</th>
                            <th>提交</th>
                            <th>AI 对话</th>
                            <th>告警</th>
                            <th>操作</th>
                        </tr>
                        </thead>
                        <tbody>
                        {Candidates.map(candidate => (
                            <tr key={candidate.studentNo}>
                                <td>
                                    <div className="candidate-name">
                                        <div className="mini-avatar">{candidate.name.slice(0, 1)}</div>
                                        <div>
                                            <div className="strong">{candidate.name}</div>
                                            <div className="candidate-sub">{candidate.studentNo}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <span className={"badge " + candidate.statusTone}>{candidate.status}</span>
                                </td>
                                <td>{candidate.progress}</td>
                                <td>{candidate.submitCount}</td>
                                <td>{candidate.aiRounds}</td>
                                <td>
                                    {candidate.alert
                                        ? <span className={"badge " + candidate.alert.tone}>{candidate.alert.text}</span>
                                        : <span className="muted">—</span>}
                                </td>
                                <td>
                                    {candidate.alert
                                        ? <span className="link"
                                                onClick={() => toast("已通知监考处置 " + candidate.name)}>处置</span>
                                        : <Link className="link" to={Routes.examReport(examId)}>查看</Link>}
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    <div className="table-footer">
                        <span>在线 42 / 45 · 最近更新 14:32:26</span>
                        <span className="link" onClick={() => toast("考生名单尚未接入")}>查看全部考生</span>
                    </div>
                </div>

                <div className="alert-side">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">异常告警</div>
                            <span className="badge red">1 高 · 1 中 · 1 低</span>
                        </div>
                        <div className="card-body">
                            {AlertItems.map((alert, index) => (
                                <div key={alert.time}
                                     className={"alert-item " + alert.level
                                         + (index === AlertItems.length - 1 ? " last" : "")}>
                                    <div className="alert-top">
                                        <span className={"badge " + alert.badgeTone}>{alert.badge}</span>
                                        <span className="alert-time">{alert.time}</span>
                                    </div>
                                    <div className="alert-title">{alert.title}</div>
                                    <div className="alert-desc">{alert.desc}</div>
                                    <div className="alert-actions">
                                        {alert.buttons.map(button => (
                                            <span key={button.label}
                                                  className={"btn btn-sm " + (button.danger ? "btn-danger" : "btn-secondary")}
                                                  onClick={() => handleAlertButton(button)}>
                                                {button.label}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">处置记录</div>
                            <span className="link" onClick={() => toast("全部处置记录尚未接入")}>查看全部</span>
                        </div>
                        <div className="card-body">
                            {HandleLogs.map((log, index) => (
                                <div key={log.text}
                                     className={"log-item" + (index === HandleLogs.length - 1 ? " last" : "")}>
                                    <span className="log-dot"/>
                                    <div>
                                        <div className="log-text">{log.text}</div>
                                        <div className="log-sub">{log.sub}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </TeacherLayout>
    );
}
