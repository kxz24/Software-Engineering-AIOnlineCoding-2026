import React, { useEffect, useMemo, useState } from "react";
import { Link, useHistory, useParams } from "react-router-dom";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { Icon } from "../../components/Icon";
import { toast } from "../../components/Toast";
import { Routes } from "../../api/urls";
import {
    ApiError,
    ExamDetail,
    ExamProblemEntry,
    examAction,
    fetchExam,
    fetchProblems,
    ProblemSummary,
    setExamProblems,
} from "../../api/client";

const TypeLabels: Record<string, string> = { engineering: "工程题", algorithm: "算法题" };
const DifficultyLabels: Record<string, string> = { easy: "简单", medium: "中等", hard: "困难" };

/** 分值输入：行内小尺寸 */
const ScoreInputStyle: React.CSSProperties = {
    width: 52,
    height: 24,
    padding: "0 6px",
    fontSize: 11,
    textAlign: "right",
};

/** 试卷内的一道题：组卷条目 + 本地编辑状态 */
interface PaperItem {
    problemId: number;
    score: number;
    info: ProblemSummary;
}

/** 把输入收敛成 1–1000 的整数（非法回退旧值） */
function toScore(raw: string, fallback: number): number {
    const parsed = Number.parseInt(raw, 10);
    if (Number.isNaN(parsed)) {
        return fallback;
    }
    return Math.min(1000, Math.max(1, parsed));
}

/**
 * 09 组卷：从题库选题、排定题序与分值。
 *
 * 保存为整体替换（顺序即数组顺序）；发布前必须至少有一道题。
 * 考试开始后配置冻结，本页只读。
 */
export function ProblemConfigPage() {
    const { examId } = useParams<{ examId: string }>();
    const id = Number(examId);
    const history = useHistory();

    const [exam, setExam] = useState<ExamDetail | null>(null);
    const [bank, setBank] = useState<ProblemSummary[]>([]);
    const [paper, setPaper] = useState<PaperItem[]>([]);
    const [keyword, setKeyword] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState(false);

    const load = () => {
        setLoading(true);
        setError(null);
        Promise.all([fetchExam(id), fetchProblems()])
            .then(([detail, problems]) => {
                setExam(detail);
                setBank(problems.problems);
                const byId = new Map(problems.problems.map(p => [p.id, p]));
                setPaper(detail.problems.map((entry: ExamProblemEntry) => ({
                    problemId: entry.problemId,
                    score: entry.score,
                    // 题库里的题目被删掉时保留条目信息（后端已阻止删除被引用的题目前先展示）
                    info: byId.get(entry.problemId) || {
                        id: entry.problemId,
                        title: entry.title,
                        type: entry.type as ProblemSummary["type"],
                        language: entry.language,
                        difficulty: entry.difficulty as ProblemSummary["difficulty"],
                        image: "",
                        sampleCount: entry.sampleCount,
                        hiddenCount: entry.hiddenCount,
                        updated: "",
                    },
                })));
                setDirty(false);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, [id]);

    /** 已开始 / 已归档：只读 */
    const frozen = !!exam && (
        exam.status === "archived" ||
        (exam.status === "published" && exam.studentStatus !== "upcoming")
    );

    const totalScore = paper.reduce((sum, item) => sum + item.score, 0);
    const paperIds = new Set(paper.map(item => item.problemId));
    const available = useMemo(
        () => bank.filter(problem =>
            !paperIds.has(problem.id) &&
            (keyword.trim() === "" || problem.title.indexOf(keyword.trim()) >= 0)
        ),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [bank, paper, keyword]
    );

    const markDirty = (next: PaperItem[]) => {
        setPaper(next);
        setDirty(true);
    };

    const addProblem = (problem: ProblemSummary) => {
        if (frozen) {
            return;
        }
        markDirty([...paper, { problemId: problem.id, score: 100, info: problem }]);
    };

    const removeProblem = (problemId: number) => {
        markDirty(paper.filter(item => item.problemId !== problemId));
    };

    const moveProblem = (index: number, offset: -1 | 1) => {
        const target = index + offset;
        if (target < 0 || target >= paper.length) {
            return;
        }
        const next = [...paper];
        const [item] = next.splice(index, 1);
        next.splice(target, 0, item);
        markDirty(next);
    };

    const setScore = (problemId: number, raw: string) => {
        markDirty(paper.map(item =>
            item.problemId === problemId
                ? { ...item, score: toScore(raw, item.score) }
                : item
        ));
    };

    /** 保存组卷；成功返回 true */
    const save = async (): Promise<boolean> => {
        setSaving(true);
        try {
            const detail = await setExamProblems(id, paper.map(item => ({
                problemId: item.problemId,
                score: item.score,
            })));
            setExam(detail);
            setDirty(false);
            setSaving(false);
            return true;
        } catch (e) {
            setSaving(false);
            toast((e as ApiError).message, "warning");
            return false;
        }
    };

    const handleSave = async () => {
        if (await save()) {
            toast("组卷已保存", "success");
        }
    };

    const handlePublish = async () => {
        if (paper.length === 0) {
            toast("请先从题库选题", "warning");
            return;
        }
        if (!(await save())) {
            return;
        }
        examAction(id, "publish")
            .then(() => {
                toast("考试已发布，学生即可看到", "success");
                history.push(Routes.examManage);
            })
            .catch((e: ApiError) => toast(e.message, "warning"));
    };

    if (loading) {
        return (
            <TeacherLayout breadcrumb={["工作台", "考试管理", "组卷"]}>
                <div className="card"><div className="card-body muted">加载中…</div></div>
            </TeacherLayout>
        );
    }

    return (
        <TeacherLayout breadcrumb={["工作台", "考试管理", "组卷"]}>
            <div className="page-head">
                <div>
                    <div className="page-title">组卷：{exam?.title || ""}</div>
                    <div className="page-sub">
                        {paper.length} 道题 · 总分 {totalScore} 分
                        {dirty && <span className="muted">（有未保存的修改）</span>}
                    </div>
                </div>
                <div className="page-actions">
                    <Link className="btn btn-ghost" to={Routes.examEdit(id)}>
                        <Icon name="arrow-left" size={14}/>考试配置
                    </Link>
                    {!frozen && (
                        <>
                            <button type="button" className="btn btn-secondary" disabled={saving}
                                    onClick={handleSave}>
                                保存组卷
                            </button>
                            {exam?.status === "draft" && (
                                <button type="button" className="btn btn-primary" disabled={saving}
                                        onClick={handlePublish}>
                                    <Icon name="check" size={14}/>保存并发布
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: "#fecaca", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#b91c1c", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/> {error}
                        <span className="link" style={{ marginLeft: 10 }} onClick={load}>重试</span>
                    </div>
                </div>
            )}

            {frozen && (
                <div className="card" style={{ borderColor: "#fde68a", marginBottom: 14 }}>
                    <div className="card-body" style={{ color: "#92400e", fontSize: 12 }}>
                        <Icon name="alert-triangle" size={13}/>
                        {exam?.status === "archived" ? "已归档的考试不能编辑" : "考试已开始，配置已冻结"}
                    </div>
                </div>
            )}

            <div className="problem-main">
                {/* 试卷：题序 / 题目 / 分值 */}
                <div className="card test-card">
                    <div className="card-head">
                        <div>
                            <div className="card-title">试卷</div>
                            <div className="card-sub">顺序即题序；分值用于判分与成绩统计</div>
                        </div>
                        <div className="table-tools">
                            <span className="badge blue">总分 {totalScore}</span>
                        </div>
                    </div>
                    <table className="table">
                        <thead>
                        <tr>
                            <th style={{ width: 56 }}>题序</th>
                            <th>题目</th>
                            <th>题型 / 语言</th>
                            <th>用例</th>
                            <th style={{ width: 110 }}>分值</th>
                            {!frozen && <th style={{ width: 120 }}>操作</th>}
                        </tr>
                        </thead>
                        <tbody>
                        {paper.length === 0 && (
                            <tr>
                                <td colSpan={frozen ? 5 : 6} style={{ color: "#94a3b8" }}>
                                    还没有选题，从右侧题库添加
                                </td>
                            </tr>
                        )}
                        {paper.map((item, index) => (
                            <tr key={item.problemId}>
                                <td><span className="tab-pill active">任务 {index + 1}</span></td>
                                <td>
                                    <div className="strong">{item.info.title}</div>
                                    <div className="sub">#{item.problemId}</div>
                                </td>
                                <td>
                                    <span className="badge blue">{TypeLabels[item.info.type] || item.info.type}</span>{" "}
                                    <span className="badge gray">{item.info.language}</span>{" "}
                                    <span className="badge amber">{DifficultyLabels[item.info.difficulty] || item.info.difficulty}</span>
                                </td>
                                <td className="muted">样例 {item.info.sampleCount} · 隐藏 {item.info.hiddenCount}</td>
                                <td>
                                    {frozen ? item.score : (
                                        <input className="input" type="number" min={1} max={1000}
                                               style={ScoreInputStyle} value={item.score}
                                               aria-label={`${item.info.title} 分值`}
                                               onChange={e => setScore(item.problemId, e.target.value)}/>
                                    )}
                                </td>
                                {!frozen && (
                                    <td>
                                        <span className="link" onClick={() => moveProblem(index, -1)}>上移</span>
                                        <span className="muted"> · </span>
                                        <span className="link" onClick={() => moveProblem(index, 1)}>下移</span>
                                        <span className="muted"> · </span>
                                        <span className="link" style={{ color: "#dc2626" }}
                                              onClick={() => removeProblem(item.problemId)}>移除</span>
                                    </td>
                                )}
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    <div className="table-footer">
                        <span>共 {paper.length} 道题 · 总分 {totalScore} 分</span>
                        <span className="muted">
                            {frozen ? "配置已冻结" : "保存为整体替换：题序、分值一并提交"}
                        </span>
                    </div>
                </div>

                <div className="problem-side">
                    {/* 题库选题 */}
                    <div className="card">
                        <div className="card-head">
                            <div className="card-title">从题库添加</div>
                            <div className="table-tools">
                                <input className="input" placeholder="搜索题目"
                                       style={{ width: 130, height: 26, fontSize: 11 }}
                                       value={keyword} onChange={e => setKeyword(e.target.value)}/>
                            </div>
                        </div>
                        <div className="card-body" style={{ maxHeight: 340, overflowY: "auto" }}>
                            {available.length === 0 && (
                                <div className="muted" style={{ fontSize: 11.5 }}>
                                    {bank.length === 0
                                        ? "题库为空，先到「题库管理」创建题目"
                                        : "没有匹配的题目"}
                                </div>
                            )}
                            {available.map(problem => (
                                <div className="res-row" key={problem.id}
                                     style={{ alignItems: "center", padding: "7px 0" }}>
                                    <span style={{ flex: 1, minWidth: 0 }}>
                                        <span className="strong" style={{ fontSize: 11.5 }}>{problem.title}</span>
                                        <span className="muted" style={{ fontSize: 10.5, marginLeft: 6 }}>
                                            {TypeLabels[problem.type] || problem.type} · {problem.language} ·{" "}
                                            {DifficultyLabels[problem.difficulty] || problem.difficulty}
                                        </span>
                                    </span>
                                    <span className={"btn btn-secondary btn-sm" + (frozen ? " disabled" : "")}
                                          onClick={() => addProblem(problem)}>
                                        <Icon name="plus" size={11}/>添加
                                    </span>
                                </div>
                            ))}
                        </div>
                        <div className="table-footer">
                            <Link className="link" to={Routes.problemBank}>管理题库 →</Link>
                        </div>
                    </div>

                    <div className="card tip-card amber">
                        <div className="tip-icon amber"><Icon name="alert-triangle" size={14}/></div>
                        <div>
                            <div className="tip-title amber">隐藏测试不可泄露</div>
                            <div className="tip-desc amber">
                                学生端只会拿到题面、初始代码与样例测试；隐藏测试仅在判题时使用。
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </TeacherLayout>
    );
}
