import React from "react";

/**
 * 轻量 Markdown 渲染：只处理题面里常用的语法，避免引入额外依赖。
 *
 * 支持：标题（# ~ #####）、粗体 **text**、行内代码 `code`、代码块 ```、有序/无序列表。
 * 所有文本都通过 React 元素渲染，用户内容不会被当作 HTML 执行。
 */

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
    const nodes: React.ReactNode[] = [];
    const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let lastIndex = 0;
    let index = 0;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(text)) !== null) {
        if (match.index > lastIndex) {
            nodes.push(text.slice(lastIndex, match.index));
        }
        const token = match[0];
        if (token.startsWith("**")) {
            nodes.push(<strong key={`${keyPrefix}-b-${index}`}>{token.slice(2, -2)}</strong>);
        } else {
            nodes.push(<code key={`${keyPrefix}-c-${index}`}>{token.slice(1, -1)}</code>);
        }
        lastIndex = pattern.lastIndex;
        index += 1;
    }
    if (lastIndex < text.length) {
        nodes.push(text.slice(lastIndex));
    }
    return nodes;
}

const headingStyle: Record<number, React.CSSProperties> = {
    1: { fontSize: 18, margin: "4px 0 10px" },
    2: { fontSize: 16, margin: "14px 0 8px" },
    3: { fontSize: 14, margin: "14px 0 8px" },
    4: { fontSize: 13, margin: "12px 0 6px" },
    5: { fontSize: 12, margin: "10px 0 6px" },
    6: { fontSize: 12, margin: "10px 0 6px" },
};

export interface MarkdownTextProps {
    text: string;
}

export function MarkdownText({ text }: MarkdownTextProps) {
    const lines = str(text).split(/\r?\n/);
    const nodes: React.ReactNode[] = [];
    let index = 0;
    let key = 0;

    const flushParagraph = (paragraph: string[]) => {
        if (paragraph.length === 0) {
            return;
        }
        nodes.push(
            <p key={`p-${key}`} style={{ margin: "0 0 9px", whiteSpace: "pre-wrap" }}>
                {renderInline(paragraph.join("\n"), `p-${key}`)}
            </p>
        );
        key += 1;
    };

    while (index < lines.length) {
        const line = lines[index];

        if (!line.trim()) {
            index += 1;
            continue;
        }

        const heading = line.match(/^(#{1,6})\s+(.*)$/);
        if (heading) {
            const level = heading[1].length;
            const Tag = (`h${level}`) as keyof JSX.IntrinsicElements;
            nodes.push(
                React.createElement(
                    Tag,
                    { key: `h-${key}`, style: { ...headingStyle[level], color: "#0f172a", fontWeight: 700 } },
                    renderInline(heading[2], `h-${key}`)
                )
            );
            key += 1;
            index += 1;
            continue;
        }

        if (line.trim().startsWith("```")) {
            const codeLines: string[] = [];
            index += 1;
            while (index < lines.length && !lines[index].trim().startsWith("```")) {
                codeLines.push(lines[index]);
                index += 1;
            }
            index += 1;
            nodes.push(
                <pre key={`code-${key}`}
                     style={{
                         margin: "6px 0 10px",
                         padding: "8px 10px",
                         background: "#f8fafc",
                         border: "1px solid #e2e8f0",
                         borderRadius: 6,
                         fontFamily: "\"SFMono-Regular\", Consolas, Menlo, monospace",
                         fontSize: 11,
                         lineHeight: 1.6,
                         whiteSpace: "pre-wrap",
                         overflowX: "auto",
                     }}>
                    {codeLines.join("\n")}
                </pre>
            );
            key += 1;
            continue;
        }

        const unordered = line.match(/^\s*[-*]\s+(.*)$/);
        const ordered = line.match(/^\s*\d+\.\s+(.*)$/);
        if (unordered || ordered) {
            const orderedList = !!ordered;
            const items: string[] = [];
            while (index < lines.length) {
                const current = lines[index];
                const match = orderedList
                    ? current.match(/^\s*\d+\.\s+(.*)$/)
                    : current.match(/^\s*[-*]\s+(.*)$/);
                if (!match) {
                    break;
                }
                items.push(match[1]);
                index += 1;
            }
            const ListTag = orderedList ? "ol" : "ul";
            nodes.push(
                React.createElement(
                    ListTag,
                    { key: `list-${key}`, style: { margin: "2px 0 10px", paddingLeft: 20 } },
                    items.map((item, itemIndex) => (
                        <li key={`li-${key}-${itemIndex}`} style={{ marginBottom: 3 }}>
                            {renderInline(item, `li-${key}-${itemIndex}`)}
                        </li>
                    ))
                )
            );
            key += 1;
            continue;
        }

        // 普通段落：收集到空行或下一个块为止
        const paragraph: string[] = [];
        while (index < lines.length && lines[index].trim()) {
            const current = lines[index];
            if (paragraph.length > 0 && (
                /^#{1,6}\s+/.test(current) ||
                /^\s*[-*]\s+/.test(current) ||
                /^\s*\d+\.\s+/.test(current) ||
                current.trim().startsWith("```")
            )) {
                break;
            }
            paragraph.push(current);
            index += 1;
        }
        flushParagraph(paragraph);
    }

    return <div className="md-body">{nodes}</div>;
}

function str(value: string | null | undefined): string {
    return String(value || "");
}
