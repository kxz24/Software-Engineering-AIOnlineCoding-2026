/**
 * 后端接口地址。
 * 开发时由 package.json 的 proxy 转发到 127.0.0.1:8000，
 * 部署后由 Nginx 把 /api/v1 转发到后端容器。
 */
export const Urls = {
    register: "/api/v1/register", // POST
    login: "/api/v1/login", // PATCH
    logout: "/api/v1/logout", // PATCH
    user: "/api/v1/user", // GET

    users: "/api/v1/users", // GET 管理员列表 / POST 创建
    usersImport: "/api/v1/users/import", // POST 批量导入
    userDetail: (userId: number) => `/api/v1/users/${userId}`, // GET / PATCH
    audit: "/api/v1/audit", // GET 管理员

    problems: "/api/v1/problems", // GET 教师列表 / POST 创建
    problemDetail: (problemId: number) => `/api/v1/problems/${problemId}`, // GET / PATCH / DELETE

    exams: "/api/v1/exams", // GET 教师 / POST 创建
    examDetail: (examId: number) => `/api/v1/exams/${examId}`, // GET / PATCH / DELETE
    examProblems: (examId: number) => `/api/v1/exams/${examId}/problems`, // PUT 组卷
    examCandidates: (examId: number) => `/api/v1/exams/${examId}/candidates`, // PUT 名单
    examAction: (examId: number, action: "publish" | "withdraw" | "archive") =>
        `/api/v1/exams/${examId}/${action}`, // POST 状态流转
    examSubmissions: (examId: number) => `/api/v1/exams/${examId}/submissions`, // GET 提交记录

    myExams: "/api/v1/my/exams", // GET 学生
    myExamDetail: (examId: number) => `/api/v1/my/exams/${examId}`, // GET
    myExamSubmissions: (examId: number) => `/api/v1/my/exams/${examId}/submissions`, // GET
    mySubmission: (examId: number, problemId: number) =>
        `/api/v1/my/exams/${examId}/problems/${problemId}/submissions`, // GET / POST
};

/**
 * 前端页面路由。
 *
 * 与 docs/prototype/页面跳转对照表.md 的页面编号一一对应：
 *   02 我的考试 / 03 考试须知 / 04 做题工作台 / 05 提交结果 / 06 成绩报告
 *   07 考试管理 / 08 创建考试 / 09 题目配置 / 10 监考中心
 */
export const Routes = {
    login: "/login",
    register: "/register",

    examList: "/exams",
    examPrecheck: (examId: string | number) => `/exams/${examId}/precheck`,
    examWorkbench: (examId: string | number) => `/exams/${examId}/workbench`,
    examResult: (examId: string | number) => `/exams/${examId}/result`,
    examReport: (examId: string | number) => `/exams/${examId}/report`,
    /** 成绩报告首页：列出可查看报告的考试 */
    reports: "/reports",

    examManage: "/manage",
    examCreate: "/manage/new",
    examEdit: (examId: string | number) => `/manage/${examId}/edit`,
    problemConfig: (examId: string | number) => `/manage/${examId}/problems`,
    /** 监考中心首页：选择要监考的考试 */
    proctorHome: "/manage/proctor",
    proctor: (examId: string | number) => `/manage/${examId}/proctor`,

    /** 题库管理（教师 / 管理员） */
    problemBank: "/manage/problems",
    /** 账号管理（管理员） */
    accounts: "/manage/accounts",
};
