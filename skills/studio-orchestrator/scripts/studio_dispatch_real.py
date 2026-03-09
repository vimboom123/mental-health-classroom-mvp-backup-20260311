#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
OUT_DIR = os.path.join(WORKSPACE, 'tmp', 'studio-dispatch')
os.makedirs(OUT_DIR, exist_ok=True)


def now_slug():
    return datetime.now(timezone.utc).astimezone().strftime('%Y%m%d-%H%M%S')


def main():
    parser = argparse.ArgumentParser(description='run real local wrapper for a dispatch item when supported')
    parser.add_argument('--agent', required=True)
    parser.add_argument('--goal', required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--instruction', required=True)
    args = parser.parse_args()

    slug = now_slug()
    out_path = os.path.join(OUT_DIR, f'{args.agent}-{slug}.txt')
    prompt = f"任务：{args.goal}\n阶段：{args.phase}\n要求：{args.instruction}\n请给出结构化审阅或执行建议。"

    if args.agent == 'oracle':
        cmd = ['bash', '-lc', f'cd {WORKSPACE} && scripts/oracle-browser-auto.sh --prompt {json.dumps(prompt)} > {json.dumps(out_path)} 2>&1 || true']
        mode = 'oracle-wrapper'
    elif args.agent == 'qwen':
        cmd = ['bash', '-lc', f'cd {WORKSPACE} && scripts/qwen_review.sh {json.dumps(prompt)} > {json.dumps(out_path)} 2>&1 || true']
        mode = 'qwen-wrapper'
    elif args.agent == 'gemini':
        cmd = ['bash', '-lc', f'cd {WORKSPACE} && scripts/gemini22.sh {json.dumps(prompt)} > {json.dumps(out_path)} 2>&1 || true']
        mode = 'gemini-wrapper'
    else:
        print(json.dumps({'supported': False, 'agent': args.agent}, ensure_ascii=False, indent=2))
        return

    subprocess.run(cmd, check=False)
    print(json.dumps({'supported': True, 'agent': args.agent, 'mode': mode, 'output_path': out_path}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
