/**
 * 演示模式。
 *
 * 后端目前只有登录接口，且本地库还需要先建表建号，前端评审时往往起不来。
 * 演示模式在**开发环境**下提供一个不经过后端、直接进入学生端 / 教师端的入口，
 * 便于按原型逐个页面对照界面。
 *
 * 正式联调或上线前删除：删掉本文件、LoginPage 中的入口、App 中的分支即可。
 */
import { UserSelf } from "./api/client";
import { Role } from "./roles";

export const DemoToken = "demo-token";
export const DemoUserKey = "demoUser";

/** 开发环境才显示演示入口 */
export const DemoEnabled = process.env.NODE_ENV === "development";

export const DemoUsers: Record<"student" | "teacher", UserSelf> = {
    student: {
        id: 1,
        username: "2023012345",
        nickname: "李同学",
        role: "student",
        created: "",
    },
    teacher: {
        id: 2,
        username: "liu",
        nickname: "刘老师",
        role: "teacher",
        created: "",
    },
};

/** 是否处于演示模式 */
export function isDemo(): boolean {
    return localStorage.getItem("token") === DemoToken;
}

/** 进入演示模式：写入假令牌与演示用户 */
export function enterDemo(identity: "student" | "teacher"): UserSelf {
    localStorage.setItem("token", DemoToken);
    localStorage.setItem(DemoUserKey, JSON.stringify(DemoUsers[identity]));
    return DemoUsers[identity];
}

/** 读取演示用户 */
export function loadDemoUser(): UserSelf | null {
    const raw = localStorage.getItem(DemoUserKey);
    if (!raw) {
        return null;
    }
    try {
        return JSON.parse(raw) as UserSelf;
    } catch (e) {
        return null;
    }
}

/** 退出演示模式 */
export function clearDemo() {
    localStorage.removeItem(DemoUserKey);
}

/** 演示用户的角色首页 */
export function demoHome(role: Role): string {
    return role === "student" ? "/exams" : "/manage";
}
