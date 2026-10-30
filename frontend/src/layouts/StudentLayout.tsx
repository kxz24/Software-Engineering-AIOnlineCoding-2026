import React from "react";
import { useSelector } from "react-redux";
import { NavLink, useHistory } from "react-router-dom";
import { Store } from "../store";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";
import { Routes } from "../api/urls";
import { roleLabel } from "../roles";
import { logout, removeToken } from "../api/client";

/** 学生端的三个一级入口，对应原型的顶部导航 */
export type StudentNav = "exams" | "reports" | "precheck";

interface Props {
    active: StudentNav;
    children: React.ReactNode;
}

/**
 * 学生端外壳：顶部导航（我的考试 / 成绩报告 / 考试须知）+ 1180px 内容区。
 * 对应原型 02、03、05、06 页的 student-page 结构。
 */
export function StudentLayout({ active, children }: Props) {
    const user = useSelector((s: Store) => s.user);
    const history = useHistory();

    const navItems: { key: StudentNav; label: string; to: string }[] = [
        { key: "exams", label: "我的考试", to: Routes.examList },
        { key: "reports", label: "成绩报告", to: Routes.examReport("exam-mid-2026") },
        { key: "precheck", label: "考试须知", to: Routes.examPrecheck("exam-mid-2026") },
    ];

    /** 退出登录：后端无状态，清掉本地令牌即可；后端未启动时也要能退出 */
    const handleLogout = async () => {
        try {
            await logout();
        } catch (e) {
            removeToken();
        }
        history.push(Routes.login);
        window.location.reload();
    };

    return (
        <div className="student-page">
            <header className="student-nav">
                <div className="student-nav-left">
                    <Brand/>
                    <nav className="nav-links">
                        {navItems.map(item => (
                            <NavLink key={item.key}
                                     to={item.to}
                                     className={"nav-link" + (active === item.key ? " active" : "")}>
                                {item.label}
                            </NavLink>
                        ))}
                    </nav>
                </div>
                <div className="student-nav-right">
                    <span className="icon-btn plain" title="搜索">
                        <Icon name="search" size={16}/>
                    </span>
                    <span className="icon-btn plain" title="通知">
                        <Icon name="bell" size={16}/>
                    </span>
                    <div className="user-inline">
                        <div className="avatar sm">{(user?.nickname || "考").slice(0, 1)}</div>
                        <div>
                            <div className="user-name">{user?.nickname || "未登录"}</div>
                            <div className="user-role">
                                {user ? `${roleLabel(user.role)} · ${user.username}` : "未登录"}
                            </div>
                        </div>
                        <span className="icon-btn plain ml-auto" title="退出登录" onClick={handleLogout}>
                            <Icon name="log-out" size={15}/>
                        </span>
                    </div>
                </div>
            </header>
            <div className="student-content">{children}</div>
        </div>
    );
}
