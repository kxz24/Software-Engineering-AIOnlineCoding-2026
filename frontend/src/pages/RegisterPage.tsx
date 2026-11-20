import React, { FormEvent, useState } from "react";
import { useDispatch } from "react-redux";
import { useHistory } from "react-router-dom";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";
import { register } from "../api/client";
import { Routes } from "../api/urls";
import { tokenSlice, userSlice } from "../store";
import { Role, roleHome, Roles } from "../roles";

/** 注册开放的角色：管理员账号由后台分配，不开放自助注册 */
const RegisterTabs: Role[] = ["student", "teacher"];

export function RegisterPage() {
    const dispatch = useDispatch();
    const history = useHistory();

    const [role, setRole] = useState<Role>("student");
    const [username, setUsername] = useState("");
    const [nickname, setNickname] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        if (submitting) {
            return;
        }
        const name = username.trim();
        const display = nickname.trim();
        if (!name || !display || !password || !confirm) {
            setError("请填写全部字段。");
            return;
        }
        if (name.length < 3 || name.length > 32) {
            setError("学号 / 工号需为 3-32 个字符。");
            return;
        }
        if (password.length < 6) {
            setError("密码至少 6 位。");
            return;
        }
        if (password !== confirm) {
            setError("两次输入的密码不一致。");
            return;
        }
        setSubmitting(true);
        setError(null);

        // 与登录一致：后端没起来时 fetch 直接抛异常，统一转成界面提示
        const result = await register(name, password, display, role).catch(() => null);
        setSubmitting(false);

        if (result === null) {
            setError("无法连接后端服务，请确认已启动后端（默认 127.0.0.1:8000）。");
            return;
        }

        if (!result.success) {
            setError(result.message);
            return;
        }

        // 注册即登录，直接进入对应角色的工作台
        dispatch(tokenSlice.actions.setToken(result.jwt));
        dispatch(userSlice.actions.updateUserStatus({
            id: result.userId,
            username: result.username,
            nickname: result.nickname,
            role: result.role,
            created: "",
        }));

        history.push(roleHome(result.role));
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
                    <div className="login-title">注册</div>
                    <div className="login-sub">创建课程账号，注册成功后直接进入平台</div>

                    <div className="role-tabs">
                        {RegisterTabs.map(tab => (
                            <span key={tab}
                                  className={"role-tab" + (role === tab ? " active" : "")}
                                  onClick={() => setRole(tab)}>
                                {Roles[tab].label}
                            </span>
                        ))}
                    </div>

                    <div className="field">
                        <div className="label">{role === "teacher" ? "工号" : "学号"}</div>
                        <input className="input"
                               value={username}
                               autoComplete="username"
                               placeholder={role === "teacher" ? "如 T2026001" : "如 2023012345"}
                               onChange={e => setUsername(e.target.value)}/>
                    </div>
                    <div className="field">
                        <div className="label">姓名</div>
                        <input className="input"
                               value={nickname}
                               placeholder={role === "teacher" ? "如 刘老师" : "如 李同学"}
                               onChange={e => setNickname(e.target.value)}/>
                    </div>
                    <div className="field">
                        <div className="label">密码</div>
                        <input className="input"
                               type="password"
                               value={password}
                               autoComplete="new-password"
                               placeholder="至少 6 位"
                               onChange={e => setPassword(e.target.value)}/>
                    </div>
                    <div className="field">
                        <div className="label">确认密码</div>
                        <input className="input"
                               type="password"
                               value={confirm}
                               autoComplete="new-password"
                               placeholder="再次输入密码"
                               onChange={e => setConfirm(e.target.value)}/>
                    </div>

                    {error && (
                        <div className="login-error fade-in">
                            <Icon name="alert-triangle" size={12}/>{error}
                        </div>
                    )}

                    <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
                        {submitting ? "注册中…" : "创建账号并进入"}
                    </button>

                    <div className="login-note">
                        已有账号？<span className="link" onClick={() => history.push(Routes.login)}>返回登录</span>
                    </div>
                    <div className="login-foot">注册即表示同意《考试诚信与数据使用说明》</div>
                </form>
            </div>

            <div className="login-bottom">清华大学软件学院 · 软件工程课程项目 · 原型 V0.1</div>
        </div>
    );
}
