import React, { useEffect, useRef, useState } from "react";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Role, roleLabel } from "../../roles";
import {
    AdminUser,
    adminCreateUser,
    adminUpdateUser,
    ApiError,
    AuditEntry,
    fetchAuditLogs,
    fetchUsers,
    ImportResult,
    importUsers,
} from "../../api/client";

/** 角色徽章配色：管理员红 / 教师绿 / 学生蓝 */
const RoleBadge: Record<Role, string> = {
    admin: "badge red",
    teacher: "badge green",
    student: "badge blue",
};

const RoleOptions: Role[] = ["student", "teacher", "admin"];

/** 后端返回的 ISO 时间 → 本地「YYYY-MM-DD HH:mm」 */
function formatTime(iso: string): string {
    const date = new Date(iso);
    if (isNaN(date.getTime())) {
        return iso;
    }
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
        `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const SmallInputStyle: React.CSSProperties = {
    height: 30,
    padding: "0 8px",
    fontSize: 11.5,
};

/** 新建账号表单 */
interface CreateForm {
    username: string;
    nickname: string;
    password: string;
    role: Role;
    email: string;
}

const EmptyCreateForm: CreateForm = {
    username: "",
    nickname: "",
    password: "",
    role: "student",
    email: "",
};

/** 编辑账号表单（密码留空表示不重置） */
interface EditForm {
    user: AdminUser;
    nickname: string;
    role: Role;
    email: string;
    password: string;
}

/**
 * 账号管理（管理员）：账号列表 / 新建 / 编辑、CSV 批量导入与审计日志。
 *
 * 对应迭代计划第一轮「账号管理与权限分级」，接口见 /api/v1/users*。
 */
export function AccountsPage() {
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [keyword, setKeyword] = useState("");
    const [roleFilter, setRoleFilter] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [createForm, setCreateForm] = useState<CreateForm | null>(null);
    const [editForm, setEditForm] = useState<EditForm | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    const [importText, setImportText] = useState("");
    const [importResult, setImportResult] = useState<ImportResult | null>(null);
    const [importing, setImporting] = useState(false);
    const fileRef = useRef<HTMLInputElement | null>(null);

    const [logs, setLogs] = useState<AuditEntry[]>([]);

    const loadUsers = (search: string, role: string) => {
        setLoading(true);
        setError(null);
        fetchUsers({ role: role || undefined, keyword: search || undefined })
            .then(result => {
                setUsers(result.users);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    const loadLogs = () => {
        fetchAuditLogs()
            .then(result => setLogs(result.logs))
            .catch(() => setLogs([]));
    };

    useEffect(() => {
        loadUsers("", "");
        loadLogs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleCreate = async () => {
        if (!createForm || saving) {
            return;
        }
        if (createForm.username.trim().length < 3) {
            setFormError("账号至少 3 个字符。");
            return;
        }
        if (createForm.password.length < 6) {
            setFormError("密码至少 6 位。");
            return;
        }
        if (!createForm.nickname.trim()) {
            setFormError("请填写姓名。");
            return;
        }
        setSaving(true);
        setFormError(null);
        try {
            await adminCreateUser({
                username: createForm.username.trim(),
                nickname: createForm.nickname.trim(),
                password: createForm.password,
                role: createForm.role,
                email: createForm.email.trim(),
            });
            toast("账号已创建", "success");
            setCreateForm(null);
            loadUsers(keyword.trim(), roleFilter);
            loadLogs();
        } catch (e) {
            setFormError((e as ApiError).message);
        } finally {
            setSaving(false);
        }
    };

    const handleUpdate = async () => {
        if (!editForm || saving) {
            return;
        }
        if (editForm.password && editForm.password.length < 6) {
            setFormError("重置密码至少 6 位。");
            return;
        }
        setSaving(true);
        setFormError(null);
        const payload: { nickname: string; role: Role; email: string; password?: string } = {
            nickname: editForm.nickname.trim(),
            role: editForm.role,
            email: editForm.email.trim(),
        };
        if (editForm.password) {
            payload.password = editForm.password;
        }
        try {
            await adminUpdateUser(editForm.user.id, payload);
            toast("账号已保存", "success");
            setEditForm(null);
            loadUsers(keyword.trim(), roleFilter);
            loadLogs();
        } catch (e) {
            setFormError((e as ApiError).message);
        } finally {
            setSaving(false);
        }
    };

    const handleImport = async () => {
        if (!importText.trim() || importing) {
            return;
        }
        setImporting(true);
        try {
            const result = await importUsers(importText);
            setImportResult(result);
            toast(`导入完成：成功 ${result.created} / 共 ${result.total} 行`, "success");
            loadUsers(keyword.trim(), roleFilter);
            loadLogs();
        } catch (e) {
            toast((e as ApiError).message, "warning");
        } finally {
            setImporting(false);
        }
    };

    /** 选择 CSV 文件后读入文本框（仍可手工修改） */
    const handleFile = (file: File | undefined) => {
        if (!file) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            setImportText(String(reader.result || ""));
        };
        reader.readAsText(file);
    };

    return (
        <TeacherLayout breadcrumb={["工作台", "账号管理"]} searchPlaceholder="搜索账号或姓名">
            <div className="page-head">
                <div>
                    <div className="page-title">账号管理</div>
                    <div className="page-sub">
                        共 {users.length} 个账号 · 管理员可创建教师 / 管理员账号、批量导入学生名单并查看审计日志
                    </div>
                </div>
                <div className="page-actions">
                    <select className="select"
                            style={SmallInputStyle}
                            value={roleFilter}
                            onChange={event => {
                                setRoleFilter(event.target.value);
                                loadUsers(keyword.trim(), event.target.value);
                            }}>
                        <option value="">全部角色</option>
                        {RoleOptions.map(role => (
                            <option key={role} value={role}>{roleLabel(role)}</option>
                        ))}
                    </select>
                    <input className="input"
                           style={SmallInputStyle}
                           placeholder="搜索账号 / 姓名"
                           value={keyword}
                           onChange={event => setKeyword(event.target.value)}
                           onKeyDown={event => {
                               if (event.key === "Enter") {
                                   loadUsers(keyword.trim(), roleFilter);
                               }
                           }}/>
                    <button type="button" className="btn btn-secondary" onClick={() => loadUsers(keyword.trim(), roleFilter)}>
                        <Icon name="search" size={13}/>搜索
                    </button>
                    <button type="button" className="btn btn-primary" onClick={() => {
                        setEditForm(null);
                        setFormError(null);
                        setCreateForm({ ...EmptyCreateForm });
                    }}>
                        <Icon name="plus" size={13}/>新建账号
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={() => loadUsers(keyword.trim(), roleFilter)}>
                            重试
                        </span>
                    </div>
                </div>
            )}

            {/* 新建账号 */}
            {createForm && (
                <div className="card" style={{ marginBottom: 14 }}>
                    <div className="card-head">
                        <div>
                            <div className="card-title">新建账号</div>
                            <div className="card-sub">教师 / 管理员账号不开放自助注册，由管理员在此创建</div>
                        </div>
                        <div className="table-tools">
                            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setCreateForm(null)}>
                                取消
                            </button>
                            <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={handleCreate}>
                                <Icon name="check" size={12}/>{saving ? "创建中…" : "创建账号"}
                            </button>
                        </div>
                    </div>
                    <div className="card-body">
                        <div className="form-grid two">
                            <div className="field">
                                <div className="label">账号（学号 / 工号）</div>
                                <input className="input" style={SmallInputStyle} value={createForm.username}
                                       placeholder="如 2023012345"
                                       onChange={event => setCreateForm({ ...createForm, username: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">姓名</div>
                                <input className="input" style={SmallInputStyle} value={createForm.nickname}
                                       placeholder="如 李同学"
                                       onChange={event => setCreateForm({ ...createForm, nickname: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">初始密码（至少 6 位）</div>
                                <input className="input" style={SmallInputStyle} value={createForm.password}
                                       type="text"
                                       placeholder="分发后请提示本人修改"
                                       onChange={event => setCreateForm({ ...createForm, password: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">角色</div>
                                <select className="select" style={SmallInputStyle} value={createForm.role}
                                        onChange={event => setCreateForm({ ...createForm, role: event.target.value as Role })}>
                                    {RoleOptions.map(role => (
                                        <option key={role} value={role}>{roleLabel(role)}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field">
                                <div className="label">邮箱（可选）</div>
                                <input className="input" style={SmallInputStyle} value={createForm.email}
                                       placeholder="name@tsinghua.edu.cn"
                                       onChange={event => setCreateForm({ ...createForm, email: event.target.value })}/>
                            </div>
                        </div>
                        {formError && (
                            <div className="login-error" style={{ marginTop: 8 }}>
                                <Icon name="alert-triangle" size={12}/>{formError}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 编辑账号 */}
            {editForm && (
                <div className="card" style={{ marginBottom: 14 }}>
                    <div className="card-head">
                        <div>
                            <div className="card-title">编辑账号 {editForm.user.username}</div>
                            <div className="card-sub">修改姓名 / 角色 / 邮箱；重置密码留空表示不修改</div>
                        </div>
                        <div className="table-tools">
                            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditForm(null)}>
                                取消
                            </button>
                            <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={handleUpdate}>
                                <Icon name="check" size={12}/>{saving ? "保存中…" : "保存修改"}
                            </button>
                        </div>
                    </div>
                    <div className="card-body">
                        <div className="form-grid two">
                            <div className="field">
                                <div className="label">姓名</div>
                                <input className="input" style={SmallInputStyle} value={editForm.nickname}
                                       onChange={event => setEditForm({ ...editForm, nickname: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">角色</div>
                                <select className="select" style={SmallInputStyle} value={editForm.role}
                                        onChange={event => setEditForm({ ...editForm, role: event.target.value as Role })}>
                                    {RoleOptions.map(role => (
                                        <option key={role} value={role}>{roleLabel(role)}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field">
                                <div className="label">邮箱</div>
                                <input className="input" style={SmallInputStyle} value={editForm.email}
                                       onChange={event => setEditForm({ ...editForm, email: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">重置密码（可选）</div>
                                <input className="input" style={SmallInputStyle} value={editForm.password}
                                       type="text" placeholder="留空表示不修改"
                                       onChange={event => setEditForm({ ...editForm, password: event.target.value })}/>
                            </div>
                        </div>
                        {formError && (
                            <div className="login-error" style={{ marginTop: 8 }}>
                                <Icon name="alert-triangle" size={12}/>{formError}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 账号列表 */}
            <div className="card">
                <div className="card-head">
                    <div>
                        <div className="card-title">全部账号</div>
                        <div className="card-sub">按创建时间倒序</div>
                    </div>
                    <div className="table-tools">
                        <span className="badge blue">{users.length} 人</span>
                    </div>
                </div>
                <table className="table">
                    <thead>
                    <tr>
                        <th>账号</th>
                        <th>姓名</th>
                        <th>角色</th>
                        <th>邮箱</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                    </thead>
                    <tbody>
                    {loading && (
                        <tr><td colSpan={6} style={{ color: "#94a3b8" }}>加载中…</td></tr>
                    )}
                    {!loading && users.length === 0 && (
                        <tr><td colSpan={6} style={{ color: "#94a3b8" }}>暂无账号</td></tr>
                    )}
                    {users.map(user => (
                        <tr key={user.id}>
                            <td style={{ fontWeight: 600 }}>{user.username}</td>
                            <td>{user.nickname}</td>
                            <td><span className={RoleBadge[user.role] || "badge gray"}>{roleLabel(user.role)}</span></td>
                            <td style={{ color: "#64748b" }}>{user.email || "—"}</td>
                            <td style={{ color: "#64748b" }}>{formatTime(user.created)}</td>
                            <td>
                                <span className="link" onClick={() => {
                                    setCreateForm(null);
                                    setFormError(null);
                                    setEditForm({
                                        user,
                                        nickname: user.nickname,
                                        role: user.role,
                                        email: user.email,
                                        password: "",
                                    });
                                }}>编辑</span>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
                <div className="table-footer">
                    <span>共 {users.length} 个账号</span>
                    <span className="muted">所有账号操作都会写入审计日志</span>
                </div>
            </div>

            {/* 批量导入 */}
            <div className="card" style={{ marginTop: 14 }}>
                <div className="card-head">
                    <div>
                        <div className="card-title">批量导入名单（CSV）</div>
                        <div className="card-sub">
                            每行「账号,姓名[,角色][,邮箱]」，角色支持 student/teacher/admin 或 学生/教师/管理员；初始密码为账号本身
                        </div>
                    </div>
                    <div className="table-tools">
                        <input ref={fileRef} type="file" accept=".csv,text/csv" style={{ display: "none" }}
                               onChange={event => handleFile(event.target.files ? event.target.files[0] : undefined)}/>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => fileRef.current && fileRef.current.click()}>
                            <Icon name="file-text" size={12}/>选择 CSV 文件
                        </button>
                        <button type="button" className="btn btn-primary btn-sm" disabled={importing || !importText.trim()}
                                onClick={handleImport}>
                            <Icon name="arrow-up" size={12}/>{importing ? "导入中…" : "开始导入"}
                        </button>
                    </div>
                </div>
                <div className="card-body">
                    <textarea className="input"
                              style={{
                                  width: "100%",
                                  minHeight: 90,
                                  padding: "6px 8px",
                                  fontSize: 11.5,
                                  lineHeight: 1.6,
                                  fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", Menlo, monospace",
                                  resize: "vertical",
                              }}
                              placeholder={"username,nickname,role\n2023010001,张三,学生\n2023010002,李四,student"}
                              value={importText}
                              onChange={event => setImportText(event.target.value)}/>
                    {importResult && (
                        <table className="table" style={{ marginTop: 10 }}>
                            <thead>
                            <tr>
                                <th>行号</th>
                                <th>账号</th>
                                <th>结果</th>
                                <th>说明</th>
                            </tr>
                            </thead>
                            <tbody>
                            {importResult.results.map(row => (
                                <tr key={row.line}>
                                    <td>{row.line}</td>
                                    <td style={{ fontWeight: 600 }}>{row.username || "—"}</td>
                                    <td>
                                        <span className={row.ok ? "badge green" : "badge red"}>
                                            {row.ok ? "成功" : "失败"}
                                        </span>
                                    </td>
                                    <td style={{ color: "#64748b" }}>{row.message}</td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* 审计日志 */}
            <div className="card" style={{ marginTop: 14 }}>
                <div className="card-head">
                    <div>
                        <div className="card-title">审计日志</div>
                        <div className="card-sub">最近 100 条登录与账号 / 题库操作记录</div>
                    </div>
                    <div className="table-tools">
                        <span className="icon-btn plain" title="刷新" onClick={loadLogs}>
                            <Icon name="refresh" size={14}/>
                        </span>
                    </div>
                </div>
                <table className="table">
                    <thead>
                    <tr>
                        <th>时间</th>
                        <th>操作人</th>
                        <th>动作</th>
                        <th>详情</th>
                    </tr>
                    </thead>
                    <tbody>
                    {logs.length === 0 && (
                        <tr><td colSpan={4} style={{ color: "#94a3b8" }}>暂无记录</td></tr>
                    )}
                    {logs.map(log => (
                        <tr key={log.id}>
                            <td style={{ color: "#64748b" }}>{formatTime(log.created)}</td>
                            <td style={{ fontWeight: 600 }}>{log.username}</td>
                            <td><span className="badge gray">{log.action}</span></td>
                            <td style={{ color: "#64748b" }}>{log.detail}</td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </TeacherLayout>
    );
}
