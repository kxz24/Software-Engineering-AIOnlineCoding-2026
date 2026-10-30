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

/** 当前令牌 */
export function getToken(): string | null {
    return localStorage.getItem("token");
}

/** 保存令牌 */
export function setToken(token: string) {
    localStorage.setItem("token", token);
}

/** 清除令牌（同时清掉演示模式写入的本地用户） */
export function removeToken() {
    localStorage.removeItem("token");
    localStorage.removeItem("demoUser");
}
