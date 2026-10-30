import React, { useEffect, useState } from "react";
import { useHistory, useParams } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import { findProblemSet, ScoreWeights } from "../../mock/problems";

/** 评分规则三项，与原型「评分规则」卡片一一对应 */
const WeightRows: { key: keyof ScoreWeights; label: string; barClass: string }[] = [
    { key: "mustPass", label: "必过用例", barClass: "bar-fill" },
    { key: "bonus", label: "加分用例", barClass: "bar-fill green" },
    { key: "quality", label: "代码质量", barClass: "bar-fill amber" },
];

/** 权重输入：沿用 .input 外观，压成行内小尺寸 */
const WeightInputStyle: React.CSSProperties = {
    width: 46,
    height: 22,
    padding: "0 6px",
    fontSize: 10,
    textAlign: "right",
};

/** 总分输入：藏在 .badge 里，视觉上仍是「总分 100」 */
const ScoreInputStyle: React.CSSProperties = {
    width: 30,
    height: 16,
    padding: 0,
    border: "none",
    outline: "none",
    background: "transparent",
    color: "inherit",
    fontFamily: "inherit",
    fontSize: 10,
    fontWeight: 600,
    textAlign: "right",
};

/** 把输入框里的字符串收敛成 0–100 的整数，避免受控输入出现 NaN */
function toNumber(raw: string): number {
    const parsed = Number.parseInt(raw, 10);
    if (Number.isNaN(parsed)) {
        return 0;
    }
    return Math.min(100, Math.max(0, parsed));
}

/**
 * 09 命题与评测配置：单个任务的用例、评分规则与运行限制。
 *
 * 题目切换、权重与分值都是本地状态，保存时只做轻提示并返回考试管理，
 * 等题目配置接口就绪后把 handleSave 换成真实请求即可。
 */
export function ProblemConfigPage() {
    const { examId } = useParams<{ examId: string }>();
    const history = useHistory();
    const problemSet = findProblemSet(examId);

    const [selectedId, setSelectedId] = useState(problemSet.problems[0].id);
    const selectedIndex = Math.max(0, problemSet.problems.findIndex(item => item.id === selectedId));
    const problem = problemSet.problems[selectedIndex];

    const [weights, setWeights] = useState<ScoreWeights>(problem.weights);
    const [totalScore, setTotalScore] = useState(problem.totalScore);

    // 切换题目时把权重与分值恢复成该题目的默认配置
    useEffect(() => {
        setWeights(problem.weights);
        setTotalScore(problem.totalScore);
    }, [problem]);

    const updateWeight = (key: keyof ScoreWeights, raw: string) => {
        setWeights(current => ({ ...current, [key]: toNumber(raw) }));
    };

    const handleSave = () => {
        toast("题目配置已保存");
        history.push(Routes.examManage);
    };

    const limitRows = [
        { label: "单用例超时", value: problem.limits.timeout },
        { label: "内存上限", value: problem.limits.memory },
        { label: "判题语言", value: problem.limits.language },
        { label: "AI 策略", value: problem.limits.aiPolicy },
    ];

    return (
        <TeacherLayout breadcrumb={["工作台", "软件工程 · 2026 秋", "考试管理", "题目配置"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">命题与评测配置</div>
                    <div className="page-sub">
                        {problemSet.examTitle} · 任务 {selectedIndex + 1} / {problemSet.problems.length}
                    </div>
                </div>
                <div className="page-actions">
                    <button type="button" className="btn btn-ghost" onClick={() => history.push(Routes.examManage)}>
                        <Icon name="arrow-left" size={14}/>返回
                    </button>
                    <button type="button" className="btn btn-secondary">
                        <Icon name="eye" size={14}/>预览题面
                    </button>
                    <button type="button" className="btn btn-primary" onClick={handleSave}>
                        <Icon name="check" size={14}/>保存任务
                    </button>
                </div>
            </div>

            {/* 当前题目的概要：题型、语言、题面状态与附件 */}
            <div className="card problem-summary">
                <div className="ps-main">
                    <div className="ps-icon"><Icon name="file-text" size={19}/></div>
                    <div>
                        <div className="ps-title">{problem.title}</div>
                        <div className="ps-meta">
                            <span className="badge blue">{problem.kindLabel}</span>
                            <span className="badge gray">{problem.language}</span>
                            <span className="badge green">{problem.statementStatus}</span>
                            <span className="ps-file">
                                <Icon name="file" size={11}/>{problem.packageFile}
                            </span>
                        </div>
                    </div>
                </div>
                <div className="row" style={{ gap: 10 }}>
                    {/* 题目列表：点击切换当前配置 */}
                    <div className="tabs-inline">
                        {problemSet.problems.map((item, index) => (
                            <span key={item.id}
                                  title={item.title}
                                  className={"tab-pill" + (item.id === selectedId ? " active" : "")}
                                  onClick={() => setSelectedId(item.id)}>
                                任务 {index + 1}
                            </span>
                        ))}
                    </div>
                    <span className="btn btn-ghost btn-sm">编辑题面</span>
                </div>
            </div>

            <div className="problem-main">
                <div className="card test-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">测试用例</div>
                            <div className="card-sub">样例测试对考生可见；隐藏测试仅用于判分</div>
                        </div>
                        <div className="table-tools">
                            <span className="btn btn-secondary btn-sm">
                                <Icon name="plus" size={12}/>上传用例
                            </span>
                            <span className="btn btn-secondary btn-sm">
                                <Icon name="play" size={12}/>运行全部
                            </span>
                        </div>
                    </div>
                    <div className="test-tabs">
                        <span className="tab active">
                            样例测试 <span className="tab-count">{problem.sampleCount}</span>
                        </span>
                        <span className="tab">
                            隐藏测试 <span className="tab-count">{problem.hiddenCount}</span>
                        </span>
                    </div>
                    <table className="table">
                        <thead>
                        <tr>
                            <th>编号</th>
                            <th>名称</th>
                            <th>类型</th>
                            <th>状态</th>
                            <th>耗时</th>
                            <th>内存</th>
                            <th>可见性</th>
                        </tr>
                        </thead>
                        <tbody>
                        {problem.cases.map(row => (
                            <tr key={row.id}>
                                <td>{row.id}</td>
                                <td>{row.name}</td>
                                <td>{row.kind}</td>
                                <td>
                                    <span className={"badge " + (row.passed ? "green" : "red")}>
                                        {row.passed ? "通过" : "失败"}
                                    </span>
                                </td>
                                <td>{row.time}</td>
                                <td>{row.memory}</td>
                                <td>{row.visible ? "可见" : "不可见"}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    <div className="table-footer">
                        <span>共 {problem.totalCases} 个用例 · 当前显示 {problem.cases.length} 个</span>
                        <span className="link">批量导入 CSV</span>
                    </div>
                </div>

                <div className="problem-side">
                    {/* 评分规则：权重与总分可编辑，进度条随权重实时变化 */}
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">评分规则</div>
                            <span className="badge blue">
                                总分{" "}
                                <input type="number"
                                       min={0}
                                       max={100}
                                       aria-label="总分"
                                       value={totalScore}
                                       style={ScoreInputStyle}
                                       onChange={event => setTotalScore(toNumber(event.target.value))}/>
                            </span>
                        </div>
                        <div className="card-body">
                            {WeightRows.map(row => (
                                <React.Fragment key={row.key}>
                                    <div className="weight-row">
                                        <span>{row.label}</span>
                                        <span className="row" style={{ gap: 3 }}>
                                            <input type="number"
                                                   min={0}
                                                   max={100}
                                                   aria-label={row.label + "权重"}
                                                   className="input"
                                                   value={weights[row.key]}
                                                   style={WeightInputStyle}
                                                   onChange={event => updateWeight(row.key, event.target.value)}/>
                                            <strong>%</strong>
                                        </span>
                                    </div>
                                    <div className="bar">
                                        <span className={row.barClass}
                                              style={{ width: weights[row.key] + "%" }}/>
                                    </div>
                                </React.Fragment>
                            ))}
                            <div className="weight-note">
                                必过用例全部通过才可获得加分用例分数；未通过则最高 {weights.mustPass} 分。
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-head"><div className="card-title">运行限制</div></div>
                        <div className="card-body">
                            {limitRows.map((row, index) => (
                                <div className={"res-row" + (index === limitRows.length - 1 ? " last" : "")}
                                     key={row.label}>
                                    <span>{row.label}</span><strong>{row.value}</strong>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="card tip-card amber">
                        <div className="tip-icon amber"><Icon name="alert-triangle" size={14}/></div>
                        <div>
                            <div className="tip-title amber">隐藏测试不可泄露</div>
                            <div className="tip-desc amber">隐藏用例不会挂载到考生容器，仅在独立判题沙箱中运行。</div>
                        </div>
                    </div>
                </div>
            </div>
        </TeacherLayout>
    );
}
