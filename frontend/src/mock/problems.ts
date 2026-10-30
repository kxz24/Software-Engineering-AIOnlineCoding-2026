/**
 * 09 命题与评测配置的演示数据。
 *
 * 后端还没有题目与测试用例接口，这里先按原型（09-problem-config.html）整理一套
 * 三个任务的配置，页面的题目切换、权重与分值都基于这些数据。
 */

/** 测试用例表格的一行 */
export interface TestCaseRow {
    /** 表格「编号」列，如 #01 */
    id: string;
    name: string;
    /** 样例 / 隐藏 */
    kind: "样例" | "隐藏";
    passed: boolean;
    /** 耗时，如 0.12s */
    time: string;
    /** 内存，如 12 MB */
    memory: string;
    /** 是否对考生可见 */
    visible: boolean;
}

/** 评分权重，三项合计对应 100% */
export interface ScoreWeights {
    /** 必过用例（%） */
    mustPass: number;
    /** 加分用例（%） */
    bonus: number;
    /** 代码质量（%） */
    quality: number;
}

/** 运行限制卡片 */
export interface ProblemLimits {
    timeout: string;
    memory: string;
    language: string;
    aiPolicy: string;
}

export interface ProblemDetail {
    id: string;
    /** 任务标题，如「任务 1：修复订单排序并补充测试」 */
    title: string;
    /** 题型徽标 */
    kindLabel: string;
    language: string;
    /** 题面状态徽标 */
    statementStatus: string;
    /** 题面压缩包文件名 */
    packageFile: string;
    /** 本题总分 */
    totalScore: number;
    weights: ScoreWeights;
    /** 样例测试数量 */
    sampleCount: number;
    /** 隐藏测试数量 */
    hiddenCount: number;
    /** 用例总数 */
    totalCases: number;
    /** 表格中展示的用例（原型展示 6 条） */
    cases: TestCaseRow[];
    limits: ProblemLimits;
}

export interface ProblemSet {
    /** 页头副标题里的考试名称 */
    examTitle: string;
    problems: ProblemDetail[];
}

/** 一套与原型逐行一致的配置：任务 1 的用例、权重、限制全部照抄原型 */
const MidTermProblemSet: ProblemSet = {
    examTitle: "软件工程 · 期末机考",
    problems: [
        {
            id: "task-1",
            title: "任务 1：修复订单排序并补充测试",
            kindLabel: "工程题",
            language: "Python 3.11",
            statementStatus: "题面已保存",
            packageFile: "exam-project.zip",
            totalScore: 100,
            weights: { mustPass: 60, bonus: 30, quality: 10 },
            sampleCount: 10,
            hiddenCount: 8,
            totalCases: 18,
            cases: [
                { id: "#01", name: "test_sort_basic", kind: "样例", passed: true, time: "0.12s", memory: "12 MB", visible: true },
                { id: "#02", name: "test_sort_ties", kind: "样例", passed: true, time: "0.10s", memory: "11 MB", visible: true },
                { id: "#03", name: "test_sort_iso", kind: "样例", passed: true, time: "0.11s", memory: "12 MB", visible: true },
                { id: "#04", name: "case_04", kind: "隐藏", passed: true, time: "0.18s", memory: "16 MB", visible: false },
                { id: "#05", name: "case_05", kind: "隐藏", passed: false, time: "0.20s", memory: "18 MB", visible: false },
                { id: "#06", name: "case_06", kind: "隐藏", passed: true, time: "0.17s", memory: "15 MB", visible: false },
            ],
            limits: {
                timeout: "2.0 s",
                memory: "256 MB",
                language: "Python 3.11",
                aiPolicy: "继承考试：受限",
            },
        },
        {
            id: "task-2",
            title: "任务 2：补全库存扣减的事务与回滚",
            kindLabel: "工程题",
            language: "Python 3.11",
            statementStatus: "题面已保存",
            packageFile: "exam-project.zip",
            totalScore: 100,
            weights: { mustPass: 70, bonus: 20, quality: 10 },
            sampleCount: 12,
            hiddenCount: 6,
            totalCases: 18,
            cases: [
                { id: "#01", name: "test_reserve_basic", kind: "样例", passed: true, time: "0.09s", memory: "10 MB", visible: true },
                { id: "#02", name: "test_reserve_shortage", kind: "样例", passed: true, time: "0.11s", memory: "11 MB", visible: true },
                { id: "#03", name: "test_rollback_on_error", kind: "样例", passed: false, time: "0.14s", memory: "13 MB", visible: true },
                { id: "#04", name: "case_04", kind: "隐藏", passed: true, time: "0.16s", memory: "15 MB", visible: false },
                { id: "#05", name: "case_05", kind: "隐藏", passed: true, time: "0.19s", memory: "17 MB", visible: false },
                { id: "#06", name: "case_06", kind: "隐藏", passed: false, time: "0.21s", memory: "19 MB", visible: false },
            ],
            limits: {
                timeout: "3.0 s",
                memory: "512 MB",
                language: "Python 3.11",
                aiPolicy: "继承考试：受限",
            },
        },
        {
            id: "task-3",
            title: "任务 3：重构日志模块并修复并发写入",
            kindLabel: "工程题",
            language: "Python 3.11",
            statementStatus: "题面待补充",
            packageFile: "exam-project.zip",
            totalScore: 100,
            weights: { mustPass: 50, bonus: 40, quality: 10 },
            sampleCount: 8,
            hiddenCount: 10,
            totalCases: 18,
            cases: [
                { id: "#01", name: "test_log_format", kind: "样例", passed: true, time: "0.08s", memory: "9 MB", visible: true },
                { id: "#02", name: "test_log_concurrent", kind: "样例", passed: false, time: "0.22s", memory: "20 MB", visible: true },
                { id: "#03", name: "test_log_rotate", kind: "样例", passed: true, time: "0.13s", memory: "14 MB", visible: true },
                { id: "#04", name: "case_04", kind: "隐藏", passed: true, time: "0.17s", memory: "16 MB", visible: false },
                { id: "#05", name: "case_05", kind: "隐藏", passed: true, time: "0.18s", memory: "16 MB", visible: false },
                { id: "#06", name: "case_06", kind: "隐藏", passed: true, time: "0.15s", memory: "14 MB", visible: false },
            ],
            limits: {
                timeout: "2.0 s",
                memory: "256 MB",
                language: "Python 3.11",
                aiPolicy: "继承考试：受限",
            },
        },
    ],
};

const ProblemSets: Record<string, ProblemSet> = {
    "exam-mid-2026": MidTermProblemSet,
};

/** 按考试取题目配置，找不到时退化为期中机考这套演示数据 */
export function findProblemSet(examId: string | undefined): ProblemSet {
    return (examId && ProblemSets[examId]) || MidTermProblemSet;
}
