/**
 * 04 做题工作台的演示数据。
 *
 * 沙箱、判题与 Agent 服务尚未接入，工作区文件、时间线、终端输出和 Agent 会话
 * 先在前端集中放在这里，保证页面结构、文案与原型逐行一致；接口就绪后按块替换。
 */

/** 工作区条目的类型：目录只占一行，文件带可编辑内容 */
export type WorkspaceKind = "folder" | "file";

export interface WorkspaceEntry {
    /** 目录或文件在项目中的路径，同时用作 React key */
    path: string;
    name: string;
    kind: WorkspaceKind;
    /** 缩进层级：1 项目根目录、2 顶层文件 / 子目录、3 子目录内文件 */
    depth: 1 | 2 | 3;
}

/** 左侧文件树（原型 exam-project 的结构） */
export const WorkspaceEntries: WorkspaceEntry[] = [
    { path: "exam-project", name: "exam-project", kind: "folder", depth: 1 },
    { path: "src", name: "src", kind: "folder", depth: 2 },
    { path: "src/buggy_sort.py", name: "buggy_sort.py", kind: "file", depth: 3 },
    { path: "src/utils.py", name: "utils.py", kind: "file", depth: 3 },
    { path: "src/models.py", name: "models.py", kind: "file", depth: 3 },
    { path: "tests", name: "tests", kind: "folder", depth: 2 },
    { path: "tests/test_sort.py", name: "test_sort.py", kind: "file", depth: 3 },
    { path: "tests/conftest.py", name: "conftest.py", kind: "file", depth: 3 },
    { path: "README.md", name: "README.md", kind: "file", depth: 2 },
    { path: "pyproject.toml", name: "pyproject.toml", kind: "file", depth: 2 },
    { path: "requirements.txt", name: "requirements.txt", kind: "file", depth: 2 },
];

/** 各文件的初始内容，与原型编辑器里展示的代码一致 */
export const WorkspaceFiles: Record<string, string> = {
    "src/buggy_sort.py": [
        "from dataclasses import dataclass",
        "",
        "@dataclass",
        "class Order:",
        "    order_id: str",
        "    amount: float",
        "    created_at: str",
        "",
        "def sort_orders(orders, key=\"amount\", reverse=False):",
        "    if key == \"amount\":",
        "        # 金额并列时依赖输入顺序，结果不稳定",
        "        return sorted(orders, key=lambda o: o.amount, reverse=reverse)",
        "    if key == \"created_at\":",
        "        return sorted(orders, key=lambda o: o.created_at, reverse=reverse)",
        "    raise ValueError(f\"unsupported key: {key}\")",
    ].join("\n"),
    "src/utils.py": [
        "from datetime import datetime",
        "",
        "",
        "def parse_time(raw: str) -> datetime:",
        "    \"\"\"兼容 ISO 与空格两种时间格式，供排序键使用。\"\"\"",
        "    return datetime.fromisoformat(raw.replace(\" \", \"T\"))",
        "",
        "",
        "def format_amount(amount: float) -> str:",
        "    return f\"{amount:.2f}\"",
    ].join("\n"),
    "src/models.py": [
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass",
        "class Order:",
        "    order_id: str",
        "    amount: float",
        "    created_at: str",
        "",
        "",
        "@dataclass",
        "class ImportResult:",
        "    total: int",
        "    failed: int",
    ].join("\n"),
    "tests/test_sort.py": [
        "from src.buggy_sort import Order, sort_orders",
        "",
        "",
        "def test_sort_basic():",
        "    orders = [Order(\"A-1002\", 20.0, \"2026-10-01T09:02\"),",
        "              Order(\"A-1001\", 10.0, \"2026-10-01T09:01\")]",
        "    assert [o.order_id for o in sort_orders(orders)] == [\"A-1001\", \"A-1002\"]",
        "",
        "",
        "def test_sort_ties_by_created_at():",
        "    orders = [Order(\"A-1003\", 99.0, \"2026-10-01T09:05\"),",
        "              Order(\"A-1001\", 99.0, \"2026-10-01T09:00\")]",
        "    assert [o.order_id for o in sort_orders(orders)] == [\"A-1001\", \"A-1003\"]",
    ].join("\n"),
    "tests/conftest.py": [
        "import pytest",
        "",
        "from src.models import Order",
        "",
        "",
        "@pytest.fixture",
        "def sample_orders():",
        "    return [",
        "        Order(\"A-1001\", 99.0, \"2026-10-01T09:00\"),",
        "        Order(\"A-1003\", 99.0, \"2026-10-01T09:05\"),",
        "    ]",
    ].join("\n"),
    "README.md": [
        "# exam-project",
        "",
        "订单导入与排序示例工程。",
        "",
        "## 运行测试",
        "",
        "    pytest -q tests/test_sort.py",
        "",
        "## 任务",
        "",
        "修复 `src/buggy_sort.py` 中金额并列时的排序稳定性问题。",
    ].join("\n"),
    "pyproject.toml": [
        "[tool.pytest.ini_options]",
        "testpaths = [\"tests\"]",
        "addopts = \"-q\"",
    ].join("\n"),
    "requirements.txt": [
        "pytest==8.3.2",
    ].join("\n"),
};

/** 原型里默认打开的编辑器标签 */
export const DefaultOpenPaths: string[] = ["src/buggy_sort.py", "src/utils.py"];

/** 原型里 buggy_sort.py 自带「未保存」标记，其余文件初始为已保存 */
export const DefaultModifiedPaths: Record<string, boolean> = {
    "src/buggy_sort.py": true,
};

/** 剩余作答秒数：原型顶部倒计时 01:27:34 */
export const RemainingSeconds = 1 * 3600 + 27 * 60 + 34;

/** 按路径取文件名，供编辑器标签展示 */
export function workspaceFileName(path: string): string {
    const entry = WorkspaceEntries.find(item => item.path === path);
    return entry ? entry.name : path;
}

/** 左侧时间线（原型 3 条） */
export const TimelineItems: { text: string; time: string; tone: "" | "blue" | "red" }[] = [
    { text: "自动保存 · 快照 #18", time: "14:32:05", tone: "blue" },
    { text: "运行样例测试 · 8 / 10 通过", time: "14:28:41", tone: "red" },
    { text: "开始作答 · 容器已就绪", time: "13:55:12", tone: "" },
];

/** 终端里的一行输出，按片段着色（对应原型 term-* 类名） */
export type TerminalTone = "prompt" | "ok" | "fail" | "muted" | "dim";

export interface TerminalSegment {
    text: string;
    tone?: TerminalTone;
}

export const TerminalLines: TerminalSegment[][] = [
    [
        { text: "$", tone: "prompt" },
        { text: " pytest -q tests/test_sort.py", tone: "muted" },
    ],
    [
        { text: ".F.......F", tone: "dim" },
        { text: "                                             [100%]", tone: "dim" },
    ],
    [
        { text: "FAILED", tone: "fail" },
        { text: " tests/test_sort.py::test_sort_ties_by_created_at", tone: "muted" },
    ],
    [
        { text: "  AssertionError: expected ['A-1001', 'A-1003'], got ['A-1003', 'A-1001']", tone: "muted" },
    ],
    [
        { text: "FAILED", tone: "fail" },
        { text: " tests/test_sort.py::test_sort_created_at_iso_format", tone: "muted" },
    ],
    [
        { text: "  ValueError: Invalid isoformat string: '2026-10-01 09:00'", tone: "muted" },
    ],
    [
        { text: "2 failed", tone: "fail" },
        { text: ", ", tone: "muted" },
        { text: "8 passed", tone: "ok" },
        { text: " in 1.42s", tone: "muted" },
    ],
];

/** 顶部「样例测试」标签的只读摘要（原型未展开该面板，切过去给出与终端一致的信息） */
export const SampleTabNotes: { label: string; text: string }[] = [
    { label: "样例测试：", text: "共 10 条，最近一次运行 8 通过 / 2 失败（1.42s）" },
    { label: "失败用例：", text: "test_sort_ties_by_created_at、test_sort_created_at_iso_format" },
    { label: "运行命令：", text: "pytest -q tests/test_sort.py" },
];

/** 顶部「提交记录」标签的只读摘要 */
export const SubmissionTabNotes: { label: string; text: string }[] = [
    { label: "提交 #1：", text: "14:28:41 · 样例 8 / 10 通过 · 未判分" },
    { label: "剩余次数：", text: "2 次（提交后立即判分，不可撤回）" },
];

/** 右侧 Agent 会话消息：用户气泡 / Agent 卡片两种形态 */
export type AgentMessage =
    | { id: string; role: "user"; text: string }
    | {
        id: string;
        role: "agent";
        /** diff：带红绿改动建议；code：带代码块；plain：纯文字（模拟回复用） */
        variant: "diff" | "code" | "plain";
        time: string;
        /** 段落文案，内部用 `反引号` 标记行内代码 */
        paragraphs: string[];
        code?: string;
    };

/** Agent 首屏会话，与原型的两轮问答一致 */
export const AgentMessages: AgentMessage[] = [
    {
        id: "msg-1",
        role: "user",
        text: "排序结果里金额相同的订单顺序不稳定。帮我定位原因，先只解释，不要改代码。",
    },
    {
        id: "msg-2",
        role: "agent",
        variant: "diff",
        time: "14:30:12",
        paragraphs: [
            "原因 1：只按 `amount` 排序，金额并列时依赖 CSV 的输入顺序。",
            "原因 2：`created_at` 按字符串比较，ISO 与空格格式混用会出错。",
            "建议：排序键改为 `(amount, parse_time(created_at))`，并统一时间解析。",
        ],
    },
    {
        id: "msg-3",
        role: "user",
        text: "@tests/test_sort.py 帮我补一个金额并列的边界用例，并说明断言思路。",
    },
    {
        id: "msg-4",
        role: "agent",
        variant: "code",
        time: "14:31:40",
        paragraphs: [
            "建议新增用例（断言思路：固定并列项的期望顺序，不依赖输入顺序）：",
        ],
        code: [
            "def test_ties_by_created_at():",
            "    orders = [Order(\"A-1003\", 99.0, \"09:05\"),",
            "              Order(\"A-1001\", 99.0, \"09:00\")]",
            "    ids = [o.order_id for o in sort_orders(orders)]",
            "    assert ids == [\"A-1001\", \"A-1003\"]",
        ].join("\n"),
    },
];

/** Agent 输入框占位文案 */
export const AgentPlaceholder = "向 Agent 提问，输入 @ 引用工作区文件…";

/** 模拟的 Agent 回复，按发送次数轮换，仅用于演示本地会话追加 */
export const CannedReplies: string[] = [
    "已收到。受限模式下我只给思路：先把并列项的比较键补齐，再补一条并列用例验证顺序。",
    "这条提问已记入过程报告。需要我继续解释 `sort_orders` 的复杂度，还是补一条边界用例？",
    "建议先运行 `pytest -q tests/test_sort.py` 确认失败用例，再逐条定位，避免改动无关代码。",
];

const Pad = (value: number): string => String(value).padStart(2, "0");

/** 当前时刻的 HH:MM:SS，用于新消息时间戳 */
export function formatClock(now: Date): string {
    return `${Pad(now.getHours())}:${Pad(now.getMinutes())}:${Pad(now.getSeconds())}`;
}
