import React, { useState } from "react";
import { useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Store } from "../../store";
import { findExam } from "../../mock/exams";

/** 报告页签，原型中仅「总览」有内容 */
const ReportTabs = ["总览", "时间线", "AI 对话（6）", "代码变更", "评分明细"];

/** 申诉可选范围，对应总分与三个评分维度 */
const AppealScopes = ["总分", "代码与测试", "AI 协作", "教师复核"];

interface ScoreDimension {
    label: string;
    /** 得分，教师复核未评时显示「待评」 */
    value: string;
    /** 满分 */
    total: string;
    /** 得分进度条的类名，沿用原型的 bar-fill 配色与宽度 */
    fill: string;
    /** 未评分的维度用琥珀色数字强调 */
    amber?: boolean;
}

const ScoreDimensions: ScoreDimension[] = [
    { label: "代码与测试", value: "66", total: "70", fill: "bar-fill green w-94" },
    { label: "AI 协作", value: "16", total: "20", fill: "bar-fill purple w-80" },
    { label: "教师复核", value: "待评", total: "10", fill: "bar-fill amber w-0", amber: true },
];

interface TimelineEvent {
    time: string;
    title: string;
    desc: string;
    /** 圆点配色，沿用原型的 tl-dot 修饰类 */
    dot: "green" | "blue" | "amber" | "purple";
}

const TimelineEvents: TimelineEvent[] = [
    { time: "13:55", title: "进入考场 · 容器就绪", desc: "环境自检通过，初始仓库已挂载", dot: "green" },
    { time: "14:02", title: "阅读题目与 README", desc: "打开 src/buggy_sort.py，标记 2 处可疑逻辑", dot: "blue" },
    { time: "14:08", title: "运行样例测试 · 6 / 10 通过", desc: "终端执行 pytest，记录 4 个失败用例", dot: "amber" },
    { time: "14:15", title: "调用 Coding Agent · 2 轮", desc: "引用 src/buggy_sort.py，询问并列排序问题", dot: "purple" },
    { time: "14:22", title: "采纳建议 · 修改排序键", desc: "将 amount 改为 (amount, parse_time(created_at))", dot: "blue" },
    { time: "14:28", title: "运行样例测试 · 8 / 10 通过", desc: "2 个时间格式用例仍失败", dot: "green" },
    { time: "14:36", title: "第 1 次提交 · 64 分", desc: "冻结代码与过程记录，运行隐藏测试", dot: "amber" },
    { time: "14:58", title: "第 2 次提交 · 82 分", desc: "当前最高分；过程分待教师复核", dot: "green" },
];

interface RubricItem {
    label: string;
    score: string;
    evidence: string;
}

const RubricItems: RubricItem[] = [
    { label: "问题拆解", score: "4 / 5", evidence: "证据：3 次任务拆解、2 次追问" },
    { label: "上下文质量", score: "4 / 5", evidence: "证据：@ 引用 2 个文件，未粘贴无关代码" },
    { label: "验证行为", score: "4 / 5", evidence: "证据：4 次测试运行，2 次失败后定位修正" },
    { label: "批判性采纳", score: "4 / 5", evidence: "证据：采纳 2 次，修改 1 次，拒绝 0 次" },
];

const KeyStats: { label: string; value: string }[] = [
    { label: "AI 对话", value: "6 轮" },
    { label: "采纳建议", value: "2 次" },
    { label: "测试运行", value: "4 次" },
    { label: "代码快照", value: "18 个" },
    { label: "代码变更", value: "+18 / -7" },
    { label: "粘贴事件", value: "0 次" },
];

/** 06 成绩报告：过程时间线、AI 协作评分与申诉入口 */
export function ReportPage() {
    const { examId } = useParams<{ examId: string }>();
    const exam = findExam(examId);
    const user = useSelector((s: Store) => s.user);
    const [appealOpen, setAppealOpen] = useState(false);
    const [appealScope, setAppealScope] = useState(AppealScopes[0]);
    const [appealDetail, setAppealDetail] = useState("");

    // 报告属于某位考生，姓名与学号取自当前登录用户，未取到时退回原型的示例值
    const studentName = user?.nickname || "李同学";
    const studentNo = user?.username || "2023012345";

    const closeAppeal = () => setAppealOpen(false);

    // 提交申诉：仅做前端反馈，关闭弹窗并清空说明
    const submitAppeal = () => {
        setAppealOpen(false);
        setAppealDetail("");
        toast("申诉已提交");
    };

    return (
        <StudentLayout active="reports">
            <div className="page-head">
                <div>
                    <div className="page-title">过程报告</div>
                    <div className="page-sub">{exam.title} · {studentName} · 学号 {studentNo}</div>
                </div>
                <div className="page-actions">
                    <span className="btn btn-secondary" onClick={() => toast("报告已导出为 PDF")}>
                        <Icon name="download" size={14}/>导出 PDF
                    </span>
                    <span className="btn btn-primary" onClick={() => setAppealOpen(true)}>
                        <Icon name="flag" size={14}/>发起申诉
                    </span>
                </div>
            </div>

            {/* 页签：原型中仅「总览」有内容，其余为占位 */}
            <div className="report-tabs">
                {ReportTabs.map((tab, index) => (
                    <span key={tab} className={"tab" + (index === 0 ? " active" : "")}>{tab}</span>
                ))}
            </div>

            {/* 总分与三个评分维度 */}
            <div className="report-summary">
                <div className="rs-score">
                    <div className="rs-label">当前总分</div>
                    <div className="rs-value">82<span> / 100</span></div>
                    <div className="rs-note">过程分待教师确认</div>
                </div>
                {ScoreDimensions.map(item => (
                    <div className="rs-item" key={item.label}>
                        <div className="rs-item-label">{item.label}</div>
                        <div className={"rs-item-value" + (item.amber ? " amber" : "")}>
                            {item.value}<span> / {item.total}</span>
                        </div>
                        <div className="bar"><span className={item.fill}/></div>
                    </div>
                ))}
            </div>

            <div className="report-main">
                <div className="card report-timeline-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">考试时间线</div>
                            <div className="card-sub">代码、测试、AI 对话与提交的关键事件</div>
                        </div>
                        <span className="badge gray">18 个快照</span>
                    </div>
                    <div className="card-body">
                        {TimelineEvents.map(event => (
                            <div className="tl-item" key={event.time + event.title}>
                                <div className="tl-rail">
                                    <span className={"tl-dot " + event.dot}/>
                                    <span className="tl-line"/>
                                </div>
                                <div className="tl-time">{event.time}</div>
                                <div className="tl-content">
                                    <div className="tl-title">{event.title}</div>
                                    <div className="tl-desc">{event.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="report-side">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">AI 协作评分</div>
                            <span className="badge purple">16 / 20</span>
                        </div>
                        <div className="card-body">
                            {RubricItems.map((item, index) => (
                                <div key={item.label}
                                     className={"rubric-item" + (index === RubricItems.length - 1 ? " last" : "")}>
                                    <div className="rubric-row"><span>{item.label}</span><strong>{item.score}</strong></div>
                                    <div className="bar"><span className="bar-fill purple w-80"/></div>
                                    <div className="rubric-ev">{item.evidence}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">关键统计</div>
                            <span className="link" onClick={() => toast("统计明细尚未接入")}>查看明细</span>
                        </div>
                        <div className="card-body stats-mini">
                            {KeyStats.map(stat => (
                                <div key={stat.label}>
                                    <span>{stat.label}</span><strong>{stat.value}</strong>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* 申诉弹窗：遮罩与卡片定位用内联样式，内部沿用原型的卡片与表单类名 */}
            {appealOpen && (
                <div
                    style={{
                        position: "fixed",
                        top: 0,
                        right: 0,
                        bottom: 0,
                        left: 0,
                        background: "rgba(15,23,42,.45)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        zIndex: 200,
                    }}
                    onClick={closeAppeal}>
                    <div className="card fade-in"
                         style={{ width: 420 }}
                         onClick={event => event.stopPropagation()}>
                        <div className="card-head">
                            <div>
                                <div className="card-title">发起申诉</div>
                                <div className="card-sub">成绩发布后 48 小时内可发起申诉，逾期不再受理</div>
                            </div>
                        </div>
                        <div className="card-body">
                            <div className="field" style={{ marginBottom: 12 }}>
                                <div className="label">申诉范围</div>
                                <select className="select"
                                        value={appealScope}
                                        onChange={event => setAppealScope(event.target.value)}>
                                    {AppealScopes.map(scope => (
                                        <option key={scope} value={scope}>{scope}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field">
                                <div className="label">申诉说明</div>
                                <textarea className="input"
                                          style={{ height: 76, padding: "8px 10px", resize: "none" }}
                                          placeholder="请说明判分异议与依据"
                                          value={appealDetail}
                                          onChange={event => setAppealDetail(event.target.value)}/>
                                <div className="hint">提交后由教师复核，复核结果将在 3 个工作日内反馈。</div>
                            </div>
                            <div style={{ display: "flex", justifyContent: "flex-end", gap: 9, marginTop: 16 }}>
                                <span className="btn btn-secondary" onClick={closeAppeal}>取消</span>
                                <span className="btn btn-primary" onClick={submitAppeal}>提交申诉</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </StudentLayout>
    );
}
