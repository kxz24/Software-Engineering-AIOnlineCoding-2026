import React from "react";
import ReactDOM from "react-dom";
import { act } from "react-dom/test-utils";
import * as client from "../api/client";
import { SampleRunPanel } from "./SampleRunPanel";

const problem: client.StudentProblem = {
    problemId: 8, order: 0, score: 10, bestScore: 0, title: "两数之和",
    type: "algorithm", language: "cpp", difficulty: "easy",
    description: "", starterCode: "",
    samples: [{ name: "样例 1", input: "2 3", expected: "5" }],
};

test("在工作台展示编译诊断，重跑后展示样例的实际和期望输出", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const code = "int main() {}";
    const start = jest.spyOn(client, "startSampleRun").mockResolvedValue({ runId: "preview" });
    const fetch = jest.spyOn(client, "fetchSampleRun")
        .mockResolvedValueOnce({
            status: "completed", compileOk: false, compileOutput: "main.cpp: error: expected ';'", cases: [],
        })
        .mockResolvedValueOnce({
            status: "completed", compileOk: true, compileOutput: "",
            cases: [{
                index: 1, name: "样例 1", verdict: "wrong_answer", timeMs: 3,
                expectedOutput: "5", outputExcerpt: "4", errorExcerpt: "",
            }],
        });
    const runButton = () => container.querySelector<HTMLButtonElement>(".sample-run-button")!;

    try {
        act(() => {
            ReactDOM.render(<SampleRunPanel examId={1} problem={problem} code={code} finished={false}/>, container);
        });
        await act(async () => { runButton().click(); });
        expect(start).toHaveBeenCalledWith(1, 8, code, expect.anything());
        expect(container.textContent).toContain("编译失败");
        expect(container.querySelector("pre")?.textContent).toBe("main.cpp: error: expected ';'");

        await act(async () => { runButton().click(); });
        expect(container.textContent).toContain("0 / 1 个样例通过");
        expect(Array.from(container.querySelectorAll("pre"), block => block.textContent)).toEqual(["4", "5"]);
    } finally {
        act(() => { ReactDOM.unmountComponentAtNode(container); });
        container.remove();
        start.mockRestore();
        fetch.mockRestore();
    }
});
