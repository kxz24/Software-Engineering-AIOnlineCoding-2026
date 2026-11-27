import React, { useEffect, useRef, useState } from "react";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import {
    ApiError,
    createProblem,
    deleteProblem,
    fetchProblem,
    fetchProblems,
    importProject,
    retryProjectPreparation,
    ProblemSummary,
    SamplePayload,
    updateProblem,
} from "../../api/client";

/** 题型 / 语言 / 难度的展示与选项映射（与后端 problem.models 的 choices 对应） */
const TypeLabels: Record<string, string> = {
    engineering: "工程题",
    algorithm: "算法题",
};

/** 表单里的题型选项：直接标出当前是否支持自动判题 */
const TypeOptionLabels: Record<string, string> = {
    algorithm: "算法题（自动判题）",
    engineering: "工程题",
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
    hasProjectBundle?: boolean;
    title: string;
    type: string;
    language: string;
    difficulty: string;
    image: string;
    projectFiles: Partial<Record<"starterArchive" | "workspaceTemplate" | "publicScript" | "hiddenScript", boolean>>;
    description: string;
    starterCode: string;
    timeLimitMs: number;
    memoryLimitMb: number;
    outputLimitKb: number;
    practiceEnabled: boolean;
    samples: SampleForm[];
}

const EmptyForm: ProblemForm = {
    id: null,
    title: "",
    type: "algorithm",
    language: "python",
    difficulty: "medium",
    image: "",
    projectFiles: {},
    description: "",
    starterCode: "",
    timeLimitMs: 2000,
    memoryLimitMb: 256,
    outputLimitKb: 1024,
    practiceEnabled: true,
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
    const projectInput = useRef<HTMLInputElement>(null);
    const [problems, setProblems] = useState<ProblemSummary[]>([]);
    const [keyword, setKeyword] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [projectUploads, setProjectUploads] = useState<Partial<Record<"starterArchive" | "workspaceTemplate" | "publicScript" | "hiddenScript", File>>>({});
    const [form, setForm] = useState<ProblemForm | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);

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

    const preparing = problems.some(problem =>
        problem.preparationStatus === "pending" || problem.preparationStatus === "preparing"
    );
    useEffect(() => {
        if (!preparing) return;
        const timer = window.setInterval(() => {
            fetchProblems(keyword ? { keyword } : {})
                .then(result => setProblems(result.problems))
                .catch((e: ApiError) => setError(e.message));
        }, 5000);
        return () => window.clearInterval(timer);
    }, [preparing, keyword]);

    const openCreate = () => {
        setProjectUploads({});
        setForm({ ...EmptyForm, samples: [] });
        setFormError(null);
    };

    const openEdit = (problemId: number) => {
        setProjectUploads({});
        setFormError(null);
        fetchProblem(problemId)
            .then(detail => {
                setForm({
                    id: detail.id,
                    hasProjectBundle: detail.hasProjectBundle,
                    title: detail.title,
                    type: detail.type,
                    language: detail.language,
                    difficulty: detail.difficulty,
                    image: detail.image,
                    projectFiles: detail.projectFiles || {},
                    description: detail.description,
                    starterCode: detail.starterCode,
                    timeLimitMs: detail.timeLimitMs,
                    memoryLimitMb: detail.memoryLimitMb,
                    outputLimitKb: detail.outputLimitKb,
                    practiceEnabled: detail.practiceEnabled !== false,
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
        if (form.type === "algorithm") {
            if (!form.description.trim()) {
                setFormError("算法题需要填写题目描述。");
                return;
            }
            if (form.samples.length === 0) {
                setFormError("算法题至少需要一条测试用例。");
                return;
            }
        }
        if (form.type === "engineering" && !form.hasProjectBundle && (["publicScript", "hiddenScript"] as const).some(
            key => !projectUploads[key] && !form.projectFiles[key]
        )) {
            setFormError("请上传公开和隐藏评分脚本。");
            return;
        }
        if (form.type === "algorithm" && form.samples.some(sample => !sample.name.trim())) {
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
            judgeProfile: form.type === "engineering" ? "script" : "",
            starterCode: form.starterCode,
            timeLimitMs: Number(form.timeLimitMs),
            memoryLimitMb: Number(form.memoryLimitMb),
            outputLimitKb: Number(form.outputLimitKb),
            practiceEnabled: form.practiceEnabled,
            samples: form.type === "algorithm" ? form.samples : [],
        };
        try {
            if (form.id == null) {
                await createProblem(payload, form.type === "engineering" ? projectUploads : undefined);
                toast("题目已创建", "success");
            } else {
                await updateProblem(form.id, form.hasProjectBundle ? {
                    title: payload.title, description: payload.description, difficulty: payload.difficulty,
                } : payload, form.type === "engineering" && !form.hasProjectBundle ? projectUploads : undefined);
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
                        共 {problems.length} 道题 · 多文件工程题通过 ZIP 导入并自动试跑教师参考提交
                    </div>
                </div>
                <div className="page-actions">
                    <input ref={projectInput} type="file" accept=".zip,application/zip" style={{ display: "none" }}
                           onChange={event => {
                               const file = event.target.files && event.target.files[0];
                               if (!file) return;
                               if (file.size > 8 * 1024 * 1024) {
                                   setError("工程题 ZIP 不能超过 8 MB");
                                   event.target.value = "";
                                   return;
                               }
                               setUploading(true);
                               importProject(file)
                                   .then(result => {
                                       toast(result.preparationStatus === "ready" ? "工程题已导入" :
                                           "工程题已上传，正在准备环境并试跑参考提交", "success");
                                       loadProblems(keyword);
                                   })
                                   .catch((e: ApiError) => setError(e.message))
                                   .finally(() => setUploading(false));
                               event.target.value = "";
                           }}/>
                    <button type="button" className="btn btn-secondary" style={{ whiteSpace: "nowrap" }} disabled={uploading}
                            onClick={() => projectInput.current?.click()}>
                        {uploading ? "上传中…" : "导入工程题 ZIP"}
                    </button>
                    <input className="input"
                           style={{ ...SmallInputStyle, width: 176, flex: "0 0 176px" }}
                           placeholder="搜索标题 / 题面"
                           value={keyword}
                           onChange={event => setKeyword(event.target.value)}
                           onKeyDown={event => {
                               if (event.key === "Enter") {
                                   loadProblems(keyword.trim());
                               }
                           }}/>
                    <button type="button" className="btn btn-secondary" style={{ whiteSpace: "nowrap" }} onClick={() => loadProblems(keyword.trim())}>
                        <Icon name="search" size={13}/>搜索
                    </button>
                    <button type="button" className="btn btn-primary" style={{ whiteSpace: "nowrap" }} onClick={openCreate}>
                        <Icon name="plus" size={13}/>新建题目
                    </button>
                </div>
            </div>

            <details className="card" style={{ marginBottom: 14 }}>
                <summary style={{ cursor: "pointer", padding: "11px 16px", fontSize: 12, fontWeight: 600, color: "#334155" }}>
                    多文件工程题怎么准备？展开查看题包清单
                </summary>
                <div className="card-body" style={{ borderTop: "1px solid #eef2f7", fontSize: 12, color: "#475569", lineHeight: 1.7 }}>
                    <div>① <strong>public/</strong> 放学生可编辑文件；<strong>private/</strong> 放评分脚本和隐藏测试。</div>
                    <div>② <strong>private/selfcheck/</strong> 放可用的参考提交，路径与 public/ 对应。</div>
                    <div>③ 在 <strong>project.json</strong> 写题面、评分命令和 Debian/Python 依赖；三项直接放在 ZIP 顶层。</div>
                    <div style={{ marginTop: 6, color: "#64748b" }}>
                        上传后平台会构建环境并试跑参考提交。自检通过后即可组卷；有特殊工具链时可在 private/Dockerfile 配置。
                    </div>
                </div>
            </details>

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
                                <div className="label">依赖镜像（预留，暂不生效）</div>
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
                                        disabled={form.hasProjectBundle}
                                        onChange={event => setForm({ ...form, type: event.target.value })}>
                                    {Object.keys(TypeOptionLabels).map(key => (
                                        <option key={key} value={key}>{TypeOptionLabels[key]}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field">
                                <div className="label">判题语言</div>
                                <select className="select"
                                        style={SmallInputStyle}
                                        value={form.language}
                                        disabled={form.hasProjectBundle}
                                        onChange={event => setForm({ ...form, language: event.target.value })}>
                                    {form.hasProjectBundle && !LanguageLabels[form.language] && (
                                        <option value={form.language}>{form.language}</option>
                                    )}
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
                            <div className="field">
                                <div className="label">自由练习</div>
                                <label className="muted"
                                       style={{ display: "flex", alignItems: "center", gap: 6, height: 30, fontSize: 11.5 }}>
                                    <input type="checkbox"
                                           checked={form.practiceEnabled}
                                           onChange={event => setForm({ ...form, practiceEnabled: event.target.checked })}/>
                                    开放给学生自主练习
                                </label>
                            </div>
                            <div className="field">
                                <div className="label">单用例时限（毫秒）</div>
                                <input className="input"
                                       type="number"
                                       min={100}
                                       max={10000}
                                       style={SmallInputStyle}
                                       value={form.timeLimitMs}
                                       onChange={event => setForm({ ...form, timeLimitMs: Number(event.target.value) })}/>
                            </div>
                            <div className="field">
                                <div className="label">内存上限（MB）</div>
                                <input className="input"
                                       type="number"
                                       min={16}
                                       max={1024}
                                       style={SmallInputStyle}
                                       value={form.memoryLimitMb}
                                       onChange={event => setForm({ ...form, memoryLimitMb: Number(event.target.value) })}/>
                            </div>
                            <div className="field">
                                <div className="label">输出上限（KB）</div>
                                <input className="input"
                                       type="number"
                                       min={1}
                                       max={10240}
                                       style={SmallInputStyle}
                                       value={form.outputLimitKb}
                                       onChange={event => setForm({ ...form, outputLimitKb: Number(event.target.value) })}/>
                            </div>
                        </div>
                        {form.type === "algorithm" ? (
                            <div className="card-sub" style={{ marginTop: 8 }}>
                                算法题：填写题面并添加测试用例即可创建；语言、时限、内存有默认值。
                                建议至少添加一条隐藏用例用于判分。
                            </div>
                        ) : (
                            <div className="card-sub" style={{ marginTop: 8 }}>
                                {form.hasProjectBundle ? "学生提交题包中的全部公开文件，平台按题包评分。" :
                                    "学生提交源码包，平台按公开和隐藏脚本自动计分。"}
                            </div>
                        )}

                        <div className="field" style={{ marginTop: 12 }}>
                            <div className="label">题面（Markdown）</div>
                            <textarea className="input"
                                      style={{ ...SmallAreaStyle, minHeight: 90, fontFamily: "inherit" }}
                                      value={form.description}
                                      placeholder="任务背景、要求与验收标准"
                                      onChange={event => setForm({ ...form, description: event.target.value })}/>
                        </div>
                        {form.type === "algorithm" ? <>
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

                        </> : !form.hasProjectBundle && (
                            <fieldset className="field" style={{ marginTop: 12 }}>
                                <legend className="label">工程题附件</legend>
                                {([
                                    ["workspaceTemplate", "在线工作区模板（学生打开题目时自动加载）", ".zip", "16 MB"],
                                    ["starterArchive", "课程资料包（可选，学生可下载）", ".zip", "16 MB"],
                                    ["publicScript", "公开评分脚本（学生可下载和试运行）", ".py", "256 KB"],
                                    ["hiddenScript", "隐藏评分脚本（仅正式评分）", ".py", "256 KB"],
                                ] as const).map(([key, label, accept, limit]) => (
                                    <label className="field" key={key}>
                                        <span className="label">{label}</span>
                                        <input type="file" accept={accept}
                                               onChange={event => setProjectUploads(current => ({
                                                   ...current, [key]: event.target.files?.[0],
                                               }))}/>
                                        <small className="muted">{projectUploads[key]?.name
                                            || (form.projectFiles[key] ? "已有附件，选新文件替换" : `上限 ${limit}`)}</small>
                                    </label>
                                ))}
                                <details>
                                    <summary>评分脚本格式与示例</summary>
                                    <p>每个脚本定义 grade(project)，返回评分项。两份脚本的得分之和除以满分之和，再按本题分值换算。</p>
                                    <pre>{`def grade(project):
    result = project.run(["python3", "main.py"], stdin="2 3\\n")
    passed = result["status"] == 0 and result["output"].strip() == "5"
    return [{"name": "正常输入", "points": 10 if passed else 0,
             "max_points": 10, "feedback": "" if passed else "结果不符"}]`}</pre>
                                    <p>服务类题目可用 project.start 启动学生程序，再通过本地回环与其交互。用 project.run 运行学生代码。</p>
                                </details>
                            </fieldset>
                        )}

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
                        <th>环境自检</th>
                        <th>难度</th>
                        <th>样例</th>
                        <th>隐藏</th>
                        <th>练习</th>
                        <th>更新时间</th>
                        <th>操作</th>
                    </tr>
                    </thead>
                    <tbody>
                    {loading && (
                        <tr><td colSpan={10} style={{ color: "#94a3b8" }}>加载中…</td></tr>
                    )}
                    {!loading && problems.length === 0 && (
                        <tr>
                            <td colSpan={10} style={{ color: "#94a3b8" }}>
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
                                {problem.hasProjectBundle ? (
                                    <>
                                        <span className={"badge " + (problem.preparationStatus === "ready" ? "green" :
                                            problem.preparationStatus === "failed" ? "red" : "gray")}>
                                            {problem.preparationStatus === "ready" ? "已通过" :
                                                problem.preparationStatus === "failed" ? "失败" : "准备中"}
                                        </span>
                                        {problem.preparationMessage && (
                                            <div style={{ maxWidth: 240, marginTop: 4, fontSize: 11, lineHeight: 1.4,
                                                color: problem.preparationStatus === "failed" ? "#b91c1c" : "#64748b",
                                                overflowWrap: "anywhere" }}>
                                                {problem.preparationMessage}
                                            </div>
                                        )}
                                        {problem.preparationStatus === "failed" && (
                                            <button type="button" className="link" style={{ marginTop: 4 }}
                                                    onClick={() => retryProjectPreparation(problem.id)
                                                        .then(() => { toast("已重新开始准备", "success"); loadProblems(keyword); })
                                                        .catch((e: ApiError) => setError(e.message))}>
                                                重试自检
                                            </button>
                                        )}
                                    </>
                                ) : "—"}
                            </td>
                            <td>
                                <span className={DifficultyBadge[problem.difficulty] || "badge gray"}>
                                    {DifficultyLabels[problem.difficulty] || problem.difficulty}
                                </span>
                            </td>
                            <td>{problem.hasProjectBundle ? "题包内" : problem.sampleCount}</td>
                            <td>{problem.hasProjectBundle ? "题包内" : problem.hiddenCount}</td>
                            <td>
                                <span className={"badge " + (problem.practiceEnabled ? "green" : "gray")}>
                                    {problem.practiceEnabled ? "开放" : "关闭"}
                                </span>
                            </td>
                            <td>{formatTime(problem.updated)}</td>
                            <td>
                                <span className="link" onClick={() => openEdit(problem.id)}>
                                    {problem.hasProjectBundle ? "编辑题面" : "编辑"}
                                </span>
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
                    <span className="muted">隐藏测试不在学生浏览器展示，仅在隔离判题容器中使用</span>
                </div>
            </div>
        </TeacherLayout>
    );
}
