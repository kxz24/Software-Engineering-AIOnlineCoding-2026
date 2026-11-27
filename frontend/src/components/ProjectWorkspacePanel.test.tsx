import React from "react";
import ReactDOM from "react-dom";
import { act, Simulate } from "react-dom/test-utils";
import { fetchProjectWorkspace, saveProjectWorkspace, StudentProblem } from "../api/client";
import { ProjectWorkspaceActions, ProjectWorkspacePanel } from "./ProjectWorkspacePanel";

jest.mock("../api/client", () => ({
    fetchProjectWorkspace: jest.fn(),
    saveProjectWorkspace: jest.fn(),
}));
jest.mock("./CodeEditor", () => ({
    CodeEditor: ({ path, initialValue, onChange }: {
        path: string; initialValue: string; onChange: (path: string, value: string) => void;
    }) => (
        <textarea aria-label="代码" value={initialValue} onChange={event => onChange(path, event.target.value)}/>
    ),
    languageForPath: () => "python",
}));
jest.mock("./SampleRunPanel", () => ({ SampleRunPanel: () => null }));

test("提交快照先保存在线编辑的多个文件，再返回服务端版本", async () => {
    const problem = { problemId: 3 } as StudentProblem;
    (fetchProjectWorkspace as jest.Mock).mockResolvedValue({
        version: 1, fixedFiles: [],
        files: [{ path: "server/main.py", content: "first", revision: 1 }],
    });
    (saveProjectWorkspace as jest.Mock).mockResolvedValue({
        version: 2, fixedFiles: [], files: [
            { path: "server/main.py", content: "updated", revision: 2 },
            { path: "client/client.py", content: "client", revision: 1 },
        ],
    });
    const actions = React.createRef<ProjectWorkspaceActions>();
    const host = document.createElement("div");
    document.body.appendChild(host);
    const type = (field: string, value: string) => act(() => {
        const input = host.querySelector<HTMLInputElement | HTMLTextAreaElement>(field)!;
        input.value = value;
        Simulate.change(input);
    });
    try {
        await act(async () => {
            ReactDOM.render(<ProjectWorkspacePanel ref={actions} examId={1} problem={problem} finished={false}/>, host);
        });
        type("textarea", "updated");
        type("#project-new-file", "client/client.py");
        act(() => Simulate.submit(host.querySelector("form")!));
        type("textarea", "client");

        await act(async () => {
            await expect(actions.current!.snapshot()).resolves.toEqual({
                workspaceVersion: 2, workspaceRevisions: { "server/main.py": 2, "client/client.py": 1 },
            });
        });
        expect(saveProjectWorkspace).toHaveBeenCalledWith(1, 3, {
            "server/main.py": "updated", "client/client.py": "client",
        }, { workspaceVersion: 1, workspaceRevisions: { "server/main.py": 1 } });
    } finally {
        act(() => { ReactDOM.unmountComponentAtNode(host); });
        host.remove();
    }
});
