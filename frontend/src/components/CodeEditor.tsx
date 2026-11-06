import React, { useEffect, useRef, useState } from "react";

/**
 * Monaco Editor 封装。
 *
 * monaco-editor 在本项目中只作为静态资源依赖（npm install 时由
 * scripts/copy-monaco.js 复制到 public/monaco-vs），不走 webpack 打包，
 * 因此这里用官方 AMD loader 按需加载，避免 CRA 3.x 下的构建配置改动，
 * 也避免运行时依赖在线 CDN。
 *
 * 组件内部为每个 path 维护独立的 model：切换文件时换 model 而不是重建编辑器，
 * 各文件的撤销历史、光标与滚动位置都能保留（视图状态手动存取）。
 */

/** Monaco 的类型：资源型依赖，无类型声明可用，统一以 any 描述 */
type MonacoNamespace = any;

declare global {
    interface Window {
        require?: any;
        monaco?: any;
    }
}

/** public/monaco-vs 的地址，构建后由 Nginx / 静态服务器直接提供 */
const AssetBase = `${process.env.PUBLIC_URL || ""}/monaco-vs`;

/** 加载状态：loading 时显示占位，failed 时退化为普通文本框，页面始终可用 */
type LoadState = "loading" | "ready" | "failed";

/** 加载 Monaco 的全局单例 Promise，重复挂载/卸载也只加载一次 */
let monacoPromise: Promise<MonacoNamespace> | null = null;

/** 以 AMD 方式从本地静态资源加载 Monaco（vs/editor/editor.main 按需拉取语言模块） */
function loadMonaco(): Promise<MonacoNamespace> {
    if (monacoPromise) {
        return monacoPromise;
    }
    monacoPromise = new Promise<MonacoNamespace>((resolve, reject) => {
        if (window.monaco) {
            resolve(window.monaco);
            return;
        }
        const script = document.createElement("script");
        script.src = `${AssetBase}/loader.js`;
        script.async = true;
        script.onload = () => {
            const amdRequire = window.require;
            if (!amdRequire) {
                reject(new Error("Monaco loader 加载后缺少 AMD require"));
                return;
            }
            amdRequire.config({ paths: { vs: AssetBase } });
            amdRequire(
                ["vs/editor/editor.main"],
                () => {
                    if (window.monaco) {
                        resolve(window.monaco);
                    } else {
                        reject(new Error("Monaco 加载完成但缺少全局 monaco"));
                    }
                },
                (error: unknown) => reject(error)
            );
        };
        script.onerror = () => reject(new Error("Monaco loader.js 加载失败"));
        document.head.appendChild(script);
    });
    // 失败时清掉单例，允许之后重试
    monacoPromise.catch(() => {
        monacoPromise = null;
    });
    return monacoPromise;
}

/** 按扩展名推断 Monaco 语言 id，供「自动」语言模式使用 */
export function languageForPath(path: string): string {
    const extension = path.slice(path.lastIndexOf(".") + 1).toLowerCase();
    const table: Record<string, string> = {
        py: "python",
        c: "c",
        h: "c",
        cpp: "cpp",
        cc: "cpp",
        cxx: "cpp",
        hpp: "cpp",
        java: "java",
        js: "javascript",
        ts: "typescript",
        go: "go",
        sql: "sql",
        json: "json",
        md: "markdown",
        toml: "ini",
        ini: "ini",
        txt: "plaintext",
    };
    return table[extension] || "plaintext";
}

/** 语言选择器里的选项：'' 表示按文件扩展名自动推断 */
export const LanguageOptions: { id: string; label: string }[] = [
    { id: "", label: "自动（按扩展名）" },
    { id: "python", label: "Python" },
    { id: "c", label: "C" },
    { id: "cpp", label: "C++" },
    { id: "java", label: "Java" },
    { id: "javascript", label: "JavaScript" },
    { id: "typescript", label: "TypeScript" },
    { id: "go", label: "Go" },
    { id: "sql", label: "SQL" },
    { id: "plaintext", label: "纯文本" },
];

/** 资源缺失时的兜底文本框样式：与原 textarea 版编辑区观感一致 */
const FallbackStyle: React.CSSProperties = {
    display: "block",
    width: "100%",
    height: "100%",
    margin: 0,
    padding: "8px 12px",
    border: "none",
    outline: "none",
    resize: "none",
    background: "transparent",
    whiteSpace: "pre",
    overflow: "auto",
    color: "#334155",
    fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", Menlo, monospace",
    fontSize: 12,
    lineHeight: "20px",
};

interface Props {
    /** 当前文件的路径，作为 model 的标识；变化时切换 model 而不重建编辑器 */
    path: string;
    /** 该 path 第一次打开时的初始内容 */
    initialValue: string;
    /** Monaco 语言 id */
    language: string;
    /** 内容变化（path + 最新全文） */
    onChange: (path: string, value: string) => void;
}

export function CodeEditor({ path, initialValue, language, onChange }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const editorRef = useRef<MonacoNamespace>(null);
    /** path -> editor model */
    const modelsRef = useRef<Map<string, MonacoNamespace>>(new Map());
    /** path -> 视图状态（光标 / 滚动位置），切走时保存、切回时恢复 */
    const viewStatesRef = useRef<Map<string, MonacoNamespace>>(new Map());
    /** 回调可能随渲染变化，监听器只在 mount 时注册一次，经 ref 转发最新实现 */
    const onChangeRef = useRef(onChange);
    onChangeRef.current = onChange;

    const [state, setState] = useState<LoadState>(() => (typeof window !== "undefined" && window.monaco ? "ready" : "loading"));
    const [fallbackValue, setFallbackValue] = useState(initialValue);

    // 挂载：加载 Monaco 并创建编辑器（StrictMode 下的重复执行由 createdRef 防御）
    const createdRef = useRef(false);
    const disposedRef = useRef(false);
    useEffect(() => {
        if (createdRef.current) {
            return;
        }
        createdRef.current = true;
        loadMonaco().then(monaco => {
            // 加载期间组件可能已被卸载，此时不再创建任何资源
            if (disposedRef.current) {
                return;
            }
            const container = containerRef.current;
            if (!container) {
                return;
            }
            const model = monaco.editor.createModel(initialValue, language, monaco.Uri.parse("inmemory://workbench/" + path));
            modelsRef.current.set(path, model);
            model.onDidChangeContent(() => {
                onChangeRef.current(path, model.getValue());
            });
            editorRef.current = monaco.editor.create(container, {
                model,
                theme: "vs",
                automaticLayout: true,
                minimap: { enabled: false },
                folding: false,
                glyphMargin: false,
                fontSize: 12,
                lineHeight: 20,
                fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", Menlo, monospace",
                scrollBeyondLastLine: false,
                renderWhitespace: "selection",
                tabSize: 4,
            });
            setState("ready");
        }).catch(() => {
            setState("failed");
        });
        // initialValue / language 只在首次创建 model 时使用，后续变化由下方 effect 处理
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // 切换文件：保存旧视图状态 -> 取或建 model -> 恢复视图状态
    const currentPathRef = useRef(path);
    useEffect(() => {
        const monaco = window.monaco;
        const editor = editorRef.current;
        if (state !== "ready" || !monaco || !editor) {
            currentPathRef.current = path;
            return;
        }
        const previous = currentPathRef.current;
        if (previous !== path) {
            const previousViewState = editor.saveViewState();
            if (previousViewState) {
                viewStatesRef.current.set(previous, previousViewState);
            }
        }
        let model = modelsRef.current.get(path);
        if (!model) {
            // language 是页面算好的「显式选择或按扩展名推断」结果，直接采用
            model = monaco.editor.createModel(
                initialValue,
                language,
                monaco.Uri.parse("inmemory://workbench/" + path)
            );
            model.onDidChangeContent(() => {
                onChangeRef.current(path, model.getValue());
            });
            modelsRef.current.set(path, model);
        }
        editor.setModel(model);
        const viewState = viewStatesRef.current.get(path);
        if (viewState) {
            editor.restoreViewState(viewState);
        }
        editor.focus();
        currentPathRef.current = path;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [path, state]);

    // 语言变化：对当前 model 应用新的语言 id
    useEffect(() => {
        const monaco = window.monaco;
        const editor = editorRef.current;
        if (state === "ready" && monaco && editor) {
            const model = editor.getModel();
            if (model) {
                monaco.editor.setModelLanguage(model, language);
            }
        }
    }, [language, state]);

    // 卸载：释放编辑器与所有 model（map 的引用在 effect 内固定，供 cleanup 使用）
    useEffect(() => {
        const models = modelsRef.current;
        return () => {
            disposedRef.current = true;
            const editor = editorRef.current;
            if (editor) {
                editor.dispose();
                editorRef.current = null;
            }
            models.forEach(model => model.dispose());
            models.clear();
        };
    }, []);

    if (state === "failed") {
        // 资源加载失败时退化为纯文本框，至少可以继续编辑代码
        return (
            <textarea
                style={FallbackStyle}
                value={fallbackValue}
                spellCheck={false}
                wrap="off"
                onChange={event => {
                    setFallbackValue(event.target.value);
                    onChange(path, event.target.value);
                }}/>
        );
    }

    return (
        <div className="code-editor-host" ref={containerRef}>
            {state === "loading" && <div className="code-editor-loading">编辑器加载中…</div>}
        </div>
    );
}
