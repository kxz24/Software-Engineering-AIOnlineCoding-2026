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

/** 环境自检项：浏览器端的真实检测，desc 是未通过时的建议 */
interface EnvCheckDef {
    key: string;
    icon: IconName;
    tone?: "green" | "purple";
    title: string;
    desc: string;
    run: () => boolean;
}

const EnvCheckDefs: EnvCheckDef[] = [
    {
        key: "browser",
        icon: "monitor",
        title: "浏览器",
        desc: "建议使用 Chrome / Edge / Firefox 的较新版本",
        run: () => /Chrome|Edg|Firefox|Safari/.test(navigator.userAgent),
    },
    {
        key: "network",
        icon: "wifi",
        title: "网络连接",
        desc: "本机网络已断开，请检查连接后重试",
        run: () => navigator.onLine,
    },
    {
        key: "storage",
        icon: "terminal",
        title: "本地存储（代码草稿）",
        desc: "浏览器禁用了本地存储，代码草稿将无法自动保存",
        run: () => {
            try {
                localStorage.setItem("__precheck__", "1");
                localStorage.removeItem("__precheck__");
                return true;
            } catch (e) {
                return false;
            }
        },
    },
    {
        key: "viewport",
        icon: "sparkles",
        tone: "purple",
        title: "窗口尺寸",
        desc: "窗口过窄可能影响作答界面，建议全屏或使用大屏幕",
        run: () => window.innerWidth >= 1100,
    },
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

    // 环境自检：真实的浏览器端检测，可重复执行
    const [checkResults, setCheckResults] = useState<Record<string, boolean>>({});
    const [checking, setChecking] = useState(true);
    const [lastCheck, setLastCheck] = useState<string>("");

    const runChecks = () => {
        setChecking(true);
        window.setTimeout(() => {
            const results: Record<string, boolean> = {};
            EnvCheckDefs.forEach(item => {
                results[item.key] = item.run();
            });
            setCheckResults(results);
            setChecking(false);
            setLastCheck(new Date().toTimeString().slice(0, 8));
        }, 500);
    };

    useEffect(runChecks, []);

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
                                <div className="card-sub">
                                    浏览器端真实检测{lastCheck ? ` · 最近检测 ${lastCheck}` : ""}
                                    {" · 判题容器与 Agent 运行环境随评测服务接入"}
                                </div>
                            </div>
                            {checking
                                ? <span className="badge blue">检测中…</span>
                                : <span className={"badge " + (Object.values(checkResults).every(Boolean) ? "green" : "amber")}>
                                    {Object.values(checkResults).filter(Boolean).length} / {EnvCheckDefs.length} 通过
                                </span>}
                        </div>
                        <div className="card-body">
                            {EnvCheckDefs.map((item, index) => {
                                const passed = checkResults[item.key];
                                return (
                                    <div className={"check-item" + (index === EnvCheckDefs.length - 1 ? " last" : "")}
                                         key={item.key}>
                                        <div className={"ci-icon" + (item.tone ? " " + item.tone : "")}>
                                            <Icon name={item.icon} size={17}/>
                                        </div>
                                        <div className="ci-main">
                                            <div className="ci-title">{item.title}</div>
                                            <div className="ci-desc">
                                                {passed === false ? item.desc : "检测通过"}
                                            </div>
                                        </div>
                                        {checking
                                            ? <span className="badge gray">…</span>
                                            : <span className={"badge " + (passed ? "green" : "amber")}>
                                                {passed ? "通过" : "注意"}
                                            </span>}
                                    </div>
                                );
                            })}

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
                                        disabled={checking}
                                        onClick={runChecks}>
                                    <Icon name="refresh" size={14}/>重新检测
                                </button>
                                <span className="hint">自检不阻断进入考场；如有问题请重试或联系监考老师。</span>
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
