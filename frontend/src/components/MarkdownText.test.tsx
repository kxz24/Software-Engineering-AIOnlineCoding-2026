import React from "react";
import ReactDOM from "react-dom";
import { MarkdownText } from "./MarkdownText";

describe("MarkdownText", () => {
    const render = (text: string) => {
        const container = document.createElement("div");
        ReactDOM.render(<MarkdownText text={text}/>, container);
        const html = container.innerHTML;
        ReactDOM.unmountComponentAtNode(container);
        return html;
    };

    it("渲染标题、粗体与行内代码，而不是原样输出 Markdown", () => {
        const html = render(
            "### 题目描述\n\n读入 `n` 个整数，把它们按**从大到小**排序后输出。"
        );
        expect(html).not.toContain("###");
        expect(html).toContain("<h3");
        expect(html).toContain("<code>n</code>");
        expect(html).toContain("<strong>从大到小</strong>");
    });

    it("渲染代码块与列表", () => {
        const html = render("- 第一项\n- 第二项\n\n```python\nprint(1)\n```");
        expect(html).toContain("<ul");
        expect(html).toContain("<li");
        expect(html).toContain("print(1)");
        expect(html).not.toContain("```");
    });

    it("空题面不抛异常", () => {
        const html = render("");
        expect(html.length).toBeGreaterThan(0);
    });
});
