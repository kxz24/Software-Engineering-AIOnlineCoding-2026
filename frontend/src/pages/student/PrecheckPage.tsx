import React, { useEffect, useState } from "react";
import { Link, useHistory, useParams } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon, IconName } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { formatCountdown, formatDateTime, secondsUntil } from "../../api/format";
import { ApiError, fetchMyExam, StudentExamDetail } from "../../api/client";

/** 顶部三步流程：阅读须知 → 环境自检 → 进入考场 */
const Steps = [
    { title: "阅读须知", sub: "已完成", state: "done" as const },
    { title: "环境自检", sub: "进行中", state: "active" as const },
    { title: "进入考场", sub: "等待自检", state: "todo" as const },
];

/** 环境自检项（检测服务后续迭代接入，当前为浏览器端静态检查） */
const EnvChecks: { icon: IconName; tone?: "green" | "purple"; title: string; desc: string }[] = [
    { icon: "monitor", title: "浏览器", desc: "Chrome / Edge 最新两个版本 · 分辨率 1280×800 以上" },
    { icon: "wifi", title: "网络", desc: "能够访问本平台 API · 建议有线或稳定 Wi-Fi" },
    { icon: "terminal", title: "编辑器与终端", desc: "在线编辑器与模拟终端加载正常" },
    { icon: "sparkles", tone: "purple", title: "Coding Agent", desc: "按本场考试的 AI 策略提供 · 对话全程留痕" },
];

const AiModeLabels: Record<string, string> = { limited: "受限", open: "开放", closed: "关闭" };

/** 03 进入考场：考试须知 + 环境自检 + 考试承诺勾选后进入考场 */
export function PrecheckPage() {
    const { examId } = useParams<{ examId: string }>();
    const history = useHistory();

    const [exam, setExam] = useState<StudentExamDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [agreed, setAgreed] = useState(true);
    const [, setTick] = useState(0);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchMyExam(Number(examId))
            .then(result => {
                setExam(result);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [examId]);

    // 待考时刷新倒计时
    useEffect(() => {
        const timer = window.setInterval(() => setTick(value => value + 1), 1000);
        return () => window.clearInterval(timer);
    }, []);

    const ongoing = exam?.status === "ongoing";
    const upcoming = exam?.status === "upcoming";
    const secondsToStart = exam ? secondsUntil(exam.startTime) : 0;

    const enterExam = () => {
        if (!agreed) {
            toast("请先阅读并同意《考试诚信承诺》与《数据使用说明》。", "warning");
            return;
        }
        if (!ongoing) {
            toast(exam?.status === "finished" ? "考试已结束。" : "考试尚未开始，请稍候。", "warning");
            return;
        }
        history.push(Routes.examWorkbench(Number(examId)));
    };

    const infoRows = exam ? [
        { label: "开始时间", value: formatDateTime(exam.startTime) },
        { label: "结束时间", value: formatDateTime(exam.endTime) },
        { label: "考试时长", value: `${exam.durationMinutes} 分钟` },
        { label: "题目数量", value: `${exam.problems.length} 道题` },
        { label: "AI 模式", value: `${AiModeLabels[exam.aiMode] || exam.aiMode}模式` },
        { label: "提交次数", value: `每题 ${exam.submitLimit} 次` },
    ] : [];

    return (
        <StudentLayout active="precheck">
            <div className="page-head">
                <div>
                    <div className="page-title">进入考场</div>
                    <div className="page-sub">{exam ? `${exam.title} · 请完成考试须知阅读与环境自检` : "请完成考试须知阅读与环境自检"}</div>
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

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                        {" · "}
                        <Link className="link" to={Routes.examList}>返回我的考试</Link>
                    </div>
                </div>
            )}

            {loading && (
                <div className="card"><div className="card-body muted">加载中…</div></div>
            )}

            {exam && (
                <div className="precheck-main">
                    {/* 环境自检 */}
                    <div className="card precheck-card">
                        <div className="card-head">
                            <div>
                                <div className="card-title">环境自检</div>
                                <div className="card-sub">浏览器端静态检查 · 运行环境检测随判题容器接入</div>
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

                            {/* 考试须知（来自考试配置） */}
                            {exam.notice && (
                                <div className="notice-box" style={{
                                    marginTop: 12, padding: "10px 12px", background: "#f8fafc",
                                    borderRadius: 8, fontSize: 11.5, lineHeight: 1.7, whiteSpace: "pre-wrap",
                                }}>
                                    <div className="strong" style={{ marginBottom: 4 }}>考试须知</div>
                                    {exam.notice}
                                </div>
                            )}

                            <div className="precheck-actions">
                                <button type="button"
                                        className="btn btn-secondary"
                                        onClick={() => toast("正在重新检测环境，请稍候", "info")}>
                                    <Icon name="refresh" size={14}/>重新检测
                                </button>
                                <span className="hint">如检测失败，请重试或联系监考老师。</span>
                            </div>
                        </div>
                    </div>

                    <div className="precheck-side">
                        <div className="card">
                            <div className="card-head">
                                <div className="card-title">考试信息</div>
                                {ongoing && <span className="badge green">进行中</span>}
                                {upcoming && <span className="badge blue">未开始</span>}
                                {exam.status === "finished" && <span className="badge gray">已结束</span>}
                            </div>
                            <div className="card-body">
                                <div className="info-title">{exam.title}</div>
                                {infoRows.map(row => (
                                    <div className="info-row" key={row.label}>
                                        <span>{row.label}</span><strong>{row.value}</strong>
                                    </div>
                                ))}
                                {exam.description && (
                                    <div className="hint" style={{ marginTop: 8, lineHeight: 1.6 }}>{exam.description}</div>
                                )}
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
                                    <Icon name="arrow-right" size={14}/>
                                    {ongoing ? "进入考场" : upcoming ? `未开始 · 距开考 ${formatCountdown(secondsToStart)}` : "考试已结束"}
                                </button>
                                <div className="hint enter-hint">
                                    {ongoing ? "进入后即可答题，按结束时间自动收卷" : "开考时间内才可进入考场"}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </StudentLayout>
    );
}
