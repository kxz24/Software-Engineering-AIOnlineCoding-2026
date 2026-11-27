import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { ApiError, fetchProjectWorkspace, saveProjectWorkspace, ProjectWorkspace, StudentProblem, WorkspaceSource } from "../api/client";
import { CodeEditor, languageForPath } from "./CodeEditor";
import { SampleRunPanel } from "./SampleRunPanel";

type Draft = Record<string, string>;

export interface ProjectWorkspaceActions {
    save: () => Promise<ProjectWorkspace>;
    snapshot: () => Promise<WorkspaceSource>;
    refresh: () => Promise<void>;
}

interface Props {
    examId: number;
    problem: StudentProblem;
    finished: boolean;
}

function fileContents(workspace: ProjectWorkspace): Draft {
    return Object.fromEntries(workspace.files.map(file => [file.path, file.content]));
}

function revisions(workspace: ProjectWorkspace): WorkspaceSource {
    return { workspaceVersion: workspace.version,
        workspaceRevisions: Object.fromEntries(workspace.files.map(file => [file.path, file.revision])) };
}

function Files({ paths, selected, select, fixed, prefix = "" }: {
    paths: string[]; selected: string; select: (path: string) => void; fixed: Set<string>; prefix?: string;
}) {
    const folders = new Map<string, string[]>();
    const leaf: string[] = [];
    paths.forEach(path => {
        const slash = path.indexOf("/");
        if (slash < 0) {
            leaf.push(path);
            return;
        }
        const folder = path.slice(0, slash);
        folders.set(folder, [...(folders.get(folder) || []), path.slice(slash + 1)]);
    });
    return (
        <ul className="project-files">
            {Array.from(folders, ([folder, children]) => (
                <li key={folder}>
                    <details open>
                        <summary>{folder}</summary>
                        <Files paths={children} selected={selected} select={select} fixed={fixed} prefix={prefix + folder + "/"}/>
                    </details>
                </li>
            ))}
            {leaf.map(name => {
                const path = prefix + name;
                return <li key={name}><button type="button" aria-current={path === selected ? true : undefined}
                                              disabled={fixed.has(path)} onClick={() => select(path)}>
                    {name}{fixed.has(path) ? "（只读）" : ""}
                </button></li>;
            })}
        </ul>
    );
}

export const ProjectWorkspacePanel = forwardRef<ProjectWorkspaceActions, Props>(function ProjectWorkspacePanel(
    { examId, problem, finished }, ref
) {
    const [workspace, setWorkspace] = useState<ProjectWorkspace | null>(null);
    const [files, setFiles] = useState<Draft>({});
    const [selected, setSelected] = useState("");
    const [editorVersion, setEditorVersion] = useState(0);
    const [fileName, setFileName] = useState("");
    const [error, setError] = useState("");
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState(false);
    const latest = useRef<ProjectWorkspace | null>(null);
    const draft = useRef<Draft>({});
    const saved = useRef<Draft>(draft.current);
    const pending = useRef<Promise<ProjectWorkspace> | null>(null);
    const { problemId } = problem;

    const refresh = async () => {
        if (draft.current !== saved.current) return;
        const result = await fetchProjectWorkspace(examId, problemId);
        if (draft.current !== saved.current) return;
        if (latest.current) setEditorVersion(value => value + 1);
        latest.current = result;
        draft.current = fileContents(result);
        saved.current = draft.current;
        setFiles(draft.current);
        setWorkspace(result);
        setSelected(current => Object.prototype.hasOwnProperty.call(draft.current, current)
            ? current : result.files[0]?.path || "");
        setError("");
        setDirty(false);
    };

    useEffect(() => {
        void refresh().catch((reason: ApiError) => setError(reason.message));
        // 实例由题号区分。
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [examId, problemId]);

    const save = async (): Promise<ProjectWorkspace> => {
        if (pending.current) await pending.current;
        if (!latest.current) throw new Error("工程工作区还未加载");
        if (draft.current === saved.current) return latest.current;
        const snapshot = draft.current;
        setSaving(true);
        const write = saveProjectWorkspace(examId, problemId, snapshot, revisions(latest.current));
        pending.current = write;
        try {
            const updated = await write;
            latest.current = updated;
            saved.current = snapshot;
            setWorkspace(updated);
            setDirty(draft.current !== saved.current);
            setError("");
            return updated;
        } catch (reason) {
            setError((reason as Error).message);
            throw reason;
        } finally {
            if (pending.current === write) pending.current = null;
            setSaving(false);
        }
    };

    const snapshot = async (): Promise<WorkspaceSource> => revisions(await save());
    useImperativeHandle(ref, () => ({ save, snapshot, refresh }));

    useEffect(() => {
        if (!dirty || finished) return;
        const task = window.setTimeout(() => void save().catch(() => {}), 800);
        return () => window.clearTimeout(task);
        // 每次文本编辑都重新计时。
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [files, dirty, finished]);

    useEffect(() => {
        if (!dirty) return;
        const warn = (event: BeforeUnloadEvent) => {
            event.preventDefault();
            event.returnValue = "";
        };
        window.addEventListener("beforeunload", warn);
        return () => window.removeEventListener("beforeunload", warn);
    }, [dirty]);

    const change = (next: Draft) => {
        draft.current = next;
        setFiles(next);
        setDirty(true);
    };

    if (!workspace) {
        return <div className="problem-body" role="status">{error || "正在加载工程工作区…"}</div>;
    }

    const fixed = new Set(workspace.fixedFiles);
    const paths = [...Object.keys(files), ...Array.from(fixed)].sort();
    const create = (event: React.FormEvent) => {
        event.preventDefault();
        const path = fileName.trim();
        if (!path || path.length > 128 || /[\\:\x00-\x1f]/.test(path)
            || path.split("/").some(part => part === "" || part === "." || part === "..")
            || paths.some(item => item.toLowerCase() === path.toLowerCase()
                || item.startsWith(path + "/") || path.startsWith(item + "/"))) {
            setError("请输入独立的相对文件路径，例如 src/main.c");
            return;
        }
        change({ ...draft.current, [path]: "" });
        setSelected(path);
        setFileName("");
        setError("");
    };

    const remove = () => {
        if (!selected || !window.confirm("删除「" + selected + "」？")) return;
        const next = { ...draft.current };
        delete next[selected];
        setEditorVersion(value => value + 1);
        change(next);
        setSelected(Object.keys(next).sort()[0] || "");
    };

    const prefix = `project/${examId}/${problemId}/`;
    const modelPath = prefix + selected;
    return (
        <>
            <div className="editor-tabs project-workspace-bar">
                <strong>{selected || "工程工作区"}</strong>
                <div className="editor-actions">
                    <span role="status">{saving ? "保存中…" : dirty ? "有未保存修改" : "已保存"}</span>
                    <button className="btn btn-secondary btn-sm" type="button" disabled={!dirty || saving || finished}
                            onClick={() => void save().catch(() => {})}>保存</button>
                </div>
            </div>
            {error && <p className="project-workspace-error" role="alert">{error}</p>}
            <div className="project-workspace-main">
                <nav aria-label="工程文件" className="project-workspace-tree">
                    {!finished && <form onSubmit={create} className="project-workspace-create">
                        <label htmlFor="project-new-file">新文件路径</label>
                        <input className="input" id="project-new-file" placeholder="src/main.c"
                               value={fileName} onChange={event => setFileName(event.target.value)}/>
                        <button type="submit" className="btn btn-secondary btn-sm" disabled={!fileName.trim()}>新建文件</button>
                    </form>}
                    <Files paths={paths} selected={selected} select={setSelected} fixed={fixed}/>
                    {selected && !finished && <button className="btn btn-secondary btn-sm" type="button"
                                                      onClick={remove}>删除当前文件</button>}
                </nav>
                <div className="project-workspace-code">
                    {selected ? (finished ? <pre>{files[selected]}</pre> :
                        <CodeEditor key={editorVersion} path={modelPath} initialValue={files[selected]} language={languageForPath(selected)}
                                    onChange={(editorPath, value) => {
                                        const file = editorPath.slice(prefix.length);
                                        if (Object.prototype.hasOwnProperty.call(draft.current, file)
                                            && draft.current[file] !== value) change({ ...draft.current, [file]: value });
                                    }}/>
                    ) : <p className="problem-body muted">新建文件或从文件树选择文件。</p>}
                </div>
            </div>
            <SampleRunPanel examId={examId} problem={problem} code={paths.length ? "工程工作区" : null}
                            prepareSource={snapshot} finished={finished}/>
        </>
    );
});
