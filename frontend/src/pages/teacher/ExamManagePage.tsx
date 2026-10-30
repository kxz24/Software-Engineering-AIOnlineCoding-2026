import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import {
    ExamRowAction,
    ManageStatusMeta,
    ManageTab,
    ManageTabs,
    manageExams,
    manageStats,
} from "../../mock/examManage";

const TableHeads = ["考试名称", "状态", "考试时间", "考生", "提交", "AI 模式", "操作"];

const PagerLabels = ["1", "2", "下一页"];

/** 行内操作：编辑 / 监考 / 报告 跳转，其余按钮统一用 toast 反馈 */
function ExamAction({ examId, action }: { examId: string; action: ExamRowAction }) {
    if (action.kind === "toast") {
        return <span className="link" onClick={() => toast(action.message)}>{action.label}</span>;
    }

    const to = action.kind === "edit"
        ? Routes.problemConfig(examId)
        : action.kind === "proctor"
            ? Routes.proctor(examId)
            : Routes.examReport(examId);
    return <Link className="link" to={to}>{action.label}</Link>;
}

/** 07 考试管理：教师端考试列表、状态筛选与行内操作入口 */
export function ExamManagePage() {
    const [tab, setTab] = useState<ManageTab>("list");

    // 三个页签各自展示一组考试：列表排除归档，成绩分析只看已结束，归档只看已归档
    const visibleExams = useMemo(() => {
        if (tab === "scores") {
            return manageExams.filter(exam => exam.status === "finished");
        }
        if (tab === "archive") {
            return manageExams.filter(exam => exam.status === "archived");
        }
        return manageExams.filter(exam => exam.status !== "archived");
    }, [tab]);

    return (
        <TeacherLayout breadcrumb={["工作台", "软件工程 · 2026 秋", "考试管理"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">考试管理</div>
                    <div className="page-sub">创建、发布与归档课程考试</div>
                </div>
                <div className="page-actions">
                    <button type="button"
                            className="btn btn-secondary"
                            onClick={() => toast("导入考生名单功能开发中")}>
                        <Icon name="users" size={14}/>导入考生名单
                    </button>
                    <Link className="btn btn-primary" to={Routes.examCreate}>
                        <Icon name="plus" size={14}/>创建考试
                    </Link>
                </div>
            </div>

            {/* 概览数据 */}
            <div className="stats-grid">
                {manageStats.map(stat => (
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
                        {ManageTabs.map(item => (
                            <span key={item.key}
                                  className={"tab" + (tab === item.key ? " active" : "")}
                                  onClick={() => setTab(item.key)}>
                                {item.label}
                            </span>
                        ))}
                    </div>
                    <div className="table-tools">
                        <span className="search-box"><Icon name="search" size={14}/>搜索考试</span>
                        <span className="icon-btn" title="筛选" onClick={() => toast("筛选条件已展开")}>
                            <Icon name="filter" size={15}/>
                        </span>
                    </div>
                </div>
                <table className="table">
                    <thead>
                    <tr>
                        {TableHeads.map(head => <th key={head}>{head}</th>)}
                    </tr>
                    </thead>
                    <tbody>
                    {visibleExams.map(exam => (
                        <tr key={exam.id}>
                            <td>
                                <div className="strong">{exam.title}</div>
                                <div className="sub">{exam.sub}</div>
                            </td>
                            <td>
                                <span className={"badge " + ManageStatusMeta[exam.status].badge}>
                                    {ManageStatusMeta[exam.status].label}
                                </span>
                            </td>
                            <td>{exam.timeLabel}</td>
                            <td>{exam.candidates}</td>
                            <td className={exam.submissions == null ? "muted" : undefined}>
                                {exam.submissions == null ? "—" : exam.submissions}
                            </td>
                            <td>{exam.aiModeLabel}</td>
                            <td>
                                {exam.actions.map((action, index) => (
                                    <React.Fragment key={action.label}>
                                        {index > 0 && <span className="muted"> · </span>}
                                        <ExamAction examId={exam.id} action={action}/>
                                    </React.Fragment>
                                ))}
                            </td>
                        </tr>
                    ))}
                    {visibleExams.length === 0 && (
                        <tr>
                            <td colSpan={TableHeads.length} className="muted" style={{ textAlign: "center" }}>
                                暂无考试
                            </td>
                        </tr>
                    )}
                    </tbody>
                </table>
                <div className="table-footer">
                    <span>共 {manageExams.length} 场考试 · 当前显示 {visibleExams.length} 场</span>
                    <span className="pager">
                        {PagerLabels.map((label, index) => (
                            <span key={label}
                                  className={"page-btn" + (index === 0 ? " active" : "")}
                                  onClick={() => toast(label === "下一页" ? "已切换到下一页" : `已切换到第 ${label} 页`)}>
                                {label}
                            </span>
                        ))}
                    </span>
                </div>
            </div>
        </TeacherLayout>
    );
}
