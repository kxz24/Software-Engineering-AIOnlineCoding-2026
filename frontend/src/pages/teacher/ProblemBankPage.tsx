import React, { useEffect, useState } from "react";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import {
    ApiError,
    createProblem,
    deleteProblem,
    fetchProblem,
    fetchProblems,
    ProblemSummary,
    SamplePayload,
    updateProblem,
} from "../../api/client";

/** 题型 / 语言 / 难度的展示与选项映射（与后端 problem.models 的 choices 对应） */
const TypeLabels: Record<string, string> = {
    engineering: "工程题",
    algorithm: "算法题",
};

const LanguageLabels: Record<string, string> = {
    python: "Python",
    cpp: "C++",
    c: "C",
    java: "Java",
};

const DifficultyLabels: Record<string, string> = {
    easy: "简单",
    medium: "中等",
    hard: "困难",
};

const DifficultyBadge: Record<string, string> = {
    easy: "badge green",
    medium: "badge gray",
    hard: "badge red",
};

/** 表单里的用例（提交时去掉本地 id 之外的额外字段） */
type SampleForm = SamplePayload;

/** 编辑器表单：id 为空表示新建 */
interface ProblemForm {
    id: number | null;
    title: string;
    type: string;
    language: string;
    difficulty: string;
    image: string;
    description: string;
    starterCode: string;
    samples: SampleForm[];
}

const EmptyForm: ProblemForm = {
    id: null,
    title: "",
    type: "engineering",
    language: "python",
    difficulty: "medium",
    image: "",
    description: "",
    starterCode: "",
    samples: [],
};

/** 后端返回的 ISO 时间 → 本地「MM-DD HH:mm」 */
function formatTime(iso: string): string {
    const date = new Date(iso);
    if (isNaN(date.getTime())) {
        return iso;
    }
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 表单与用例编辑器共用的小号输入样式 */
const SmallInputStyle: React.CSSProperties = {
    height: 30,
    padding: "0 8px",
    fontSize: 11.5,
};

const SmallAreaStyle: React.CSSProperties = {
    width: "100%",
    minHeight: 44,
    padding: "6px 8px",
    fontSize: 11.5,
    lineHeight: 1.5,
    fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", Menlo, monospace",
    resize: "vertical",
};

/**
 * 题库管理（教师 / 管理员）：题目列表 + 新建 / 编辑表单 + 测试样例管理。
 *
 * 对应迭代计划第一轮「题库与测试样例管理」：样例测试对学生可见，
 * 隐藏测试仅用于判分；接口见 /api/v1/problems。
 */
export function ProblemBankPage() {
    const [problems, setProblems] = useState<ProblemSummary[]>([]);
    const [keyword, setKeyword] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [form, setForm] = useState<ProblemForm | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    const loadProblems = (search: string) => {
        setLoading(true);
        setError(null);
        fetchProblems(search ? { keyword: search } : {})
            .then(result => {
                setProblems(result.problems);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(() => {
        loadProblems("");
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const openCreate = () => {
        setForm({ ...EmptyForm, samples: [] });
        setFormError(null);
    };

    const openEdit = (problemId: number) => {
        setFormError(null);
        fetchProblem(problemId)
            .then(detail => {
                setForm({
                    id: detail.id,
                    title: detail.title,
                    type: detail.type,
                    language: detail.language,
                    difficulty: detail.difficulty,
                    image: detail.image,
                    description: detail.description,
                    starterCode: detail.starterCode,
                    samples: detail.samples.map(sample => ({
                        name: sample.name,
                        input: sample.input,
                        expected: sample.expected,
                        isSample: sample.isSample,
                    })),
                });
            })
            .catch((e: ApiError) => setFormError(e.message));
    };

    const handleSave = async () => {
        if (!form || saving) {
            return;
        }
        if (!form.title.trim()) {
            setFormError("请填写题目标题。");
            return;
        }
        if (form.samples.some(sample => !sample.name.trim())) {
            setFormError("每个测试用例都需要名称。");
            return;
        }
        setSaving(true);
        setFormError(null);
        const payload = {
            title: form.title.trim(),
            description: form.description,
            type: form.type,
            language: form.language,
            difficulty: form.difficulty,
            image: form.image.trim(),
            starterCode: form.starterCode,
            samples: form.samples,
        };
        try {
            if (form.id == null) {
                await createProblem(payload);
                toast("题目已创建", "success");
            } else {
                await updateProblem(form.id, payload);
                toast("题目已保存", "success");
            }
            setForm(null);
            loadProblems(keyword);
        } catch (e) {
            setFormError((e as ApiError).message);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = (problem: ProblemSummary) => {
        const confirmed = window.confirm(`确认删除题目「${problem.title}」？其测试用例将一并删除。`);
        if (!confirmed) {
            return;
        }
        deleteProblem(problem.id)
            .then(() => {
                toast("题目已删除", "success");
                loadProblems(keyword);
            })
            .catch((e: ApiError) => setError(e.message));
    };

    const updateSample = (index: number, patch: Partial<SampleForm>) => {
        if (!form) {
            return;
        }
        setForm({
            ...form,
            samples: form.samples.map((sample, i) => (i === index ? { ...sample, ...patch } : sample)),
        });
    };

    const addSample = (isSample: boolean) => {
        if (!form) {
            return;
        }
        const count = form.samples.filter(sample => sample.isSample === isSample).length + 1;
        const prefix = isSample ? "样例" : "隐藏";
        setForm({
            ...form,
            samples: [
                ...form.samples,
                { name: `${prefix} ${count}`, input: "", expected: "", isSample },
            ],
        });
    };

    return (
        <TeacherLayout breadcrumb={["工作台", "题库管理"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">题库管理</div>
                    <div className="page-sub">
                        共 {problems.length} 道题 · 样例测试对考生可见，隐藏测试仅用于判分
                    </div>
                </div>
                <div className="page-actions">
                    <input className="input"
                           style={SmallInputStyle}
                           placeholder="搜索标题 / 题面"
                           value={keyword}
                           onChange={event => setKeyword(event.target.value)}
                           onKeyDown={event => {
                               if (event.key === "Enter") {
                                   loadProblems(keyword.trim());
                               }
                           }}/>
                    <button type="button" className="btn btn-secondary" onClick={() => loadProblems(keyword.trim())}>
                        <Icon name="search" size={13}/>搜索
                    </button>
                    <button type="button" className="btn btn-primary" onClick={openCreate}>
                        <Icon name="plus" size={13}/>新建题目
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={() => loadProblems(keyword.trim())}>
                            重试
                        </span>
                    </div>
                </div>
            )}

            {/* 新建 / 编辑表单 */}
            {form && (
                <div className="card" style={{ marginBottom: 14 }}>
                    <div className="card-head">
                        <div>
                            <div className="card-title">{form.id == null ? "新建题目" : `编辑题目 #${form.id}`}</div>
                            <div className="card-sub">题面、初始代码与测试样例；隐藏测试不会下发给考生</div>
                        </div>
                        <div className="table-tools">
                            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setForm(null)}>
                                取消
                            </button>
                            <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={handleSave}>
                                <Icon name="check" size={12}/>{saving ? "保存中…" : "保存题目"}
                            </button>
                        </div>
                    </div>
                    <div className="card-body">
                        <div className="form-grid two">
                            <div className="field">
                                <div className="label">题目标题</div>
                                <input className="input"
                                       style={SmallInputStyle}
                                       value={form.title}
                                       placeholder="如：修复订单排序并补充测试"
                                       onChange={event => setForm({ ...form, title: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">依赖镜像（可选）</div>
                                <input className="input"
                                       style={SmallInputStyle}
                                       value={form.image}
                                       placeholder="如 python:3.11-slim"
                                       onChange={event => setForm({ ...form, image: event.target.value })}/>
                            </div>
                            <div className="field">
                                <div className="label">题型</div>
                                <select className="select"
                                        style={SmallInputStyle}
                                        value={form.type}
                                        onChange={event => setForm({ ...form, type: event.target.value })}>
                                    {Object.keys(TypeLabels).map(key => (
                                        <option key={key} value={key}>{TypeLabels[key]}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field">
                                <div className="label">判题语言</div>
                                <select className="select"
                                        style={SmallInputStyle}
                                        value={form.language}
                                        onChange={event => setForm({ ...form, language: event.target.value })}>
                                    {Object.keys(LanguageLabels).map(key => (
                                        <option key={key} value={key}>{LanguageLabels[key]}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field">
                                <div className="label">难度</div>
                                <select className="select"
                                        style={SmallInputStyle}
                                        value={form.difficulty}
                                        onChange={event => setForm({ ...form, difficulty: event.target.value })}>
                                    {Object.keys(DifficultyLabels).map(key => (
                                        <option key={key} value={key}>{DifficultyLabels[key]}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="field" style={{ marginTop: 12 }}>
                            <div className="label">题面（Markdown）</div>
                            <textarea className="input"
                                      style={{ ...SmallAreaStyle, minHeight: 90, fontFamily: "inherit" }}
                                      value={form.description}
                                      placeholder="任务背景、要求与验收标准"
                                      onChange={event => setForm({ ...form, description: event.target.value })}/>
                        </div>
                        <div className="field" style={{ marginTop: 10 }}>
                            <div className="label">初始代码 / 仓库说明</div>
                            <textarea className="input"
                                      style={SmallAreaStyle}
                                      value={form.starterCode}
                                      placeholder="def solution(): pass"
                                      onChange={event => setForm({ ...form, starterCode: event.target.value })}/>
                        </div>

                        <div className="card-head" style={{ marginTop: 16 }}>
                            <div>
                                <div className="card-title">测试样例</div>
                                <div className="card-sub">
                                    样例 {form.samples.filter(sample => sample.isSample).length} 条 ·
                                    隐藏 {form.samples.filter(sample => !sample.isSample).length} 条
                                </div>
                            </div>
                            <div className="table-tools">
                                <button type="button" className="btn btn-secondary btn-sm" onClick={() => addSample(true)}>
                                    <Icon name="plus" size={12}/>添加样例
                                </button>
                                <button type="button" className="btn btn-secondary btn-sm" onClick={() => addSample(false)}>
                                    <Icon name="lock" size={12}/>添加隐藏用例
                                </button>
                            </div>
                        </div>

                        {form.samples.length === 0 && (
                            <div className="card-sub" style={{ padding: "8px 0" }}>还没有测试用例</div>
                        )}
                        {form.samples.map((sample, index) => (
                            <div key={index}
                                 style={{
                                     display: "grid",
                                     gridTemplateColumns: "140px 1fr 1fr 84px 32px",
                                     gap: 8,
                                     alignItems: "start",
                                     marginBottom: 8,
                                 }}>
                                <input className="input"
                                       style={SmallInputStyle}
                                       value={sample.name}
                                       placeholder="用例名称"
                                       onChange={event => updateSample(index, { name: event.target.value })}/>
                                <textarea className="input"
                                          style={SmallAreaStyle}
                                          value={sample.input}
                                          placeholder="输入"
                                          onChange={event => updateSample(index, { input: event.target.value })}/>
                                <textarea className="input"
                                          style={SmallAreaStyle}
                                          value={sample.expected}
                                          placeholder="期望输出"
                                          onChange={event => updateSample(index, { expected: event.target.value })}/>
                                <span className={"badge " + (sample.isSample ? "blue" : "gray")}
                                      style={{ cursor: "pointer", textAlign: "center", marginTop: 6 }}
                                      title="点击切换可见性"
                                      onClick={() => updateSample(index, { isSample: !sample.isSample })}>
                                    {sample.isSample ? "样例可见" : "隐藏"}
                                </span>
                                <span className="link"
                                      title="删除该用例"
                                      style={{ color: "#dc2626", marginTop: 8, whiteSpace: "nowrap" }}
                                      onClick={() => setForm({
                                          ...form,
                                          samples: form.samples.filter((_item, i) => i !== index),
                                      })}>
                                    删除
                                </span>
                            </div>
                        ))}

                        {formError && (
                            <div className="login-error" style={{ marginTop: 8 }}>
                                <Icon name="alert-triangle" size={12}/>{formError}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 题目列表 */}
            <div className="card">
                <div className="card-head">
                    <div>
                        <div className="card-title">全部题目</div>
                        <div className="card-sub">按更新时间倒序</div>
                    </div>
                    <div className="table-tools">
                        <span className="badge blue">{problems.length} 题</span>
                    </div>
                </div>
                <table className="table">
                    <thead>
                    <tr>
                        <th>标题</th>
                        <th>题型</th>
                        <th>语言</th>
                        <th>难度</th>
                        <th>样例</th>
                        <th>隐藏</th>
                        <th>更新时间</th>
                        <th>操作</th>
                    </tr>
                    </thead>
                    <tbody>
                    {loading && (
                        <tr><td colSpan={8} style={{ color: "#94a3b8" }}>加载中…</td></tr>
                    )}
                    {!loading && problems.length === 0 && (
                        <tr>
                            <td colSpan={8} style={{ color: "#94a3b8" }}>
                                题库还是空的，点击右上角「新建题目」开始命题
                            </td>
                        </tr>
                    )}
                    {problems.map(problem => (
                        <tr key={problem.id}>
                            <td style={{ fontWeight: 600 }}>{problem.title}</td>
                            <td><span className="badge blue">{TypeLabels[problem.type] || problem.type}</span></td>
                            <td>{LanguageLabels[problem.language] || problem.language}</td>
                            <td>
                                <span className={DifficultyBadge[problem.difficulty] || "badge gray"}>
                                    {DifficultyLabels[problem.difficulty] || problem.difficulty}
                                </span>
                            </td>
                            <td>{problem.sampleCount}</td>
                            <td>{problem.hiddenCount}</td>
                            <td>{formatTime(problem.updated)}</td>
                            <td>
                                <span className="link" onClick={() => openEdit(problem.id)}>编辑</span>
                                <span style={{ color: "#e2e8f0", margin: "0 6px" }}>|</span>
                                <span className="link" style={{ color: "#dc2626" }} onClick={() => handleDelete(problem)}>
                                    删除
                                </span>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
                <div className="table-footer">
                    <span>共 {problems.length} 道题</span>
                    <span className="muted">隐藏测试仅在判题沙箱运行，不会挂载到考生容器</span>
                </div>
            </div>
        </TeacherLayout>
    );
}
