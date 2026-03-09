#!/usr/bin/env python3
import argparse
import json

TEMPLATES = {
    "codex": "[CODEx IMPLEMENTATION]\n任务：{goal}\n当前阶段：{phase}\n指令：{instruction}",
    "gemini": "[GEMINI EXPRESSION]\n任务：{goal}\n当前阶段：{phase}\n指令：{instruction}",
    "claude-code": "[CLAUDE REVIEW]\n任务：{goal}\n当前阶段：{phase}\n指令：{instruction}",
    "oracle": "[ORACLE SECOND OPINION]\n任务：{goal}\n当前阶段：{phase}\n指令：{instruction}",
    "qwen": "[QWEN CN REVIEW]\n任务：{goal}\n当前阶段：{phase}\n指令：{instruction}",
    "main": "[MAIN ORCHESTRATION]\n任务：{goal}\n当前阶段：{phase}\n指令：{instruction}",
}


def main():
    parser = argparse.ArgumentParser(description="render agent-specific dispatch prompt skeleton")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--instruction", required=True)
    args = parser.parse_args()

    tmpl = TEMPLATES.get(args.agent, TEMPLATES["main"])
    prompt = tmpl.format(goal=args.goal, phase=args.phase, instruction=args.instruction)
    print(json.dumps({"agent": args.agent, "prompt": prompt}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
