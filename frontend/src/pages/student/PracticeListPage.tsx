import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StudentLayout } from "../../layouts/StudentLayout";
import { Icon } from "../../components/Icon";
import { Routes } from "../../api/urls";
import { formatDateTime } from "../../api/format";
import { ApiError } from "../../api/client";
import {
    fetchPracticeProblems,
    PracticeProblemSummary,
} from "../../api/practice";

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

const LanguageLabels: Record<string, string> = {
    python: "Python",
    cpp: "C++",
    c: "C",
    java: "Java",
};

/**
 * 学生端「自由练习」：浏览题库中开放练习的算法题。
 * 题目由教师在题库中勾选「开放自由练习」后出现。
 */
export function PracticeListPage() {
    const [problems, setProblems] = useState<PracticeProblemSummary[]>([]);
    const [keyword, setKeyword] = useState("");
    const [difficulty, setDifficulty] = useState("");
    const [language, setLanguage] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        setError(null);
        fetchPracticeProblems({
            keyword: keyword.trim() || undefined,
            difficulty: difficulty || undefined,
            language: language || undefined,
        })
            .then(result => {
                setProblems(result.problems);
                setLoading(false);
            })
            .catch((e: ApiError) => {
                setError(e.message);
                setLoading(false);
            });
    };

    useEffect(load, []);   // 首次进入加载，筛选由按钮触发

    const commentTotal = problems.reduce((sum, item) => sum + item.commentCount, 0);

    return (
        <StudentLayout active="practice">
            <div className="page-head">
                <div>
                    <div className="page-title">自由练习</div>
                    <div className="page-sub">
                        自主选题练习，不计入考试成绩 · 共 {problems.length} 道题 · {commentTotal} 条讨论
                    </div>
                </div>
                <div className="page-actions">
                    <input className="input"
                           style={{ width: 200, height: 30, fontSize: 11.5 }}
                           placeholder="搜索题目 / 题面"
                           value={keyword}
                           onChange={event => setKeyword(event.target.value)}
                           onKeyDown={event => {
                               if (event.key === "Enter") {
                                   load();
                               }
                           }}/>
                    <select className="select"
                            style={{ width: 110, height: 30, fontSize: 11.5 }}
                            value={difficulty}
                            onChange={event => setDifficulty(event.target.value)}>
                        <option value="">全部难度</option>
                        {Object.keys(DifficultyLabels).map(key => (
                            <option key={key} value={key}>{DifficultyLabels[key]}</option>
                        ))}
                    </select>
                    <select className="select"
                            style={{ width: 110, height: 30, fontSize: 11.5 }}
                            value={language}
                            onChange={event => setLanguage(event.target.value)}>
                        <option value="">全部语言</option>
                        {Object.keys(LanguageLabels).map(key => (
                            <option key={key} value={key}>{LanguageLabels[key]}</option>
                        ))}
                    </select>
                    <button type="button" className="btn btn-primary" onClick={load}>
                        <Icon name="search" size={13}/>筛选
                    </button>
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

            <div className="card">
                <div className="card-head">
                    <div>
                        <div className="card-title">开放练习的题目</div>
                        <div className="card-sub">按更新时间倒序；点击进入可写代码、看样例和参与讨论</div>
                    </div>
                    <span className="badge blue">{problems.length} 题</span>
                </div>
                <table className="table">
                    <thead>
                    <tr>
                        <th>题目</th>
                        <th>难度</th>
                        <th>语言</th>
                        <th>公开样例</th>
                        <th>用例总数</th>
                        <th>讨论</th>
                        <th>更新时间</th>
                        <th>操作</th>
                    </tr>
                    </thead>
                    <tbody>
                    {loading && (
                        <tr><td colSpan={8} className="muted">加载中…</td></tr>
                    )}
                    {!loading && problems.length === 0 && (
                        <tr>
                            <td colSpan={8} className="muted" style={{ textAlign: "center" }}>
                                {error ? "加载失败" : "暂无开放自由练习的题目，请等待老师在题库中开放"}
                            </td>
                        </tr>
                    )}
                    {problems.map(problem => (
                        <tr key={problem.id}>
                            <td>
                                <div className="strong">{problem.title}</div>
                                <div className="sub">算法题 · 单用例限时见题目页</div>
                            </td>
                            <td>
                                <span className={DifficultyBadge[problem.difficulty] || "badge gray"}>
                                    {DifficultyLabels[problem.difficulty] || problem.difficulty}
                                </span>
                            </td>
                            <td>{LanguageLabels[problem.language] || problem.language}</td>
                            <td>{problem.sampleCount}</td>
                            <td>{problem.testCount}</td>
                            <td>{problem.commentCount} 条</td>
                            <td>{problem.updated ? formatDateTime(problem.updated) : "—"}</td>
                            <td>
                                <Link className="link" to={Routes.practiceProblem(problem.id)}>
                                    开始练习
                                </Link>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
                <div className="table-footer">
                    <span>共 {problems.length} 道开放练习</span>
                    <span className="muted">练习提交不占用考试次数，不影响考试成绩</span>
                </div>
            </div>
        </StudentLayout>
    );
}
