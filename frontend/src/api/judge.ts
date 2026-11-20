/**
 * 判题状态与判定结果的展示映射。
 *
 * 后端提交状态：pending / judging / judged / failed
 * 判定结果：accepted / partial / wrong_answer / *_exceeded / runtime_error /
 *          compile_error / system_error
 */

export interface VerdictMeta {
    label: string;
    tone: "green" | "amber" | "red" | "gray" | "blue";
}

const Verdicts: Record<string, VerdictMeta> = {
    pending: { label: "待判定", tone: "gray" },
    judging: { label: "判题中", tone: "amber" },
    accepted: { label: "通过", tone: "green" },
    partial: { label: "部分通过", tone: "amber" },
    wrong_answer: { label: "未通过", tone: "red" },
    time_limit_exceeded: { label: "超时", tone: "red" },
    memory_limit_exceeded: { label: "内存超限", tone: "red" },
    output_limit_exceeded: { label: "输出超限", tone: "red" },
    runtime_error: { label: "运行错误", tone: "red" },
    compile_error: { label: "编译错误", tone: "red" },
    system_error: { label: "系统错误", tone: "gray" },
    failed: { label: "判题失败", tone: "red" },
};

export function verdictMeta(key: string | null | undefined): VerdictMeta {
    return Verdicts[key || ""] || { label: key || "未知", tone: "gray" };
}

/** 提交状态优先按 verdict 展示；未判完时展示 pending / judging。 */
export function submissionLabel(submission: {
    status: string;
    verdict?: string;
}): VerdictMeta {
    if (submission.status === "judged" && submission.verdict) {
        return verdictMeta(submission.verdict);
    }
    if (submission.status === "failed") {
        return { label: "判题失败", tone: "red" };
    }
    return verdictMeta(submission.status);
}

export function isPending(status: string | null | undefined): boolean {
    return status === "pending" || status === "judging";
}
