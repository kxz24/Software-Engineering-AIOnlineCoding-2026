/**
 * 后端接口地址。
 * 开发时由 package.json 的 proxy 转发到 127.0.0.1:8000，
 * 部署后由 Nginx 把 /api/v1 转发到后端容器。
 */
export const Urls = {
    login: "/api/v1/login", // PATCH
    logout: "/api/v1/logout", // PATCH
    user: "/api/v1/user", // GET
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

    examList: "/exams",
    examPrecheck: (examId: string | number) => `/exams/${examId}/precheck`,
    examWorkbench: (examId: string | number) => `/exams/${examId}/workbench`,
    examResult: (examId: string | number) => `/exams/${examId}/result`,
    examReport: (examId: string | number) => `/exams/${examId}/report`,

    examManage: "/manage",
    examCreate: "/manage/new",
    problemConfig: (examId: string | number) => `/manage/${examId}/problems`,
    proctor: (examId: string | number) => `/manage/${examId}/proctor`,
};
