/**
 * 考试相关的前端演示数据。
 *
 * 后端目前只提供登录 / 登出 / 用户信息三个接口，考试、题目、成绩等
 * 数据先在前端集中放在这里，后续接口就绪后逐个替换成真实请求即可。
 */

/** AI 使用模式：受限 / 开放 / 关闭 */
export type AiMode = "limited" | "open" | "closed";

/** 考试状态 */
export type ExamStatus = "upcoming" | "ongoing" | "finished";

export interface ExamSummary {
    id: string;
    /** 考试名称 */
    title: string;
    /** 表头副标题，如「3 道工程题 · 45 人」 */
    sub: string;
    /** 列表中的时间列，如「10-25 14:00」 */
    dateLabel: string;
    /** 详情中的时间段，如「10月25日 14:00–16:00」 */
    periodLabel: string;
    durationMinutes: number;
    aiMode: AiMode;
    status: ExamStatus;
    problemCount: number;
    candidates: number;
    /** 已完成考试的得分 */
    score?: number;
}

export const AiModeLabels: Record<AiMode, string> = {
    limited: "受限",
    open: "开放",
    closed: "关闭",
};

export const ExamStatusLabels: Record<ExamStatus, string> = {
    upcoming: "待考",
    ongoing: "进行中",
    finished: "已完成",
};

/** 我的考试列表 */
export const mockExams: ExamSummary[] = [
    {
        id: "exam-mid-2026",
        title: "软件工程 · 期中机考",
        sub: "3 道工程题 · 45 人",
        dateLabel: "10-25 14:00",
        periodLabel: "10月25日 14:00–16:00",
        durationMinutes: 120,
        aiMode: "limited",
        status: "upcoming",
        problemCount: 3,
        candidates: 45,
    },
    {
        id: "exam-ds-quiz-3",
        title: "数据结构 · 随堂测验 3",
        sub: "2 道算法题 · 42 人",
        dateLabel: "10-18 10:00",
        periodLabel: "10月18日 10:00–10:45",
        durationMinutes: 45,
        aiMode: "closed",
        status: "finished",
        problemCount: 2,
        candidates: 42,
        score: 92,
    },
    {
        id: "exam-algo-unit",
        title: "算法设计 · 单元测试",
        sub: "1 道工程题 · 38 人",
        dateLabel: "10-11 14:00",
        periodLabel: "10月11日 14:00–15:00",
        durationMinutes: 60,
        aiMode: "open",
        status: "finished",
        problemCount: 1,
        candidates: 38,
        score: 88,
    },
    {
        id: "exam-se-hw-2",
        title: "软件工程 · 作业 2",
        sub: "1 道工程题 · 45 人",
        dateLabel: "09-27 19:00",
        periodLabel: "09月27日 19:00–20:30",
        durationMinutes: 90,
        aiMode: "limited",
        status: "finished",
        problemCount: 1,
        candidates: 45,
        score: 80,
    },
];

/** 默认展示的考试（首页英雄区、各类示例链接都指向它） */
export const featuredExam = mockExams[0];

/** 按 id 取考试，找不到时退化为默认考试，保证页面不会白屏 */
export function findExam(examId: string | undefined): ExamSummary {
    return mockExams.find(exam => exam.id === examId) || featuredExam;
}

/** 待考考试数量 */
export function countByStatus(status: ExamStatus): number {
    return mockExams.filter(exam => exam.status === status).length;
}

/** 已完成考试的平均分 */
export function averageScore(): number {
    const scored = mockExams.filter(exam => exam.score != null);
    if (scored.length === 0) {
        return 0;
    }
    const total = scored.reduce((sum, exam) => sum + (exam.score || 0), 0);
    return Math.round((total / scored.length) * 10) / 10;
}

const Weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

/** 今天的中文日期，如「2026年10月25日 周日」 */
export function formatToday(now: Date = new Date()): string {
    return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${Weekdays[now.getDay()]}`;
}

/** 秒数格式化为 HH:MM:SS */
export function formatCountdown(totalSeconds: number): string {
    const safe = Math.max(0, totalSeconds);
    const hours = Math.floor(safe / 3600);
    const minutes = Math.floor((safe % 3600) / 60);
    const seconds = safe % 60;
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

/**
 * 演示用的开考时间：今天 14:00；若已过点则顺延到明天 14:00。
 * 用于首页英雄区的倒计时，真实接口就绪后改成考试的开始时间。
 */
export function nextExamStart(now: Date = new Date()): Date {
    const start = new Date(now);
    start.setHours(14, 0, 0, 0);
    if (start.getTime() <= now.getTime()) {
        start.setDate(start.getDate() + 1);
    }
    return start;
}
