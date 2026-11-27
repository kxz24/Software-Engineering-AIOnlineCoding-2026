/**
 * 自由练习接口。
 *
 * 后端见 backend/practice/：开放练习的算法题、练习判题与题目评论区。
 */
import { ApiError, getToken } from "./client";

const PracticeBase = "/api/v1/practice";

export interface PracticeProblemSummary {
    id: number;
    title: string;
    difficulty: "easy" | "medium" | "hard";
    language: string;
    type: "algorithm";
    sampleCount: number;
    testCount: number;
    commentCount: number;
    updated: string | null;
}

export interface PracticeSample {
    name: string;
    input: string;
    expected: string;
}

export interface PracticeProblemDetail extends PracticeProblemSummary {
    description: string;
    starterCode: string;
    timeLimitMs: number;
    samples: PracticeSample[];
}

export interface PracticeCaseResult {
    index: number;
    name: string;
    isSample: boolean;
    verdict: string;
    timeMs: number;
    memoryKb: number;
    outputExcerpt: string;
    errorExcerpt: string;
}

export type PracticeSubmissionStatus = "pending" | "judging" | "judged" | "failed";

export interface PracticeSubmission {
    id: number;
    problemId: number;
    status: PracticeSubmissionStatus;
    verdict: string;
    passedCount: number;
    totalCount: number;
    samplePassed: number;
    sampleTotal: number;
    hiddenPassed: number;
    hiddenTotal: number;
    timeMs: number;
    memoryKb: number;
    results: PracticeCaseResult[];
    compileOutput: string;
    judgeError: string;
    created: string;
    judgedAt: string | null;
}

export interface PracticeComment {
    id: number;
    username: string;
    nickname: string;
    content: string;
    code: string;
    language: string;
    parentId: number | null;
    created: string;
}

async function request<T>(path: string, options: {
    method?: string;
    body?: unknown;
    query?: Record<string, string | undefined>;
} = {}): Promise<T> {
    let url = PracticeBase + path;
    if (options.query) {
        const search = new URLSearchParams();
        Object.keys(options.query).forEach(key => {
            const value = options.query ? options.query[key] : undefined;
            if (value) {
                search.append(key, value);
            }
        });
        const suffix = search.toString();
        if (suffix) {
            url += (url.indexOf("?") >= 0 ? "&" : "?") + suffix;
        }
    }
    let response: Response;
    try {
        response = await fetch(url, {
            method: options.method || "GET",
            headers: {
                "Content-Type": "application/json",
                "Authorization": getToken() || "",
            },
            body: options.body === undefined ? undefined : JSON.stringify(options.body),
        });
    } catch (e) {
        throw new ApiError("无法连接后端服务，请确认已启动后端。", 0);
    }
    const json = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new ApiError((json as { message?: string }).message || "请求失败。", response.status);
    }
    return json as T;
}

export function fetchPracticeProblems(query: {
    keyword?: string;
    difficulty?: string;
    language?: string;
} = {}): Promise<{ problems: PracticeProblemSummary[] }> {
    return request("/problems", { query: { ...query } });
}

export function fetchPracticeProblem(problemId: number): Promise<PracticeProblemDetail> {
    return request(`/problems/${problemId}`);
}

export function submitPracticeCode(
    problemId: number,
    code: string,
    language?: string
): Promise<{ submission: PracticeSubmission }> {
    return request(`/problems/${problemId}/submissions`, {
        method: "POST",
        body: { code, language },
    });
}

export function fetchPracticeSubmission(submissionId: number): Promise<{
    submission: PracticeSubmission;
    problemTitle: string;
}> {
    return request(`/submissions/${submissionId}`);
}

export function fetchPracticeComments(problemId: number): Promise<{ comments: PracticeComment[] }> {
    return request(`/problems/${problemId}/comments`);
}

export function createPracticeComment(
    problemId: number,
    payload: { content: string; code: string; language: string; parentId?: number }
): Promise<{ comment: PracticeComment }> {
    return request(`/problems/${problemId}/comments`, { method: "POST", body: payload });
}

export function deletePracticeComment(commentId: number): Promise<{ message: string }> {
    return request(`/comments/${commentId}`, { method: "DELETE" });
}
