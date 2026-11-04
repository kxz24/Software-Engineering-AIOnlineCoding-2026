import React from "react";
import { useSelector } from "react-redux";
import { NavLink, useHistory } from "react-router-dom";
import { Store } from "../store";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";
import { Routes } from "../api/urls";
import { roleLabel } from "../roles";
import { logout, removeToken } from "../api/client";

interface Props {
    /** 面包屑，最后一项为当前页 */
    breadcrumb: string[];
    children: React.ReactNode;
}

/**
 * 教师端外壳：220px 侧边栏 + 60px 顶栏（面包屑 / 用户）。
 * 对应原型 07、08、09、10 页的 teacher-shell 结构。
 */
export function TeacherLayout({ breadcrumb, children }: Props) {
    const user = useSelector((s: Store) => s.user);
    const history = useHistory();

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
        <div className="teacher-shell">
            <aside className="teacher-sidebar">
                <div className="teacher-brand">
                    <Brand small subtitle="考试平台 · 教师端"/>
                </div>
                <div className="side-nav">
                    <div className="side-label">工作台</div>
                    <NavLink to={Routes.examManage} className="side-link" activeClassName="active">
                        <Icon name="file-text" size={16}/>考试管理
                    </NavLink>
                    <NavLink to={Routes.problemBank} className="side-link" activeClassName="active">
                        <Icon name="book-open" size={16}/>题库管理
                    </NavLink>
                    <NavLink to={Routes.proctorHome} className="side-link" activeClassName="active">
                        <Icon name="monitor" size={16}/>监考中心
                    </NavLink>
                    {user?.role === "admin" && (
                        <>
                            <div className="side-label">配置</div>
                            <NavLink to={Routes.accounts} className="side-link" activeClassName="active">
                                <Icon name="shield" size={16}/>账号管理
                            </NavLink>
                        </>
                    )}
                </div>
                <div className="side-bottom">
                    <div className="user-inline">
                        <div className="avatar sm">{(user?.nickname || "师").slice(0, 1)}</div>
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
            </aside>
            <div className="teacher-main">
                <header className="teacher-topbar">
                    <div className="breadcrumb">
                        {breadcrumb.map((crumb, index) => {
                            const last = index === breadcrumb.length - 1;
                            return (
                                <React.Fragment key={crumb + index}>
                                    <span className={last ? "current" : undefined}>{crumb}</span>
                                    {!last && <Icon name="chevron-right" size={12} stroke="#cbd5e1"/>}
                                </React.Fragment>
                            );
                        })}
                    </div>
                    <div className="topbar-actions">
                        <div className="avatar sm">{(user?.nickname || "师").slice(0, 1)}</div>
                    </div>
                </header>
                <div className="teacher-content">{children}</div>
            </div>
        </div>
    );
}
