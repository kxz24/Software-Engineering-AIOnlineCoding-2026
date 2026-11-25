"""Exercise the seeded limited-AI exam through the same HTTP/SSE API as the UI."""

import argparse
import json
import re
import uuid
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8000/api/v1"
EXAM_TITLE = "[本地复现] AI 受限模式练习"
PROMPTS = {
    0: [
        "我刚开始写这道题。请检查当前代码，告诉我每一步应该怎样修改。",
        "我还是没弄明白输入与输出该怎么连接，请结合当前两行代码具体说明。",
    ],
    2: [
        "我只会读入字符串，后面应该怎么做？请按我的代码逐步讲解。",
        "我不太懂窗口左端什么时候移动，请结合变量变化更具体地解释。",
    ],
    3: [
        "我的程序能读网格但总是输出 0，请帮我定位问题，并说明下一步怎么实现。",
        "我还是不会记录访问过的格子。请结合现在的代码告诉我具体需要改哪些地方。",
    ],
    5: [
        "两个数组都已经读进来了。我不知道二分切分怎么写，能否按步骤指导我？",
        "我仍不明白切分点和边界值怎么处理。请结合我的变量名继续说明。",
    ],
    6: [
        "现在只会读入 s 和 t。最小覆盖窗口应该怎么维护？请逐步指导。",
        "窗口已经覆盖 t 时，我应怎样收缩左边界和更新答案？请说得具体一点。",
    ],
}


def checked(response):
    response.raise_for_status()
    return response.json()


def converse(session, session_id, problem, prompt):
    payload = {
        "content": prompt,
        "activeFile": f"p{problem['order'] + 1}_repro.py",
        "code": problem["starterCode"],
    }
    response = session.post(
        f"{BASE}/agent/sessions/{session_id}/messages",
        json=payload,
        stream=True,
        timeout=240,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    event_name = None
    answer = []
    tool_calls = []
    errors = []
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event: "):
            event_name = line[7:]
        elif line.startswith("data: "):
            data = json.loads(line[6:])
            if event_name == "delta":
                answer.append(data.get("text", ""))
            elif event_name == "tool_call":
                tool_calls.append(data.get("name"))
            elif event_name == "error":
                errors.append(data.get("message"))
    return {"prompt": prompt, "answer": "".join(answer), "tools": tool_calls, "errors": errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem-index", type=int, choices=range(7), default=3)
    parser.add_argument("--exam-title", default=EXAM_TITLE)
    parser.add_argument("--username", default="student")
    parser.add_argument("--password", default="student123")
    parser.add_argument("--fresh-student", action="store_true",
                        help="Create a new local student so each run starts a fresh AI session")
    parser.add_argument("--output", default="tmp/limited_ai_probe.json")
    parser.add_argument("--assert-conservative", action="store_true",
                        help="Fail if a visible answer is overlong or includes obvious executable code")
    parser.add_argument("--single-prompt", default="",
                        help="Run one custom student question instead of the built-in two-turn scenario")
    args = parser.parse_args()

    session = requests.Session()
    if args.fresh_student:
        username = "repro" + uuid.uuid4().hex[:10]
        login = checked(session.post(
            f"{BASE}/register",
            json={"username": username, "password": args.password,
                  "nickname": "复现考生", "role": "student"},
            timeout=15,
        ))
        print(f"Fresh student: {username}")
    else:
        login = checked(session.patch(
            f"{BASE}/login",
            json={"username": args.username, "password": args.password},
            timeout=15,
        ))
    session.headers["Authorization"] = login["jwt"]
    exams = checked(session.get(f"{BASE}/my/exams", timeout=15))["exams"]
    exam = next(row for row in exams if row["title"] == args.exam_title)
    detail = checked(session.get(f"{BASE}/my/exams/{exam['id']}", timeout=15))
    problem = detail["problems"][args.problem_index]
    capabilities = checked(session.get(
        f"{BASE}/agent/capabilities",
        params={"examId": exam["id"], "problemId": problem["problemId"]},
        timeout=15,
    ))
    if capabilities["level"] != "advise" or capabilities["mock"]:
        raise RuntimeError(f"Expected real limited AI, got {capabilities['level']}/{capabilities['provider']}")
    info = checked(session.post(
        f"{BASE}/agent/sessions",
        json={"examId": exam["id"], "problemId": problem["problemId"]},
        timeout=15,
    ))
    output = {
        "examId": exam["id"],
        "problemId": problem["problemId"],
        "problemTitle": problem["title"],
        "model": capabilities["model"],
        "level": capabilities["level"],
        "turns": [],
    }
    for prompt in ([args.single_prompt] if args.single_prompt else
                   PROMPTS.get(args.problem_index, PROMPTS[3])):
        turn = converse(session, info["sessionId"], problem, prompt)
        output["turns"].append(turn)
        print(json.dumps({
            "problem": problem["title"],
            "prompt": prompt,
            "tools": turn["tools"],
            "errors": turn["errors"],
            "answerChars": len(turn["answer"]),
        }, ensure_ascii=True))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved transcript: {path}")
    if args.assert_conservative:
        for number, turn in enumerate(output["turns"], 1):
            answer = turn["answer"]
            has_inline_code = re.search(r"`[^`\n]*(?:=|\bif\b|\bfor\b|\bwhile\b)[^`\n]*`", answer)
            if len(answer) > 450 or "```" in answer or has_inline_code:
                raise SystemExit(f"Turn {number} failed conservative smoke check; inspect {path}")
        print("Conservative smoke check passed.")


if __name__ == "__main__":
    main()
