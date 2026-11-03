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

    examManage: "/manage",
    examCreate: "/manage/new",
    problemConfig: (examId: string | number) => `/manage/${examId}/problems`,
    proctor: (examId: string | number) => `/manage/${examId}/proctor`,

    /** 题库管理（教师 / 管理员） */
    problemBank: "/manage/problems",
    /** 账号管理（管理员） */
    accounts: "/manage/accounts",
};
