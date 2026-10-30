/**
 * 教师端「考试管理」页（07）的演示数据。
 *
 * 学生端的考试安排放在 mock/exams.ts；这里保存管理表格需要的状态、
 * 提交进度与行内操作，后续接口就绪后整体替换成真实请求。
 */

import { IconName } from "../components/Icon";

/** 管理列表里的考试状态 */
export type ManageExamStatus = "ongoing" | "draft" | "finished" | "archived";

/** 行内操作：跳转类操作与 toast 占位操作 */
export type ExamRowAction =
    | { label: string; kind: "edit" | "proctor" | "report" }
    | { label: string; kind: "toast"; message: string };

export interface ManageExam {
    id: string;
    title: string;
    /** 表格第二行的课程与题量说明 */
    sub: string;
    status: ManageExamStatus;
    /** 考试时间列，如「10-25 14:00–16:00」 */
    timeLabel: string;
    candidates: number;
    /** 提交进度；草稿没有提交数据，表格显示「—」 */
    submissions?: string;
    aiModeLabel: string;
    actions: ExamRowAction[];
}

/** 状态对应的徽章文案与颜色 */
export const ManageStatusMeta: Record<ManageExamStatus, { label: string; badge: string }> = {
    ongoing: { label: "进行中", badge: "green" },
    draft: { label: "草稿", badge: "gray" },
    finished: { label: "已结束", badge: "gray" },
    archived: { label: "已归档", badge: "gray" },
};

/** 管理卡片顶部的三个页签 */
export type ManageTab = "list" | "scores" | "archive";

export const ManageTabs: { key: ManageTab; label: string }[] = [
    { key: "list", label: "考试列表" },
    { key: "scores", label: "成绩分析" },
    { key: "archive", label: "归档" },
];

/** 顶部统计卡片 */
export interface ManageStat {
    icon: IconName;
    /** stat-icon 的颜色修饰，空字符串表示默认蓝色 */
    tone: "" | "green" | "amber" | "purple";
    value: string;
    label: string;
    trend: string;
}

export const manageStats: ManageStat[] = [
    { icon: "play", tone: "green", value: "1", label: "进行中", trend: "1 场" },
    { icon: "file-text", tone: "amber", value: "3", label: "待发布", trend: "草稿" },
    { icon: "check-circle", tone: "", value: "5", label: "已归档", trend: "本学期" },
    { icon: "users", tone: "purple", value: "45", label: "考生人数", trend: "软件工程" },
];

/**
 * 管理表格数据：前 7 条是占用的「考试列表」，最后一条归档考试只在
 * 「归档」页签出现，因此初始视图仍是原型的 7 行。
 */
export const manageExams: ManageExam[] = [
    {
        id: "exam-mid-2026",
        title: "软件工程 · 期中机考",
        sub: "2026 秋 · 3 道工程题",
        status: "ongoing",
        timeLabel: "10-25 14:00–16:00",
        candidates: 45,
        submissions: "38 / 90",
        aiModeLabel: "受限",
        actions: [
            { label: "监考", kind: "proctor" },
            { label: "更多", kind: "toast", message: "更多操作功能开发中" },
        ],
    },
    {
        id: "exam-final-2026",
        title: "软件工程 · 期末机考",
        sub: "2026 秋 · 3 道工程题",
        status: "draft",
        timeLabel: "11-08 09:00–11:00",
        candidates: 45,
        aiModeLabel: "受限",
        actions: [
            { label: "编辑", kind: "edit" },
            { label: "发布", kind: "toast", message: "考试已发布" },
        ],
    },
    {
        id: "exam-se-hw-3",
        title: "软件工程 · 作业 3",
        sub: "2026 秋 · 1 道工程题",
        status: "draft",
        timeLabel: "11-01 19:00–20:30",
        candidates: 45,
        aiModeLabel: "受限",
        actions: [
            { label: "编辑", kind: "edit" },
            { label: "发布", kind: "toast", message: "考试已发布" },
        ],
    },
    {
        id: "exam-ds-quiz-3",
        title: "数据结构 · 随堂测验 3",
        sub: "2026 秋 · 2 道算法题",
        status: "finished",
        timeLabel: "10-18 10:00–10:45",
        candidates: 42,
        submissions: "42 / 42",
        aiModeLabel: "关闭",
        actions: [
            { label: "报告", kind: "report" },
            { label: "归档", kind: "toast", message: "考试已归档" },
        ],
    },
    {
        id: "exam-algo-unit",
        title: "算法设计 · 单元测试",
        sub: "2026 秋 · 1 道工程题",
        status: "finished",
        timeLabel: "10-11 14:00–15:00",
        candidates: 38,
        submissions: "38 / 38",
        aiModeLabel: "开放",
        actions: [
            { label: "报告", kind: "report" },
            { label: "归档", kind: "toast", message: "考试已归档" },
        ],
    },
    {
        id: "exam-se-hw-2",
        title: "软件工程 · 作业 2",
        sub: "2026 秋 · 1 道工程题",
        status: "finished",
        timeLabel: "09-27 19:00–20:30",
        candidates: 45,
        submissions: "45 / 45",
        aiModeLabel: "受限",
        actions: [
            { label: "报告", kind: "report" },
            { label: "归档", kind: "toast", message: "考试已归档" },
        ],
    },
    {
        id: "exam-algo-final",
        title: "算法设计 · 期末机考",
        sub: "2026 秋 · 3 道题",
        status: "draft",
        timeLabel: "11-15 09:00–11:00",
        candidates: 38,
        aiModeLabel: "开放",
        actions: [
            { label: "编辑", kind: "edit" },
            { label: "发布", kind: "toast", message: "考试已发布" },
        ],
    },
    {
        id: "exam-se-hw-1",
        title: "软件工程 · 作业 1",
        sub: "2026 秋 · 1 道工程题",
        status: "archived",
        timeLabel: "09-13 19:00–20:30",
        candidates: 45,
        submissions: "45 / 45",
        aiModeLabel: "受限",
        actions: [
            { label: "报告", kind: "report" },
            { label: "更多", kind: "toast", message: "该考试已在归档中" },
        ],
    },
];
