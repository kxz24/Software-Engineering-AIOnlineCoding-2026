import { Urls } from "./urls";
import { Role } from "../roles";

/** 当前登录用户的信息 */
export interface UserSelf {
    id: number;
    username: string;
    nickname: string;
    role: Role;
    created: string;
}

/** 登录接口成功时的返回体 */
export interface LoginResult {
    jwt: string;
    userId: number;
    username: string;
    nickname: string;
    role: Role;
}

export type LoginResponse =
    | ({ success: true } & LoginResult)
    | { success: false; message: string };

export type UserResponse =
    | { success: true, user: UserSelf }
    | { success: false, authorized: boolean, message: string };

export type LogoutResponse =
    | { success: true }
    | { success: false, message: string };

/** 注册接口与登录返回同样的载荷（注册即登录），复用同一类型 */
export type RegisterResponse = LoginResponse;

/**
 * 读取响应体 JSON。服务端返回非 JSON 时退化为一个带错误信息的对象，
 * 避免 JSON.parse 抛异常导致界面卡死。
 */
async function readJson(response: Response): Promise<any> {
    try {
        return await response.json();
    } catch (e) {
        return { "message": "服务返回了非预期的内容，请稍后重试。" };
    }
}

/**
 * 登录。
 * 成功后会把 JWT 写入 localStorage，后续请求在 Authorization 头里带上。
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
    const response = await fetch(Urls.login, {
        "method": "PATCH",
        "mode": "cors",
        "headers": {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password })
    });
    const json = await readJson(response);

    if (response.status !== 200 || json.jwt == null || json.role == null) {
        return {
            "success": false,
            "message": json.message || "账号或密码不正确。",
        };
    }

    setToken(json.jwt);
    return {
        "success": true,
        "jwt": json.jwt,
        "userId": json.userId,
        "username": json.username,
        "nickname": json.nickname,
        "role": json.role,
    };
}

/**
 * 注册。
 * 后端在注册成功时直接下发 JWT（注册即登录），这里同样写入 localStorage。
 */
export async function register(
    username: string,
    password: string,
    nickname: string,
    role: Role
): Promise<RegisterResponse> {
    const response = await fetch(Urls.register, {
        "method": "POST",
        "mode": "cors",
        "headers": {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password, nickname, role })
    });
    const json = await readJson(response);

    if (response.status !== 201 || json.jwt == null || json.role == null) {
        return {
            "success": false,
            "message": json.message || "注册失败，请稍后重试。",
        };
    }

    setToken(json.jwt);
    return {
        "success": true,
        "jwt": json.jwt,
        "userId": json.userId,
        "username": json.username,
        "nickname": json.nickname,
        "role": json.role,
    };
}

/**
 * 登出。
 * 后端为无状态 JWT，这里只负责清掉本地令牌。
 */
export async function logout(): Promise<LogoutResponse> {
    const response = await fetch(Urls.logout, {
        "method": "PATCH",
        "mode": "cors",
        "headers": {
            "Authorization": getToken() || "",
        }
    });
    const json = await readJson(response);
    removeToken();

    if (response.status !== 200) {
        return { "success": false, "message": json.message || "登出失败。" };
    }
    return { "success": true };
}

/**
 * 获取当前登录用户信息（含角色）。
 */
export async function fetchUser(): Promise<UserResponse> {
    const response = await fetch(Urls.user, {
        "method": "GET",
        "mode": "cors",
        "headers": {
            "Authorization": getToken() || "",
        }
    });
    const json = await readJson(response);

    if (response.status !== 200) {
        return {
            "success": false,
            "authorized": response.status !== 401,
            "message": json.message || "获取用户信息失败。",
        };
    }
    return { "success": true, "user": json };
}

/** 是否已持有令牌 */
export function isAuthenticated(): boolean {
    return !!localStorage.getItem("token");
}

// ---------------------------------------------------------------------------
// 账号管理与题库（管理端 CRUD）。
// 与登录类的「联合类型返回」不同，这里统一抛 ApiError，由页面 catch 后提示，
// 避免每个接口都写一遍 success 判别。
// ---------------------------------------------------------------------------

/** 带 status 的请求错误；status 为 0 表示请求根本没发出去（后端未启动等） */
export class ApiError extends Error {
    readonly status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
    }
}

/** 连接失败 / 非 JSON 响应的统一文案 */
export const NetworkErrorMessage =
    "无法连接后端服务，请确认已启动后端（默认 127.0.0.1:8000）。";

/**
 * 管理端请求入口：自动带 Authorization 头与 JSON 序列化，
 * 非 2xx 一律抛 ApiError（async 函数保证不会同步抛出，页面 catch 即可）。
 */
async function request<T>(
    url: string,
    options: {
        method?: string;
        body?: unknown;
        query?: Record<string, string | undefined>;
    } = {}
): Promise<T> {
    if (typeof fetch !== "function") {
        // 测试环境（jsdom）没有 fetch，统一走错误分支
        throw new ApiError(NetworkErrorMessage, 0);
    }
    let fullUrl = url;
    if (options.query) {
        const search = new URLSearchParams();
        Object.keys(options.query).forEach(key => {
            const value = options.query ? options.query[key] : undefined;
            if (value) {
                search.append(key, value);
            }
        });
        const queryString = search.toString();
        if (queryString) {
            fullUrl += (url.indexOf("?") >= 0 ? "&" : "?") + queryString;
        }
    }
    let response: Response;
    try {
        response = await fetch(fullUrl, {
            method: options.method || "GET",
            mode: "cors",
            headers: {
                "Content-Type": "application/json",
                "Authorization": getToken() || "",
            },
            body: options.body === undefined ? undefined : JSON.stringify(options.body),
        });
    } catch (e) {
        throw new ApiError(NetworkErrorMessage, 0);
    }
    const json = await readJson(response);
    if (!response.ok) {
        throw new ApiError(json.message || "请求失败。", response.status);
    }
    return json as T;
}

/** 管理端看到的账号信息（比 UserSelf 多邮箱） */
export interface AdminUser {
    id: number;
    username: string;
    nickname: string;
    email: string;
    role: Role;
    created: string;
}

export interface UserListQuery {
    role?: string;
    keyword?: string;
}

/** 账号列表（管理员） */
export function fetchUsers(query: UserListQuery = {}): Promise<{ users: AdminUser[] }> {
    return request(Urls.users, {
        query: { role: query.role, keyword: query.keyword },
    });
}

/** 创建账号（管理员，可建教师 / 管理员） */
export function adminCreateUser(payload: {
    username: string;
    nickname: string;
    password: string;
    role: Role;
    email?: string;
}): Promise<AdminUser> {
    return request(Urls.users, { method: "POST", body: payload });
}

/** 编辑账号：改姓名 / 角色 / 重置密码 / 邮箱（管理员） */
export function adminUpdateUser(
    userId: number,
    payload: { nickname?: string; role?: Role; password?: string; email?: string }
): Promise<AdminUser> {
    return request(Urls.userDetail(userId), { method: "PATCH", body: payload });
}

/** 一行导入结果明细 */
export interface ImportRowResult {
    line: number;
    username: string;
    ok: boolean;
    message: string;
}

export interface ImportResult {
    created: number;
    total: number;
    results: ImportRowResult[];
}

/** 批量导入名单（CSV 文本，初始密码为账号） */
export function importUsers(content: string): Promise<ImportResult> {
    return request(Urls.usersImport, { method: "POST", body: { content } });
}

/** 审计日志条目 */
export interface AuditEntry {
    id: number;
    username: string;
    action: string;
    detail: string;
    created: string;
}

/** 最近审计日志（管理员） */
export function fetchAuditLogs(): Promise<{ logs: AuditEntry[] }> {
    return request(Urls.audit);
}

/** 题库列表条目（不含题面与用例内容） */
export interface ProblemSummary {
    id: number;
    title: string;
    type: "engineering" | "algorithm";
    language: string;
    difficulty: "easy" | "medium" | "hard";
    image: string;
    sampleCount: number;
    hiddenCount: number;
    updated: string;
}

/** 测试样例（提交格式，也是详情的返回格式） */
export interface SamplePayload {
    name: string;
    input: string;
    expected: string;
    isSample: boolean;
}

/** 题目详情：题面 + 初始代码 + 全部用例（教师 / 管理员可见） */
export interface ProblemDetail extends ProblemSummary {
    description: string;
    starterCode: string;
    createdBy: string;
    samples: (SamplePayload & { id: number })[];
}

export interface ProblemListQuery {
    keyword?: string;
    type?: string;
    language?: string;
}

/** 题库列表（教师 / 管理员） */
export function fetchProblems(query: ProblemListQuery = {}): Promise<{ problems: ProblemSummary[] }> {
    return request(Urls.problems, {
        query: { keyword: query.keyword, type: query.type, language: query.language },
    });
}

/** 题目详情 */
export function fetchProblem(problemId: number): Promise<ProblemDetail> {
    return request(Urls.problemDetail(problemId));
}

/** 创建题目（可携带用例） */
export function createProblem(payload: {
    title: string;
    description: string;
    type: string;
    language: string;
    difficulty: string;
    image: string;
    starterCode: string;
    samples: SamplePayload[];
}): Promise<ProblemDetail> {
    return request(Urls.problems, { method: "POST", body: payload });
}

/** 编辑题目；samples 缺省表示不改用例 */
export function updateProblem(
    problemId: number,
    payload: {
        title?: string;
        description?: string;
        type?: string;
        language?: string;
        difficulty?: string;
        image?: string;
        starterCode?: string;
        samples?: SamplePayload[];
    }
): Promise<ProblemDetail> {
    return request(Urls.problemDetail(problemId), { method: "PATCH", body: payload });
}

/** 删除题目（级联删除用例） */
export function deleteProblem(problemId: number): Promise<{ message: string }> {
    return request(Urls.problemDetail(problemId), { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// 考试管理（教师 / 管理端）
// ---------------------------------------------------------------------------

/** 管理端考试列表条目 */
export interface ExamSummary {
    id: number;
    title: string;
    course: string;
    /** 后端状态：draft / published / archived */
    status: "draft" | "published" | "archived";
    /** 按时间推导的学生侧状态：upcoming / ongoing / finished */
    studentStatus: "upcoming" | "ongoing" | "finished";
    startTime: string | null;
    endTime: string | null;
    durationMinutes: number;
    submitLimit: number;
    aiMode: string;
    problemCount: number;
    candidateCount: number;
    openToAll: boolean;
    submissionCount: number;
    updated: string;
}

/** 组卷条目 */
export interface ExamProblemEntry {
    problemId: number;
    order: number;
    score: number;
    title: string;
    type: string;
    language: string;
    difficulty: string;
    sampleCount: number;
    hiddenCount: number;
}

/** 管理端考试详情 */
export interface ExamDetail extends ExamSummary {
    description: string;
    notice: string;
    createdBy: string;
    problems: ExamProblemEntry[];
    candidates: string[];
}

/** 创建 / 编辑考试的载荷 */
export interface ExamPayload {
    title: string;
    course: string;
    description: string;
    notice: string;
    startTime: string;
    endTime: string;
    durationMinutes: number;
    submitLimit: number;
    aiMode: string;
}

/** 考试列表（教师 / 管理员） */
export function fetchExams(query: { status?: string } = {}): Promise<{ exams: ExamSummary[] }> {
    return request(Urls.exams, { query: { status: query.status } });
}

/** 考试详情（含组卷与名单） */
export function fetchExam(examId: number): Promise<ExamDetail> {
    return request(Urls.examDetail(examId));
}

/** 创建考试（保存为草稿） */
export function createExam(payload: Partial<ExamPayload>): Promise<ExamDetail> {
    return request(Urls.exams, { method: "POST", body: payload });
}

/** 编辑考试（传空串可清除时间） */
export function updateExam(examId: number, payload: Partial<ExamPayload>): Promise<ExamDetail> {
    return request(Urls.examDetail(examId), { method: "PATCH", body: payload });
}

/** 删除考试（仅草稿） */
export function deleteExam(examId: number): Promise<{ message: string }> {
    return request(Urls.examDetail(examId), { method: "DELETE" });
}

/** 组卷：整体替换题目与分值，顺序即题序 */
export function setExamProblems(
    examId: number,
    problems: { problemId: number; score: number }[]
): Promise<ExamDetail> {
    return request(Urls.examProblems(examId), { method: "PUT", body: { problems } });
}

/** 考生名单：传空数组表示全体学生 */
export function setExamCandidates(examId: number, candidates: string[]): Promise<ExamDetail> {
    return request(Urls.examCandidates(examId), { method: "PUT", body: { candidates } });
}

/** 发布 / 撤回 / 归档 */
export function examAction(
    examId: number,
    action: "publish" | "withdraw" | "archive"
): Promise<ExamDetail> {
    return request(Urls.examAction(examId, action), { method: "POST", body: {} });
}

/** 管理端提交记录条目 */
export interface ExamSubmissionEntry {
    id: number;
    examId: number;
    problemId: number;
    problemTitle: string;
    username: string;
    nickname: string;
    language: string;
    status: string;
    created: string;
}

/** 本场考试的提交记录（可按题过滤） */
export function fetchExamSubmissions(
    examId: number,
    problemId?: number
): Promise<{ submissions: ExamSubmissionEntry[]; total: number }> {
    return request(Urls.examSubmissions(examId), {
        query: { problemId: problemId === undefined ? undefined : String(problemId) },
    });
}

// ---------------------------------------------------------------------------
// 考试作答（学生侧）
// ---------------------------------------------------------------------------

/** 学生侧考试列表条目（在管理端字段之上多一个我的提交数） */
export interface MyExamSummary extends ExamSummary {
    mySubmissions: number;
}

/** 学生可见的样例测试 */
export interface StudentSample {
    name: string;
    input: string;
    expected: string;
}

/** 学生视角的题目：题面 + 初始代码 + 样例测试（无隐藏测试） */
export interface StudentProblem {
    problemId: number;
    order: number;
    score: number;
    title: string;
    type: string;
    language: string;
    difficulty: string;
    description: string;
    starterCode: string;
    samples: StudentSample[];
}

/** 学生侧考试详情 */
export interface StudentExamDetail {
    id: number;
    title: string;
    course: string;
    description: string;
    notice: string;
    status: "upcoming" | "ongoing" | "finished";
    startTime: string | null;
    endTime: string | null;
    durationMinutes: number;
    submitLimit: number;
    aiMode: string;
    problems: StudentProblem[];
}

/** 学生侧提交记录（含代码正文） */
export interface MySubmission {
    id: number;
    examId: number;
    problemId: number;
    problemTitle: string;
    language: string;
    status: string;
    created: string;
    code: string;
}

/** 我的考试列表 */
export function fetchMyExams(): Promise<{ exams: MyExamSummary[] }> {
    return request(Urls.myExams);
}

/** 考试详情（题面 + 样例 + 初始代码） */
export function fetchMyExam(examId: number): Promise<StudentExamDetail> {
    return request(Urls.myExamDetail(examId));
}

/** 我在本场考试的提交记录 */
export function fetchMyExamSubmissions(examId: number): Promise<{ submissions: MySubmission[] }> {
    return request(Urls.myExamSubmissions(examId));
}

/** 我对某题的提交历史 */
export function fetchMyProblemSubmissions(
    examId: number,
    problemId: number
): Promise<{ submissions: MySubmission[] }> {
    return request(Urls.mySubmission(examId, problemId));
}

/** 提交代码（当前只收卷存档，判题服务接入后返回判定结果） */
export function submitCode(
    examId: number,
    problemId: number,
    code: string,
    language?: string
): Promise<{ submission: { id: number; problemId: number; status: string; created: string }; used: number; remaining: number }> {
    return request(Urls.mySubmission(examId, problemId), {
        method: "POST",
        body: { code, language },
    });
}

/** 当前令牌 */
export function getToken(): string | null {
    return localStorage.getItem("token");
}

/** 保存令牌 */
export function setToken(token: string) {
    localStorage.setItem("token", token);
}

/** 清除令牌 */
export function removeToken() {
    localStorage.removeItem("token");
}
