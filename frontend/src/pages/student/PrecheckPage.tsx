import React, { useState } from "react";
import { Link, useHistory, useParams } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon, IconName } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { AiModeLabels, findExam } from "../../mock/exams";

/** 顶部三步流程：阅读须知 → 环境自检 → 进入考场 */
interface Step {
    title: string;
    sub: string;
    /** done 显示对勾，active 高亮，todo 保持灰色 */
    state: "done" | "active" | "todo";
}

const Steps: Step[] = [
    { title: "阅读须知", sub: "已完成", state: "done" },
    { title: "环境自检", sub: "进行中", state: "active" },
    { title: "进入考场", sub: "等待自检", state: "todo" },
];

/** 环境自检项，tone 对应 ci-icon 的配色 */
interface EnvCheck {
    icon: IconName;
    tone?: "green" | "purple";
    title: string;
    desc: string;
}

const EnvChecks: EnvCheck[] = [
    { icon: "monitor", title: "浏览器", desc: "Chrome 128 · 分辨率 1440×900 · 支持最近两个版本" },
    { icon: "wifi", title: "网络", desc: "下行 86 Mbps / 上行 12 Mbps · 延迟 18 ms" },
    { icon: "cpu", tone: "green", title: "隔离容器", desc: "容器 c-7f3a 已就绪 · 2 vCPU / 4 GB · 初始仓库已挂载" },
    { icon: "terminal", title: "编辑器与终端", desc: "Monaco Editor、xterm.js 连接正常 · Python 3.11" },
    { icon: "sparkles", tone: "purple", title: "Coding Agent", desc: "受限模式 · 网关连接正常 · 对话将全程留痕" },
    { icon: "shield-check", title: "考试策略", desc: "网络隔离已开启 · 自动保存 30s · 提交次数 2 次" },
];

/** 03 进入考场：考试须知 + 环境自检 + 考试承诺勾选后进入考场 */
export function PrecheckPage() {
    const { examId } = useParams<{ examId: string }>();
    const history = useHistory();
    const exam = findExam(examId);

    // 原型默认已勾选；取消勾选后点击「进入考场」只给提示，不跳转
    const [agreed, setAgreed] = useState(true);

    // 考试信息面板：时间、时长、题量、AI 模式取考试数据，提交次数与成绩规则是本场策略
    const infoRows = [
        { label: "考试时间", value: exam.periodLabel },
        { label: "考试时长", value: `${exam.durationMinutes} 分钟` },
        { label: "题目数量", value: `${exam.problemCount} 道工程题` },
        { label: "AI 模式", value: `${AiModeLabels[exam.aiMode]}模式` },
        { label: "提交次数", value: "2 次" },
        { label: "成绩规则", value: "取最高分" },
    ];

    const enterExam = () => {
        if (!agreed) {
            toast("请先阅读并同意《考试诚信承诺》与《数据使用说明》。", "warning");
            return;
        }
        history.push(Routes.examWorkbench(exam.id));
    };

    return (
        <StudentLayout active="precheck">
            <div className="page-head">
                <div>
                    <div className="page-title">进入考场</div>
                    <div className="page-sub">{exam.title} · 请完成考试须知阅读与环境自检</div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-ghost" to={Routes.examList}>
                        <Icon name="arrow-left" size={14}/>返回我的考试
                    </Link>
                </div>
            </div>

            {/* 流程条 */}
            <div className="stepper">
                {Steps.map((step, index) => (
                    <React.Fragment key={step.title}>
                        <div className={"step" + (step.state === "todo" ? "" : " " + step.state)}>
                            <span className="step-num">
                                {step.state === "done"
                                    ? <Icon name="check" size={11} stroke="#ffffff" strokeWidth={3}/>
                                    : index + 1}
                            </span>
                            <div>
                                <div className="step-title">{step.title}</div>
                                <div className="step-sub">{step.sub}</div>
                            </div>
                        </div>
                        {index < Steps.length - 1 && <div className="step-line"/>}
                    </React.Fragment>
                ))}
            </div>

            <div className="precheck-main">
                {/* 环境自检 */}
                <div className="card precheck-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">环境自检</div>
                            <div className="card-sub">最近检测 14:02:18 · 全部项目通过</div>
                        </div>
                        <span className="badge green">{EnvChecks.length} / {EnvChecks.length} 通过</span>
                    </div>
                    <div className="card-body">
                        {EnvChecks.map((item, index) => (
                            <div className={"check-item" + (index === EnvChecks.length - 1 ? " last" : "")}
                                 key={item.title}>
                                <div className={"ci-icon" + (item.tone ? " " + item.tone : "")}>
                                    <Icon name={item.icon} size={17}/>
                                </div>
                                <div className="ci-main">
                                    <div className="ci-title">{item.title}</div>
                                    <div className="ci-desc">{item.desc}</div>
                                </div>
                                <span className="badge green">通过</span>
                            </div>
                        ))}
                        <div className="precheck-actions">
                            <button type="button"
                                    className="btn btn-secondary"
                                    onClick={() => toast("正在重新检测环境，请稍候", "info")}>
                                <Icon name="refresh" size={14}/>重新检测
                            </button>
                            <span className="hint">检测不会修改你的代码；如失败，请重试或联系监考。</span>
                        </div>
                    </div>
                </div>

                <div className="precheck-side">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">考试信息</div>
                        </div>
                        <div className="card-body">
                            <div className="info-title">{exam.title}</div>
                            {infoRows.map(row => (
                                <div className="info-row" key={row.label}>
                                    <span>{row.label}</span><strong>{row.value}</strong>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 考试承诺：勾选状态为本页本地状态 */}
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">考试承诺</div>
                        </div>
                        <div className="card-body">
                            <div className="check-row">
                                <span className={"check-box" + (agreed ? " checked" : "")}
                                      role="checkbox"
                                      aria-checked={agreed}
                                      tabIndex={0}
                                      onClick={() => setAgreed(value => !value)}
                                      onKeyDown={event => {
                                          if (event.key === "Enter" || event.key === " ") {
                                              event.preventDefault();
                                              setAgreed(value => !value);
                                          }
                                      }}>
                                    {agreed && <Icon name="check" size={9} stroke="#ffffff" strokeWidth={3}/>}
                                </span>
                                <span>我已阅读并同意《考试诚信承诺》与《数据使用说明》。</span>
                            </div>
                            <div className="privacy-note">
                                <Icon name="shield-check" size={13}/>本场考试不录屏、不采集摄像头；仅记录平台内操作与 AI 对话。
                            </div>
                            <button type="button" className="btn btn-primary btn-block" onClick={enterExam}>
                                <Icon name="arrow-right" size={14}/>进入考场
                            </button>
                            <div className="hint enter-hint">进入后计时立即开始</div>
                        </div>
                    </div>
                </div>
            </div>
        </StudentLayout>
    );
}
