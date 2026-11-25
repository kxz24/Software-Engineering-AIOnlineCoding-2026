import React, { useEffect, useRef, useState } from "react";
import { fetchSampleRun, SampleRunResult, startSampleRun, StudentProblem } from "../api/client";
import { verdictMeta } from "../api/judge";
import { Icon } from "./Icon";

const LanguageLabels: Record<string, string> = {
    python: "Python",
    c: "C17",
    cpp: "C++17",
    java: "Java",
};

interface Run {
    examId: number;
    problemId: number;
    code: string;
    result: SampleRunResult;
}

interface Props {
    examId: number;
    problem: StudentProblem;
    code: string;
    finished: boolean;
}

export function SampleRunPanel({ examId, problem, code, finished }: Props) {
    const [run, setRun] = useState<Run | null>(null);
    const [expanded, setExpanded] = useState(true);
    const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
    const activeRequest = useRef<AbortController | null>(null);
    useEffect(() => () => activeRequest.current?.abort(), []);

    if (problem.type !== "algorithm") {
        return null;
    }

    const result = run?.examId === examId && run.problemId === problem.problemId ? run.result : null;
    const busy = run?.result.status === "queued" || run?.result.status === "running";
    const compileOnly = problem.samples.length === 0;
    const actionLabel = compileOnly ? "检查编译" : "运行公开样例";
    const language = LanguageLabels[problem.language];
    const disabledReason = finished ? "考试已结束"
        : !language || (compileOnly && problem.language === "python") ? "本题没有可运行的公开样例"
        : !code.trim() ? "请先编写代码"
        : busy && !result ? "另一题正在运行" : "";

    const runCode = async () => {
        if (activeRequest.current || disabledReason) {
            return;
        }
        const request = new AbortController();
        activeRequest.current = request;
        const snapshot = { examId, problemId: problem.problemId, code };
        const updateResult = (next: SampleRunResult) => setRun({ ...snapshot, result: next });
        setExpanded(true);
        setSelectedIndex(null);
        updateResult({ status: "queued" });

        const timeout = window.setTimeout(() => {
            if (request.signal.aborted) {
                return;
            }
            updateResult({ status: "failed", message: "等待运行结果超时，请稍后重试。" });
            request.abort();
            activeRequest.current = null;
        }, 195_000);
        try {
            const { runId } = await startSampleRun(examId, problem.problemId, code, request.signal);
            while (!request.signal.aborted) {
                const next = await fetchSampleRun(examId, problem.problemId, runId, request.signal);
                if (request.signal.aborted) {
                    break;
                }
                updateResult(next);
                if (next.status === "completed") {
                    const first = next.cases.find(item => item.verdict !== "accepted") || next.cases[0];
                    setSelectedIndex(first?.index ?? null);
                    break;
                }
                if (next.status === "failed") {
                    break;
                }
                await new Promise(resolve => window.setTimeout(resolve, 1500));
            }
        } catch (error) {
            if (!request.signal.aborted) {
                updateResult({ status: "failed", message: error.message || "运行失败，请稍后重试。" });
            }
        } finally {
            window.clearTimeout(timeout);
            if (activeRequest.current === request) {
                activeRequest.current = null;
            }
        }
    };

    const passed = result?.status === "completed"
        ? result.cases.filter(item => item.verdict === "accepted").length : 0;
    const selectedCase = result?.status === "completed"
        ? result.cases.find(item => item.index === selectedIndex) : undefined;
    let statusLabel = "";
    let tone = "neutral";
    if (result?.status === "queued" || result?.status === "running") {
        statusLabel = result.status === "queued" ? "等待运行" : "正在运行";
    } else if (result?.status === "failed") {
        statusLabel = "运行失败";
        tone = "error";
    } else if (result?.status === "completed") {
        if (!result.compileOk) {
            statusLabel = "编译失败";
            tone = "error";
        } else {
            statusLabel = result.cases.length ? `${passed} / ${result.cases.length} 个样例通过` : "编译通过";
            tone = passed === result.cases.length ? "success" : "warning";
        }
    }

    return (
        <section className="sample-run" aria-label="代码试运行">
            <div className="sample-run-bar">
                <div className="sample-run-heading">
                    <span className="sample-run-icon"><Icon name="terminal" size={16}/></span>
                    <div>
                        <div className="sample-run-title">代码试运行 {language && <span>{language}</span>}</div>
                        <div className="sample-run-note">{disabledReason || "不占用正式提交次数"}</div>
                    </div>
                </div>
                <div className="sample-run-controls">
                    {result && (
                        <button type="button" className={`sample-run-toggle is-${tone}`}
                                aria-expanded={expanded} aria-controls="sample-run-details"
                                onClick={() => setExpanded(value => !value)}>
                            <span role="status">{statusLabel}</span>
                            <Icon name={expanded ? "chevron-down" : "chevron-right"} size={14}/>
                        </button>
                    )}
                    <button type="button" className="sample-run-button"
                            disabled={busy || Boolean(disabledReason)} onClick={runCode}>
                        {busy && result
                            ? <span aria-hidden="true" className="sample-run-spinner"/>
                            : <Icon name="play" size={15}/>}
                        {busy && result ? "运行中" : actionLabel}
                    </button>
                </div>
            </div>
            {result && (
                <div id="sample-run-details" className="sample-run-details" hidden={!expanded}>
                    {run?.code !== code && (
                        <p className="sample-run-stale">代码已修改，以下结果对应上一次运行。</p>
                    )}
                    {result.status === "queued" && <p className="sample-run-message">已加入运行队列，可以继续编辑。</p>}
                    {result.status === "running" && <p className="sample-run-message">正在使用题目指定的环境处理代码。</p>}
                    {result.status === "failed" && <p className="sample-run-message is-error" role="alert">{result.message}</p>}
                    {result.status === "completed" && !result.compileOk && (
                        <div className="sample-run-output is-error">
                            <h3>编译诊断</h3>
                            <pre tabIndex={0}>{result.compileOutput || "编译器未返回诊断信息。"}</pre>
                        </div>
                    )}
                    {result.status === "completed" && result.compileOk && result.cases.length === 0 && (
                        <p className="sample-run-message">本题没有公开样例，本次已完成编译检查。</p>
                    )}
                    {result.status === "completed" && result.compileOk && selectedCase && (
                        <>
                            <div className="sample-run-cases" aria-label="公开样例">
                                {result.cases.map(item => {
                                    const verdict = verdictMeta(item.verdict);
                                    return (
                                        <button type="button" key={item.index}
                                                className={`sample-run-case is-${verdict.tone}`}
                                                aria-pressed={item.index === selectedIndex}
                                                onClick={() => setSelectedIndex(item.index)}>
                                            <span>{item.name}</span>
                                            <small>{verdict.label}</small>
                                        </button>
                                    );
                                })}
                            </div>
                            <div className="sample-run-comparison">
                                <div className="sample-run-output">
                                    <h3>实际输出 <span>{selectedCase.timeMs} ms</span></h3>
                                    <pre tabIndex={0}>{selectedCase.outputExcerpt || "（无输出）"}</pre>
                                </div>
                                <div className="sample-run-output">
                                    <h3>期望输出</h3>
                                    <pre tabIndex={0}>{selectedCase.expectedOutput || "（空）"}</pre>
                                </div>
                            </div>
                            {selectedCase.errorExcerpt && (
                                <div className="sample-run-output is-error">
                                    <h3>运行诊断</h3>
                                    <pre tabIndex={0}>{selectedCase.errorExcerpt}</pre>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </section>
    );
}
