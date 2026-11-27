import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { StudentLayout } from "../layouts/StudentLayout";
import { TeacherLayout } from "../layouts/TeacherLayout";
import { Icon } from "../components/Icon";
import { toast } from "../components/Toast";
import { Store, userSlice } from "../store";
import { roleLabel } from "../roles";
import { formatDateTime } from "../api/format";
import {
    ApiError,
    changePassword,
    fetchProfile,
    ProfileInfo,
    updateProfile,
} from "../api/client";

const StatLabels: Record<string, string> = {
    examSubmissions: "考试提交",
    practiceSubmissions: "练习提交",
    aiSessions: "AI 会话",
    createdExams: "创建考试",
    publishedExams: "已发布考试",
    createdProblems: "创建题目",
    users: "平台账号",
    auditLogs: "审计日志",
};

const ActionLabels: Record<string, string> = {
    login: "登录",
    register: "注册",
    "account.update_self": "修改个人资料",
    "account.password": "修改密码",
    "submission.create": "提交考试代码",
    "practice.submit": "提交练习代码",
    "problem.create": "创建题目",
    "problem.update": "编辑题目",
};

const inputStyle: React.CSSProperties = {
    height: 34,
    fontSize: 11.5,
};

/**
 * 个人中心（学生 / 教师 / 管理员均可访问）：
 * 查看账号状态与使用概况、修改姓名 / 邮箱、修改密码、查看本人操作记录。
 */
export function AccountPage() {
    const user = useSelector((s: Store) => s.user);
    const dispatch = useDispatch();

    const [profile, setProfile] = useState<ProfileInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [nickname, setNickname] = useState("");
    const [email, setEmail] = useState("");
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const [oldPassword, setOldPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [passwordBusy, setPasswordBusy] = useState(false);
    const [passwordError, setPasswordError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchProfile()
            .then(result => {
                setProfile(result);
                setNickname(result.nickname);
                setEmail(result.email || "");
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, []);

    const handleSaveProfile = () => {
        if (saving) {
            return;
        }
        if (!nickname.trim()) {
            setFormError("姓名不能为空");
            return;
        }
        setSaving(true);
        setFormError(null);
        updateProfile({ nickname: nickname.trim(), email: email.trim() })
            .then(result => {
                setProfile(result);
                setNickname(result.nickname);
                setEmail(result.email || "");
                if (user) {
                    dispatch(userSlice.actions.updateUserStatus({
                        ...user,
                        nickname: result.nickname,
                    }));
                }
                toast("个人资料已保存", "success");
            })
            .catch((e: ApiError) => setFormError(e.message))
            .finally(() => setSaving(false));
    };

    const handleChangePassword = () => {
        if (passwordBusy) {
            return;
        }
        if (!oldPassword || !newPassword) {
            setPasswordError("原密码和新密码均不能为空");
            return;
        }
        if (newPassword.length < 6 || newPassword.length > 64) {
            setPasswordError("新密码长度需在 6-64 个字符之间");
            return;
        }
        if (newPassword !== confirmPassword) {
            setPasswordError("两次输入的新密码不一致");
            return;
        }
        setPasswordBusy(true);
        setPasswordError(null);
        changePassword(oldPassword, newPassword)
            .then(() => {
                setOldPassword("");
                setNewPassword("");
                setConfirmPassword("");
                toast("密码已修改，请牢记新密码", "success");
                load();
            })
            .catch((e: ApiError) => setPasswordError(e.message))
            .finally(() => setPasswordBusy(false));
    };

    const content = (
        <>
            <div className="page-head">
                <div>
                    <div className="page-title">个人中心</div>
                    <div className="page-sub">
                        {profile
                            ? `${profile.nickname}（${profile.username}） · ${roleLabel(profile.role)}`
                            : "查看账号状态、修改资料与密码"}
                    </div>
                </div>
                <div className="page-actions">
                    <span className="badge green">账号正常</span>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                    </div>
                </div>
            )}

            {loading && !profile && (
                <div className="card"><div className="card-body muted">加载中…</div></div>
            )}

            {profile && (
                <>
                    <div className="card" style={{ marginBottom: 14 }}>
                        <div className="card-body" style={{ display: "flex", alignItems: "center", gap: 16 }}>
                            <div className="avatar" style={{ width: 56, height: 56, fontSize: 20 }}>
                                {profile.nickname.slice(0, 1)}
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: 18, fontWeight: 700 }}>{profile.nickname}</div>
                                <div className="muted" style={{ fontSize: 11.5, marginTop: 3 }}>
                                    {profile.username} · {roleLabel(profile.role)} · 注册于 {formatDateTime(profile.created)}
                                </div>
                                <div className="muted" style={{ fontSize: 10.5, marginTop: 2 }}>
                                    {profile.email || "未填写邮箱"}
                                </div>
                            </div>
                            <span className="badge green">正常</span>
                        </div>
                    </div>

                    {Object.keys(profile.stats).length > 0 && (
                        <div className="stats-grid">
                            {Object.keys(profile.stats).map(key => (
                                <div className="stat-card" key={key}>
                                    <div className="stat-icon"><Icon name="bar-chart" size={17}/></div>
                                    <div>
                                        <div className="stat-value">{profile.stats[key]}</div>
                                        <div className="stat-label">{StatLabels[key] || key}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="form-grid two">
                        <div className="card">
                            <div className="card-head">
                                <div>
                                    <div className="card-title">基本资料</div>
                                    <div className="card-sub">姓名会显示在考试、监考与讨论区</div>
                                </div>
                            </div>
                            <div className="card-body">
                                <div className="field">
                                    <div className="label">姓名 / 昵称</div>
                                    <input className="input" style={inputStyle}
                                           value={nickname}
                                           onChange={event => setNickname(event.target.value)}/>
                                </div>
                                <div className="field" style={{ marginTop: 10 }}>
                                    <div className="label">邮箱</div>
                                    <input className="input" style={inputStyle}
                                           placeholder="用于接收通知（可选）"
                                           value={email}
                                           onChange={event => setEmail(event.target.value)}/>
                                </div>
                                <div className="field" style={{ marginTop: 10 }}>
                                    <div className="label">登录账号</div>
                                    <input className="input" style={{ ...inputStyle, background: "#f8fafc" }}
                                           value={profile.username} disabled/>
                                </div>
                                {formError && (
                                    <div className="login-error" style={{ marginTop: 8 }}>
                                        <Icon name="alert-triangle" size={12}/>{formError}
                                    </div>
                                )}
                                <button type="button" className="btn btn-primary"
                                        style={{ marginTop: 12 }}
                                        disabled={saving}
                                        onClick={handleSaveProfile}>
                                    <Icon name="check" size={13}/>{saving ? "保存中…" : "保存资料"}
                                </button>
                            </div>
                        </div>

                        <div className="card">
                            <div className="card-head">
                                <div>
                                    <div className="card-title">修改密码</div>
                                    <div className="card-sub">修改后其他已登录页面不会自动退出</div>
                                </div>
                            </div>
                            <div className="card-body">
                                <div className="field">
                                    <div className="label">原密码</div>
                                    <input className="input" style={inputStyle} type="password"
                                           value={oldPassword}
                                           onChange={event => setOldPassword(event.target.value)}/>
                                </div>
                                <div className="field" style={{ marginTop: 10 }}>
                                    <div className="label">新密码（6-64 位）</div>
                                    <input className="input" style={inputStyle} type="password"
                                           value={newPassword}
                                           onChange={event => setNewPassword(event.target.value)}/>
                                </div>
                                <div className="field" style={{ marginTop: 10 }}>
                                    <div className="label">确认新密码</div>
                                    <input className="input" style={inputStyle} type="password"
                                           value={confirmPassword}
                                           onChange={event => setConfirmPassword(event.target.value)}/>
                                </div>
                                {passwordError && (
                                    <div className="login-error" style={{ marginTop: 8 }}>
                                        <Icon name="alert-triangle" size={12}/>{passwordError}
                                    </div>
                                )}
                                <button type="button" className="btn btn-primary"
                                        style={{ marginTop: 12 }}
                                        disabled={passwordBusy}
                                        onClick={handleChangePassword}>
                                    <Icon name="lock" size={13}/>{passwordBusy ? "修改中…" : "修改密码"}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="card" style={{ marginTop: 14 }}>
                        <div className="card-head">
                            <div>
                                <div className="card-title">我的操作记录</div>
                                <div className="card-sub">最近 20 条账号相关操作</div>
                            </div>
                            <span className="badge blue">{profile.audits.length} 条</span>
                        </div>
                        <div className="card-body" style={{ maxHeight: 300, overflowY: "auto" }}>
                            {profile.audits.length === 0 && (
                                <div className="muted" style={{ fontSize: 11.5 }}>暂无操作记录</div>
                            )}
                            {profile.audits.map((audit, index) => (
                                <div className="log-item" key={index}>
                                    <span className="log-dot green"/>
                                    <div>
                                        <div className="log-text">
                                            {ActionLabels[audit.action] || audit.action}
                                        </div>
                                        <div className="log-sub">
                                            {formatDateTime(audit.created)} · {audit.detail || "—"}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </>
    );

    if (user && user.role !== "student") {
        return <TeacherLayout breadcrumb={["工作台", "个人中心"]}>{content}</TeacherLayout>;
    }
    return <StudentLayout active="account">{content}</StudentLayout>;
}
