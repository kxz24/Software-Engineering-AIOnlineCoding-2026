import React from "react";
import { Link, useParams } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { findExam } from "../../mock/exams";

/** 本次提交的总分（演示数据） */
const CurrentScore = 82;

/** 用例总数：表格只展示前 9 条，隐藏用例仅给汇总 */
const CaseTotal = 20;

/** 顶部四项指标 */
interface Metric {
    value: string;
    label: string;
    tone?: "green" | "amber";
}

const Metrics: Metric[] = [
    { value: "10/10", label: "样例测试", tone: "green" },
    { value: "8/10", label: "隐藏测试" },
    { value: "良好", label: "代码质量" },
    { value: "待评", label: "AI 协作过程", tone: "amber" },
];

/** 用例结果：隐藏用例不展示输入与预期输出 */
interface CaseResult {
    name: string;
    type: "样例" | "隐藏";
    passed: boolean;
    duration: string;
    memory: string;
}

const CaseResults: CaseResult[] = [
    { name: "test_sort_basic", type: "样例", passed: true, duration: "0.12s", memory: "12 MB" },
    { name: "test_sort_ties", type: "样例", passed: true, duration: "0.10s", memory: "11 MB" },
    { name: "test_sort_iso_format", type: "样例", passed: true, duration: "0.11s", memory: "12 MB" },
    { name: "test_sort_empty", type: "样例", passed: true, duration: "0.08s", memory: "10 MB" },
    { name: "test_sort_single", type: "样例", passed: true, duration: "0.07s", memory: "10 MB" },
    { name: "隐藏用例 #07", type: "隐藏", passed: true, duration: "0.18s", memory: "16 MB" },
    { name: "隐藏用例 #08", type: "隐藏", passed: false, duration: "0.20s", memory: "18 MB" },
    { name: "隐藏用例 #09", type: "隐藏", passed: true, duration: "0.17s", memory: "15 MB" },
    { name: "隐藏用例 #10", type: "隐藏", passed: false, duration: "0.19s", memory: "17 MB" },
];

/** 提交记录：best 标记当前最高分 */
interface SubmitRecord {
    title: string;
    time: string;
    best: boolean;
}

const SubmitRecords: SubmitRecord[] = [
    { title: `第 2 次 · ${CurrentScore} 分`, time: "14:58:32 · 当前最高分", best: true },
    { title: "第 1 次 · 64 分", time: "14:36:10", best: false },
];

/** 评分说明 */
const ScoreRules = [
    { label: "测试用例", weight: "70%" },
    { label: "AI 协作过程", weight: "20%" },
    { label: "教师复核", weight: "10%" },
];

/** 05 提交结果：本次得分、用例结果与提交记录 */
export function ResultPage() {
    const { examId } = useParams<{ examId: string }>();
    const exam = findExam(examId);

    const failedCount = CaseResults.filter(item => !item.passed).length;

    return (
        <StudentLayout active="reports">
            <div className="page-head">
                <div>
                    <div className="page-title">提交结果</div>
                    <div className="page-sub">{exam.title} · 第 2 次提交 · 14:58:32</div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-secondary" to={Routes.examWorkbench(exam.id)}>
                        <Icon name="arrow-left" size={14}/>返回工作台
                    </Link>
                    <Link className="btn btn-primary" to={Routes.examReport(exam.id)}>
                        <Icon name="file-text" size={14}/>查看过程报告
                    </Link>
                </div>
            </div>

            {/* 分数概览 */}
            <div className="result-summary">
                <div className="score-block">
                    <div className="score-label">当前总分</div>
                    <div className="score-value">{CurrentScore}<span> / 100</span></div>
                    <div className="score-status">
                        <span className="badge green">已提交</span>
                        <span className="badge amber">过程分待复核</span>
                    </div>
                    <div className="score-bar"><span className="score-fill"/></div>
                    <div className="score-note">成绩规则：取最高分 · 当前为第 2 次提交（最高分）</div>
                </div>
                <div className="score-metrics">
                    {Metrics.map((metric, index) => (
                        <div className={"metric" + (index === 0 ? " first" : "")} key={metric.label}>
                            <div className={"metric-value" + (metric.tone ? " " + metric.tone : "")}>
                                {metric.value}
                            </div>
                            <div className="metric-label">{metric.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="result-main">
                <div className="card result-table-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">用例结果</div>
                            <div className="card-sub">隐藏用例仅显示汇总结果，不展示输入与预期输出</div>
                        </div>
                        <span className="badge gray">共 {CaseTotal} 个用例</span>
                    </div>
                    <table className="table">
                        <thead>
                        <tr>
                            <th>用例</th>
                            <th>类型</th>
                            <th>结果</th>
                            <th>耗时</th>
                            <th>内存</th>
                        </tr>
                        </thead>
                        <tbody>
                        {CaseResults.map(item => (
                            <tr key={item.name}>
                                <td>{item.name}</td>
                                <td>{item.type}</td>
                                <td>
                                    <span className={"badge " + (item.passed ? "green" : "red")}>
                                        {item.passed ? "通过" : "失败"}
                                    </span>
                                </td>
                                <td>{item.duration}</td>
                                <td>{item.memory}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    <div className="table-foot">
                        <Icon name="alert-triangle" size={12}/>
                        {failedCount} 个隐藏用例未通过：边界条件与异常输入。可返回工作台继续修改。
                    </div>
                </div>

                <div className="result-side">
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">提交记录</div>
                            <span className="badge blue">剩余 1 次</span>
                        </div>
                        <div className="card-body">
                            {SubmitRecords.map((record, index) => (
                                <div className={"submit-item" + (index === SubmitRecords.length - 1 ? " last" : "")}
                                     key={record.title}>
                                    <div className={"submit-dot" + (record.best ? "" : " gray")}/>
                                    <div>
                                        <div className="submit-title">{record.title}</div>
                                        <div className="submit-time">{record.time}</div>
                                    </div>
                                    {record.best && <span className="badge green">最高</span>}
                                </div>
                            ))}
                            <div className="submit-rule">
                                <Icon name="clock" size={11}/>
                                成绩取最高分；提交次数用尽后仍可查看结果。
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">下一步</div>
                        </div>
                        <div className="card-body">
                            <Link className="btn btn-primary btn-block" to={Routes.examWorkbench(exam.id)}>
                                继续修改并提交
                            </Link>
                            <div className="gap-8"/>
                            <Link className="btn btn-secondary btn-block" to={Routes.examReport(exam.id)}>
                                查看完整过程报告
                            </Link>
                            <div className="appeal-note">对判分有异议？可在考试结束后 48 小时内发起申诉。</div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">评分说明</div>
                        </div>
                        <div className="card-body">
                            {ScoreRules.map((rule, index) => (
                                <div className={"score-rule" + (index === ScoreRules.length - 1 ? " last" : "")}
                                     key={rule.label}>
                                    <span>{rule.label}</span><strong>{rule.weight}</strong>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </StudentLayout>
    );
}
