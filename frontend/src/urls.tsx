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
 */
export const LocalUrls = {
    home: function () {
        return "/";
    },
    login: function () {
        return "/login";
    },
};
