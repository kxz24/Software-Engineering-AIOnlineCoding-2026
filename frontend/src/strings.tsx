/**
 * 界面文案集中管理，避免中文散落在组件里。
 * 参数占位统一用 {name} 形式，由 format 替换。
 */
export const Strings = {
    "api/illegal_json": "服务器返回了一个非法的 JSON",
    "api/unknown_error": "未知的错误",

    "main/title": "AICoding 考试平台",
    "main/not_logged_in": "未登录",
    "main/go_homepage": "返回主页",
    "main/go_back": "返回上一页",

    "home/welcome": "欢迎，{nickname}",
    "home/role": "当前身份：{role}",
    "home/not_logged_in_title": "你还没有登录",
    "home/not_logged_in_content": "登录后即可进入对应身份的工作台。",
    "home/go_login": "去登录",
    "home/logout": "退出登录",

    "drawer/login": "登录",
    "drawer/home": "首页",
    "drawer/logout": "退出登录",

    "login/title": "AICoding 考试平台",
    "login/subtitle": "请使用平台账号登录",
    "login/login": "登录",
    "login/username": "用户名",
    "login/password": "密码",
    "login/failed": "登录失败: {message}",

    "error/page_not_found": "页面不存在",
};

/** 后端错误码到中文的映射，未命中则原样显示 */
const translations: { [message: string]: string } = {
    "User must be authorized.": "请先登录",
    "Invalid credentials": "用户名或密码错误",
    "Permission denied.": "没有访问权限",
};

export function translate(message: string): string {
    return translations[message] || message;
}

/**
 * 把 {key} 占位替换为实际值。
 * 例如 format("login/failed", {"message": "x"}) -> "登录失败: x"
 */
export function format(key: keyof typeof Strings, params?: { [k: string]: string }): string {
    let result: string = Strings[key];
    if (params) {
        for (const [k, v] of Object.entries(params)) {
            result = result.replace(`{${k}}`, v);
        }
    }
    return result;
}
