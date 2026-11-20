import { Routes } from "./api/urls";

/**
 * 平台角色定义。
 *
 * 与后端 user.models.User.ROLE_CHOICES 保持一致，
 * 新增角色时两边要同时修改。
 */
export type Role = "admin" | "teacher" | "student";

export interface RoleMeta {
    /** 中文名称 */
    label: string;
    /** 该角色在本平台中的职责说明 */
    description: string;
    /** 登录后进入的首页 */
    home: string;
}

export const Roles: Record<Role, RoleMeta> = {
    admin: {
        label: "管理员",
        description: "负责账号与权限、镜像与资源、审计与数据导出。",
        home: "/manage",
    },
    teacher: {
        label: "教师",
        description: "负责命题配置、考试发布、过程监控与成绩复核。",
        home: "/manage",
    },
    student: {
        label: "学生",
        description: "参加在线编程考试，查看答题记录与过程报告。",
        home: "/exams",
    },
};

/**
 * 取角色中文名。未知角色原样返回，避免界面显示空白。
 */
export function roleLabel(role: string | null | undefined): string {
    if (!role) {
        return "";
    }
    return Roles[role as Role]?.label ?? role;
}

/** 某个角色的首页路由，未登录时回登录页 */
export function roleHome(role: string | null | undefined): string {
    if (!role) {
        return Routes.login;
    }
    return Roles[role as Role]?.home ?? Routes.examList;
}
