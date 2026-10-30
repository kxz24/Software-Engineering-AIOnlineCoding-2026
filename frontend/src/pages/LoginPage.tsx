import React, { FormEvent, useState } from "react";
import { useDispatch } from "react-redux";
import { useHistory, useLocation } from "react-router-dom";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";
import { login } from "../api/client";
import { tokenSlice, userSlice } from "../store";
import { Role, roleHome, Roles } from "../roles";
import { demoHome, DemoEnabled, enterDemo } from "../demo";

/** 原型里的三个身份标签；真实角色仍以账号在后端记录的角色为准 */
const IdentityTabs: Role[] = ["student", "teacher", "admin"];

const IdentityHints: Record<Role, string> = {
    student: "登录后进入我的考试",
    teacher: "登录后进入考试管理工作台",
    admin: "登录后进入考试管理工作台",
};

interface LocationState {
    from?: string;
}

export function LoginPage() {
    const dispatch = useDispatch();
    const history = useHistory();
    const location = useLocation<LocationState>();

    const [identity, setIdentity] = useState<Role>("student");
    const [username, setUsername] = useState(localStorage.getItem("rememberedUsername") || "");
    const [password, setPassword] = useState("");
    const [remember, setRemember] = useState(!!localStorage.getItem("rememberedUsername"));
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        if (submitting) {
            return;
        }
        if (!username.trim() || !password) {
            setError("请输入学号 / 工号与密码。");
            return;
        }
        setSubmitting(true);
        setError(null);

        // 后端没起来时 fetch 会直接抛异常，这里统一转成界面上的错误提示
        const result = await login(username.trim(), password).catch(() => null);
        setSubmitting(false);

        if (result === null) {
            setError("无法连接后端服务，请确认已启动后端（默认 127.0.0.1:8000）。");
            return;
        }

        if (!result.success) {
            setError(result.message);
            return;
        }

        if (remember) {
            localStorage.setItem("rememberedUsername", username.trim());
        } else {
            localStorage.removeItem("rememberedUsername");
        }

        dispatch(tokenSlice.actions.setToken(result.jwt));
        dispatch(userSlice.actions.updateUserStatus({
            id: result.userId,
            username: result.username,
            nickname: result.nickname,
            role: result.role,
            created: "",
        }));

        history.push(location.state?.from || roleHome(result.role));
    };

    /** 演示模式：不经过后端，直接用内置账号进入对应工作台 */
    const enterAs = (identity: "student" | "teacher") => {
        const demoUser = enterDemo(identity);
        dispatch(tokenSlice.actions.setToken("demo-token"));
        dispatch(userSlice.actions.updateUserStatus(demoUser));
        history.push(demoHome(demoUser.role));
    };

    return (
        <div className="login-page">
            <div className="login-top">
                <Brand/>
                <div className="login-top-right">
                    <span>帮助中心</span><span>·</span><span>隐私说明</span>
                </div>
            </div>

            <div className="login-wrap">
                <form className="login-card" onSubmit={handleSubmit}>
                    <div className="login-title">登录</div>
                    <div className="login-sub">使用课程账号进入考试或工作台</div>

                    <div className="role-tabs">
                        {IdentityTabs.map(tab => (
                            <span key={tab}
                                  className={"role-tab" + (identity === tab ? " active" : "")}
                                  onClick={() => setIdentity(tab)}>
                                {Roles[tab].label}
                            </span>
                        ))}
                    </div>

                    <div className="field">
                        <div className="label">学号 / 工号</div>
                        <input className="input"
                               value={username}
                               autoComplete="username"
                               placeholder="2023012345"
                               onChange={e => setUsername(e.target.value)}/>
                    </div>
                    <div className="field">
                        <div className="label">密码</div>
                        <input className="input"
                               type="password"
                               value={password}
                               autoComplete="current-password"
                               placeholder="请输入密码"
                               onChange={e => setPassword(e.target.value)}/>
                    </div>

                    <div className="login-row">
                        <span className="check-row" onClick={() => setRemember(!remember)}>
                            <span className={"check-box" + (remember ? " checked" : "")}>
                                {remember &&
                                <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#ffffff"
                                     strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M20 6L9 17l-5-5"/>
                                </svg>}
                            </span>记住我
                        </span>
                        <span className="link">忘记密码？</span>
                    </div>

                    {error && (
                        <div className="login-error fade-in">
                            <Icon name="alert-triangle" size={12}/>{error}
                        </div>
                    )}

                    <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
                        {submitting ? "登录中…" : "登录"}
                    </button>

                    <div className="login-note">
                        当前身份：{Roles[identity].label} · {IdentityHints[identity]}
                    </div>
                    <div className="login-foot">登录即表示同意《考试诚信与数据使用说明》</div>

                    {DemoEnabled && (
                        <div className="demo-entry">
                            后端未就绪？
                            <span className="link" onClick={() => enterAs("student")}>以学生身份预览</span>
                            <span className="muted">·</span>
                            <span className="link" onClick={() => enterAs("teacher")}>以教师身份预览</span>
                        </div>
                    )}
                </form>
            </div>

            <div className="login-bottom">清华大学软件学院 · 软件工程课程项目 · 原型 V0.1</div>
        </div>
    );
}
