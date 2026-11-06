import React, { useEffect, useState } from "react";
import { useHistory, useParams } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon, IconName } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { toInputValue } from "../../api/format";
import { ApiError, createExam, ExamDetail, fetchExam, setExamCandidates, updateExam } from "../../api/client";

/** 表单状态：时间与数字先用字符串承载，提交时再交给后端校验 */
interface ExamForm {
    title: string;
    course: string;
    startTime: string;
    endTime: string;
    duration: string;
    submitLimit: string;
    notice: string;
    description: string;
    candidates: string;
    aiMode: string;
}

const InitialForm: ExamForm = {
    title: "",
    course: "软件工程（2026 秋）",
    startTime: "",
    endTime: "",
    duration: "120",
    submitLimit: "2",
    notice: "开考 15 分钟后禁止入场；考试期间禁止外部网络。",
    description: "",
    candidates: "",
    aiMode: "limited",
};

const Courses = ["软件工程（2026 秋）", "数据结构（2026 秋）", "算法设计（2026 秋）"];

const SmallInputStyle: React.CSSProperties = { height: 30, padding: "0 8px", fontSize: 11.5 };

const AreaStyle: React.CSSProperties = {
    width: "100%",
    minHeight: 60,
    padding: "6px 8px",
    fontSize: 11.5,
    lineHeight: 1.5,
    resize: "vertical",
};

interface AiOption {
    key: string;
    title: string;
    desc: string;
    icon: IconName;
}

const AiOptions: AiOption[] = [
    { key: "open", title: "开放", desc: "完整对话与代码修改，全部留痕。", icon: "unlock" },
    { key: "limited", title: "受限", desc: "仅解释与运行测试，不可直接写入代码。", icon: "shield-check" },
    { key: "closed", title: "关闭", desc: "禁用 Agent，入口不可用。", icon: "lock" },
];

/**
 * 08 创建 / 编辑考试。
 *
 * /manage/new 为新建，/manage/:examId/edit 为编辑（已发布且未开始的考试也可修改）。
 * 保存后为草稿，组卷与名单在「题目配置」页继续。
 */
export function ExamCreatePage() {
    const { examId } = useParams<{ examId?: string }>();
    const editing = examId != null;
    const history = useHistory();

    const [form, setForm] = useState<ExamForm>(InitialForm);
    const [detail, setDetail] = useState<ExamDetail | null>(null);
    const [loading, setLoading] = useState(editing);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!editing) {
            return;
        }
        fetchExam(Number(examId))
            .then(result => {
                setDetail(result);
                setForm({
                    title: result.title,
                    course: result.course || Courses[0],
                    startTime: toInputValue(result.startTime),
                    endTime: toInputValue(result.endTime),
                    duration: String(result.durationMinutes),
                    submitLimit: String(result.submitLimit),
                    notice: result.notice,
                    description: result.description,
                    candidates: result.candidates.join("\n"),
                    aiMode: result.aiMode,
                });
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    }, [editing, examId]);

    const update = (patch: Partial<ExamForm>) => setForm(current => ({ ...current, ...patch }));

    /** 组装载荷并保存；成功后返回考试详情 */
    const save = async (): Promise<ExamDetail | null> => {
        if (!form.title.trim()) {
            toast("请填写考试名称", "warning");
            return null;
        }
        setSaving(true);
        const payload = {
            title: form.title.trim(),
            course: form.course.trim(),
            startTime: form.startTime,
            endTime: form.endTime,
            durationMinutes: Number(form.duration) || 120,
            submitLimit: Number(form.submitLimit) || 2,
            notice: form.notice,
            description: form.description,
            aiMode: form.aiMode,
        };
        try {
            let result: ExamDetail;
            if (editing) {
                result = await updateExam(Number(examId), payload);
                const candidates = form.candidates.split(/[\n,，]/).map(s => s.trim()).filter(Boolean);
                if (candidates.join("\n") !== detail?.candidates.join("\n")) {
                    result = await setExamCandidates(result.id, candidates);
                }
            } else {
                result = await createExam(payload);
                const candidates = form.candidates.split(/[\n,，]/).map(s => s.trim()).filter(Boolean);
                if (candidates.length > 0) {
                    result = await setExamCandidates(result.id, candidates);
                }
            }
            setSaving(false);
            return result;
        } catch (e) {
            setSaving(false);
            toast((e as ApiError).message, "warning");
            return null;
        }
    };

    const handleSaveDraft = async () => {
        const result = await save();
        if (result) {
            toast("已保存", "success");
            history.push(Routes.examManage);
        }
    };

    const handleNext = async () => {
        const result = await save();
        if (result) {
            history.push(Routes.problemConfig(result.id));
        }
    };

    /** 发布前检查：时间 / 题目 / 名单（SRS 3.3.2-4，发布接口也会兜底校验） */
    const checks = [
        {
            ok: !!form.startTime && !!form.endTime,
            text: form.startTime && form.endTime ? "考试时间已设置" : "待设置开始 / 结束时间",
        },
        {
            ok: (detail?.problemCount || 0) > 0,
            text: detail ? `题目 ${detail.problemCount} 道（保存后可在下一步组卷）` : "保存后进行组卷",
        },
        {
            ok: editing ? (detail?.candidates.length || 0) > 0 || (detail?.openToAll ?? true) : true,
            text: editing && detail
                ? (detail.openToAll ? "名单为空 = 全体学生可参加" : `名单 ${detail.candidateCount} 人`)
                : "名单为空 = 全体学生可参加",
        },
        { ok: true, text: `AI 策略：${AiOptions.find(o => o.key === form.aiMode)?.title}` },
    ];
    const okCount = checks.filter(check => check.ok).length;

    if (loading) {
        return (
            <TeacherLayout breadcrumb={["工作台", "考试管理", editing ? "编辑考试" : "创建考试"]}>
                <div className="card"><div className="card-body muted">加载中…</div></div>
            </TeacherLayout>
        );
    }

    return (
        <TeacherLayout breadcrumb={["工作台", "考试管理", editing ? "编辑考试" : "创建考试"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">{editing ? `编辑：${detail?.title || ""}` : "创建考试"}</div>
                    <div className="page-sub">配置考试时间、规则、AI 策略与考生名单</div>
                </div>
                <div className="page-actions">
                    <button type="button" className="btn btn-ghost" onClick={() => history.push(Routes.examManage)}>
                        <Icon name="arrow-left" size={14}/>返回
                    </button>
                    <button type="button" className="btn btn-secondary" disabled={saving} onClick={handleSaveDraft}>
                        保存
                    </button>
                    <button type="button" className="btn btn-primary" disabled={saving} onClick={handleNext}>
                        {saving ? "保存中…" : "保存并组卷"}<Icon name="arrow-right" size={14}/>
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                    </div>
                </div>
            )}

            <div className="create-main">
                <div className="card create-form">
                    <div className="card-body">
                        {/* 1 基本信息 */}
                        <div className="form-section">
                            <div className="section-head">
                                <span className="section-num">1</span>
                                <div>
                                    <div className="section-title">基本信息</div>
                                    <div className="section-sub">考试名称、课程与时间安排</div>
                                </div>
                            </div>
                            <div className="form-grid two">
                                <div className="field">
                                    <div className="label">考试名称 *</div>
                                    <input className="input" style={SmallInputStyle}
                                           value={form.title}
                                           placeholder="如：软件工程 · 期中机考"
                                           onChange={e => update({ title: e.target.value })}/>
                                </div>
                                <div className="field">
                                    <div className="label">课程</div>
                                    <select className="select" style={SmallInputStyle}
                                            value={form.course}
                                            onChange={e => update({ course: e.target.value })}>
                                        {Courses.map(course => (
                                            <option key={course} value={course}>{course}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div className="form-grid two">
                                <div className="field">
                                    <div className="label">开始时间 *</div>
                                    <input className="input" style={SmallInputStyle} type="datetime-local"
                                           value={form.startTime}
                                           onChange={e => update({ startTime: e.target.value })}/>
                                </div>
                                <div className="field">
                                    <div className="label">结束时间 *</div>
                                    <input className="input" style={SmallInputStyle} type="datetime-local"
                                           value={form.endTime}
                                           onChange={e => update({ endTime: e.target.value })}/>
                                </div>
                            </div>
                            <div className="form-grid two">
                                <div className="field">
                                    <div className="label">考试时长（分钟）*</div>
                                    <input className="input" style={SmallInputStyle} type="number" min={1}
                                           value={form.duration}
                                           onChange={e => update({ duration: e.target.value })}/>
                                </div>
                                <div className="field">
                                    <div className="label">每题提交次数上限 *</div>
                                    <input className="input" style={SmallInputStyle} type="number" min={1}
                                           value={form.submitLimit}
                                           onChange={e => update({ submitLimit: e.target.value })}/>
                                </div>
                            </div>
                        </div>

                        {/* 2 考生名单 */}
                        <div className="form-section">
                            <div className="section-head">
                                <span className="section-num">2</span>
                                <div>
                                    <div className="section-title">考生名单</div>
                                    <div className="section-sub">每行一个学号；留空表示全体学生可参加</div>
                                </div>
                            </div>
                            <div className="field">
                                <textarea className="input" style={AreaStyle}
                                          value={form.candidates}
                                          placeholder={"2023012345\n2023012346"}
                                          onChange={e => update({ candidates: e.target.value })}/>
                            </div>
                        </div>

                        {/* 3 考试说明 */}
                        <div className="form-section">
                            <div className="section-head">
                                <span className="section-num">3</span>
                                <div>
                                    <div className="section-title">考试说明与须知</div>
                                    <div className="section-sub">考试须知会展示在进入考场前的自检页</div>
                                </div>
                            </div>
                            <div className="field">
                                <div className="label">考试说明（可选）</div>
                                <textarea className="input" style={AreaStyle}
                                          value={form.description}
                                          placeholder="考核范围、题型说明等"
                                          onChange={e => update({ description: e.target.value })}/>
                            </div>
                            <div className="field" style={{ marginTop: 10 }}>
                                <div className="label">考试须知</div>
                                <textarea className="input" style={AreaStyle}
                                          value={form.notice}
                                          onChange={e => update({ notice: e.target.value })}/>
                            </div>
                        </div>

                        {/* 4 AI 使用策略 */}
                        <div className="form-section last">
                            <div className="section-head">
                                <span className="section-num">4</span>
                                <div>
                                    <div className="section-title">AI 使用策略</div>
                                    <div className="section-sub">决定考生可以使用 Coding Agent 的范围（Agent 服务下一迭代接入）</div>
                                </div>
                            </div>
                            <div className="radio-row">
                                {AiOptions.map(option => {
                                    const selected = form.aiMode === option.key;
                                    return (
                                        <div key={option.key}
                                             className={"radio-card" + (selected ? " selected" : "")}
                                             onClick={() => update({ aiMode: option.key })}>
                                            <div className="rc-head">
                                                <div className="rc-title">
                                                    <Icon name={option.icon} size={13}
                                                          stroke={selected ? "#1d4ed8" : "#64748b"}/>
                                                    {option.title}
                                                </div>
                                                <div className="radio-mark">
                                                    {selected && <span className="radio-dot"/>}
                                                </div>
                                            </div>
                                            <div className="rc-desc">{option.desc}</div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="create-side">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">发布前检查</div>
                            <span className={"badge " + (okCount === checks.length ? "green" : "amber")}>
                                {okCount} / {checks.length}
                            </span>
                        </div>
                        <div className="card-body">
                            {checks.map(check => (
                                <div className="check-line" key={check.text}>
                                <span className={check.ok ? "ok" : "warn"}>
                                    <Icon name={check.ok ? "check-circle" : "alert-triangle"} size={13}
                                          stroke={check.ok ? "#059669" : "#d97706"}/>
                                </span>
                                    {check.text}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="card tip-card">
                        <div className="tip-icon"><Icon name="sparkles" size={15}/></div>
                        <div>
                            <div className="tip-title">发布后可撤回</div>
                            <div className="tip-desc">
                                考试开始前仍可撤回并修改配置；开始后配置冻结。
                                在「考试管理」列表操作发布 / 撤回 / 归档。
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </TeacherLayout>
    );
}
