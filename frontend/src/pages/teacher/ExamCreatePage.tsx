import React, { useState } from "react";
import { useHistory } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon, IconName } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { AiMode } from "../../mock/exams";

/** 表单字段：除 AI 策略外都是字符串，方便统一做受控更新 */
interface ExamForm {
    title: string;
    course: string;
    startTime: string;
    endTime: string;
    duration: string;
    passScore: string;
    submitLimit: string;
    scoreRule: string;
    lateRule: string;
    submitRule: string;
    cpu: string;
    memory: string;
    network: string;
    image: string;
    aiMode: AiMode;
}

type FormKey = Exclude<keyof ExamForm, "aiMode">;

const InitialForm: ExamForm = {
    title: "软件工程 · 期末机考",
    course: "软件工程（2026 秋）",
    startTime: "2026-11-08 09:00",
    endTime: "2026-11-08 11:00",
    duration: "120 分钟",
    passScore: "60 分",
    submitLimit: "2 次",
    scoreRule: "取最高分",
    lateRule: "开考 15 分钟后禁止入场",
    submitRule: "时间到自动交卷",
    cpu: "2 vCPU",
    memory: "4 GB",
    network: "仅平台网关",
    image: "se-2026-python",
    aiMode: "limited",
};

interface FieldConfig {
    key: FormKey;
    label: string;
    /** 文本框左侧图标，开始 / 结束时间使用日历 */
    icon?: IconName;
    /** 有选项时渲染为下拉框 */
    options?: string[];
    /** 资源区四个字段的下拉箭头略小 */
    chevronSize?: number;
    required?: boolean;
}

interface RowConfig {
    layout: "two" | "four";
    fields: FieldConfig[];
}

interface SectionConfig {
    num: number;
    title: string;
    sub: string;
    rows: RowConfig[];
    /** 第 3 段单独渲染 AI 策略卡片 */
    aiPolicy?: boolean;
    last?: boolean;
}

const FormSections: SectionConfig[] = [
    {
        num: 1,
        title: "基本信息",
        sub: "考试名称、课程与时间安排",
        rows: [
            {
                layout: "two",
                fields: [
                    { key: "title", label: "考试名称", required: true },
                    {
                        key: "course",
                        label: "课程",
                        options: ["软件工程（2026 秋）", "数据结构（2026 秋）", "算法设计（2026 秋）"],
                    },
                ],
            },
            {
                layout: "two",
                fields: [
                    { key: "startTime", label: "开始时间", icon: "calendar", required: true },
                    { key: "endTime", label: "结束时间", icon: "calendar", required: true },
                ],
            },
            {
                layout: "two",
                fields: [
                    { key: "duration", label: "考试时长", required: true },
                    { key: "passScore", label: "及格线", required: true },
                ],
            },
        ],
    },
    {
        num: 2,
        title: "考试规则",
        sub: "提交次数与成绩计算",
        rows: [
            {
                layout: "two",
                fields: [
                    { key: "submitLimit", label: "提交次数上限", required: true },
                    { key: "scoreRule", label: "成绩计算", options: ["取最高分", "取最后一次", "取平均分"] },
                ],
            },
            {
                layout: "two",
                fields: [
                    {
                        key: "lateRule",
                        label: "迟到入场",
                        options: ["开考 15 分钟后禁止入场", "开考 30 分钟后禁止入场", "允许迟到入场"],
                    },
                    {
                        key: "submitRule",
                        label: "交卷规则",
                        options: ["时间到自动交卷", "时间到后 5 分钟内自动交卷", "仅手动交卷"],
                    },
                ],
            },
        ],
    },
    {
        num: 3,
        title: "AI 使用策略",
        sub: "决定考生可以使用 Coding Agent 的范围",
        rows: [],
        aiPolicy: true,
    },
    {
        num: 4,
        title: "资源与网络",
        sub: "每位考生独立容器",
        last: true,
        rows: [
            {
                layout: "four",
                fields: [
                    { key: "cpu", label: "CPU", required: true },
                    { key: "memory", label: "内存", required: true },
                    {
                        key: "network",
                        label: "网络",
                        options: ["仅平台网关", "平台网关 + 镜像源", "完全离线"],
                        chevronSize: 12,
                    },
                    {
                        key: "image",
                        label: "镜像",
                        options: ["se-2026-python", "se-2026-java", "se-2026-node"],
                        chevronSize: 12,
                    },
                ],
            },
        ],
    },
];

/** 让原生输入框 / 下拉框贴合原型里的 .input / .select 外观（不改全局 CSS） */
const BareControlStyle: React.CSSProperties = {
    flex: 1,
    minWidth: 0,
    height: "100%",
    padding: 0,
    border: "none",
    outline: "none",
    background: "transparent",
    color: "inherit",
    font: "inherit",
    appearance: "none",
};

interface AiOption {
    key: AiMode;
    title: string;
    desc: string;
    icon: IconName;
}

const AiOptions: AiOption[] = [
    { key: "open", title: "开放", desc: "完整对话与代码修改，全部留痕。", icon: "unlock" },
    { key: "limited", title: "受限", desc: "仅解释与运行测试，不可直接写入代码。", icon: "shield-check" },
    { key: "closed", title: "关闭", desc: "禁用 Agent，入口不可用。", icon: "lock" },
];

const PublishChecks: { kind: "ok" | "warn"; text: string }[] = [
    { kind: "ok", text: "考试时间已设置" },
    { kind: "ok", text: "考生名单已导入（45 人）" },
    { kind: "ok", text: "镜像可用" },
    { kind: "warn", text: "题目与测试待配置（0 / 3）" },
    { kind: "ok", text: "AI 策略已选择（受限）" },
];

const ResourceRows = [
    { label: "考生人数", value: "45 人" },
    { label: "容器数量", value: "45 个" },
    { label: "CPU", value: "90 vCPU" },
    { label: "内存", value: "180 GB" },
];

/** 找到第一个未填写的必填字段，用于提交前校验 */
function findMissingField(form: ExamForm): FieldConfig | undefined {
    for (const section of FormSections) {
        for (const row of section.rows) {
            for (const field of row.fields) {
                if (field.required && !form[field.key].trim()) {
                    return field;
                }
            }
        }
    }
    return undefined;
}

interface FormFieldProps {
    config: FieldConfig;
    value: string;
    onChange: (key: FormKey, value: string) => void;
}

/** 单个表单项：文本框与下拉框共用同一套 .field / .label 结构 */
function FormField({ config, value, onChange }: FormFieldProps) {
    return (
        <div className="field">
            <div className="label">{config.label}</div>
            {config.options
                ? (
                    <div className="select">
                        <select style={BareControlStyle}
                                value={value}
                                onChange={event => onChange(config.key, event.target.value)}>
                            {config.options.map(option => (
                                <option key={option} value={option}>{option}</option>
                            ))}
                        </select>
                        <Icon name="chevron-down" size={config.chevronSize || 13} stroke="#94a3b8"/>
                    </div>
                )
                : (
                    <div className="input">
                        {config.icon && <Icon name={config.icon} size={13} stroke="#94a3b8"/>}
                        <input style={BareControlStyle}
                               value={value}
                               onChange={event => onChange(config.key, event.target.value)}/>
                    </div>
                )}
        </div>
    );
}

/** 08 创建考试：考试信息、规则、AI 策略与资源网络配置 */
export function ExamCreatePage() {
    const [form, setForm] = useState<ExamForm>(InitialForm);
    const history = useHistory();

    const updateField = (key: FormKey, value: string) => {
        setForm(current => ({ ...current, [key]: value }));
    };

    const handleSaveDraft = () => {
        toast("草稿已保存");
        history.push(Routes.examManage);
    };

    // 必填校验通过后进入题目配置；原型固定指向期中机考的命题页
    const handleNext = () => {
        const missing = findMissingField(form);
        if (missing) {
            toast("请填写" + missing.label, "warning");
            return;
        }
        history.push(Routes.problemConfig("exam-mid-2026"));
    };

    return (
        <TeacherLayout breadcrumb={["工作台", "软件工程 · 2026 秋", "创建考试"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">创建考试</div>
                    <div className="page-sub">配置考试时间、规则与 AI 使用策略</div>
                </div>
                <div className="page-actions">
                    <button type="button" className="btn btn-secondary" onClick={handleSaveDraft}>
                        保存草稿
                    </button>
                    <button type="button" className="btn btn-primary" onClick={handleNext}>
                        下一步：命题<Icon name="arrow-right" size={14}/>
                    </button>
                </div>
            </div>

            <div className="create-main">
                <div className="card create-form">
                    <div className="card-body">
                        {FormSections.map(section => (
                            <div key={section.num}
                                 className={"form-section" + (section.last ? " last" : "")}>
                                <div className="section-head">
                                    <span className="section-num">{section.num}</span>
                                    <div>
                                        <div className="section-title">{section.title}</div>
                                        <div className="section-sub">{section.sub}</div>
                                    </div>
                                </div>

                                {section.rows.map((row, rowIndex) => (
                                    <div className={"form-grid " + row.layout} key={rowIndex}>
                                        {row.fields.map(field => (
                                            <FormField key={field.key}
                                                       config={field}
                                                       value={form[field.key]}
                                                       onChange={updateField}/>
                                        ))}
                                    </div>
                                ))}

                                {section.aiPolicy && (
                                    <div className="radio-row">
                                        {AiOptions.map(option => {
                                            const selected = form.aiMode === option.key;
                                            return (
                                                <div key={option.key}
                                                     className={"radio-card" + (selected ? " selected" : "")}
                                                     onClick={() => setForm(current => ({
                                                         ...current,
                                                         aiMode: option.key,
                                                     }))}>
                                                    <div className="rc-head">
                                                        <div className="rc-title">
                                                            <Icon name={option.icon}
                                                                  size={13}
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
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="create-side">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">发布前检查</div>
                            <span className="badge amber">4 / 5</span>
                        </div>
                        <div className="card-body">
                            {PublishChecks.map(check => (
                                <div className="check-line" key={check.text}>
                                    <span className={check.kind === "ok" ? "ok" : "warn"}>
                                        <Icon name={check.kind === "ok" ? "check-circle" : "alert-triangle"}
                                              size={13}
                                              stroke={check.kind === "ok" ? "#059669" : "#d97706"}/>
                                    </span>
                                    {check.text}
                                </div>
                            ))}
                            <div className="check-progress">
                                <div className="bar"><span className="bar-fill amber w-80"/></div>
                                <span>4 / 5 完成</span>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">资源预估</div>
                        </div>
                        <div className="card-body">
                            {ResourceRows.map((row, index) => (
                                <div key={row.label}
                                     className={"res-row" + (index === ResourceRows.length - 1 ? " last" : "")}>
                                    <span>{row.label}</span><strong>{row.value}</strong>
                                </div>
                            ))}
                            <div className="res-note">按每位考生 2 vCPU / 4 GB 估算，考试期间按需启动。</div>
                        </div>
                    </div>

                    <div className="card tip-card">
                        <div className="tip-icon"><Icon name="sparkles" size={15}/></div>
                        <div>
                            <div className="tip-title">发布后可撤回</div>
                            <div className="tip-desc">考试开始前仍可撤回并修改配置；开始后配置冻结。</div>
                        </div>
                    </div>
                </div>
            </div>
        </TeacherLayout>
    );
}
