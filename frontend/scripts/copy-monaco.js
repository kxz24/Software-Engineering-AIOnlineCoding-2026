/*
 * 把 monaco-editor 的运行时资源（min/vs）复制到 public/monaco-vs，
 * 页面以本地静态资源的方式加载 Monaco（scripts 在线 CDN 在内网 / 弱网下不可靠）。
 *
 * 资源体积较大（约 4MB），public/monaco-vs 已加入 .gitignore，
 * clone 后执行 npm install 时由本脚本自动生成，无需提交进仓库。
 */
const fs = require("fs");
const path = require("path");

const source = path.join(__dirname, "..", "node_modules", "monaco-editor", "min", "vs");
const target = path.join(__dirname, "..", "public", "monaco-vs");

function copyDir(from, to) {
    fs.mkdirSync(to, { recursive: true });
    for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
        // min-maps 是 sourcemap，不需要进入构建产物
        if (entry.name === "min-maps") {
            continue;
        }
        const src = path.join(from, entry.name);
        const dest = path.join(to, entry.name);
        if (entry.isDirectory()) {
            copyDir(src, dest);
        } else {
            fs.copyFileSync(src, dest);
        }
    }
}

if (!fs.existsSync(source)) {
    console.warn("[copy-monaco] 未找到 monaco-editor/min/vs，跳过复制（请确认已安装依赖）");
    process.exit(0);
}

copyDir(source, target);
console.log("[copy-monaco] public/monaco-vs 已就绪（Monaco 本地静态资源）");
