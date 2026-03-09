#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PY = os.path.join(BASE_DIR, "scripts", "studio_report.py")


def main():
    parser = argparse.ArgumentParser(description="send reportable studio updates via OpenClaw messaging")
    parser.add_argument("--task-id")
    parser.add_argument("--target", required=True)
    parser.add_argument("--channel", default="telegram")
    parser.add_argument("--min-interval", type=int, default=1800)
    args = parser.parse_args()

    cmd = [sys.executable, REPORT_PY, "--json", "--mark-reported", "--min-interval", str(args.min_interval)]
    if args.task_id:
        cmd.extend(["--task-id", args.task_id])
    payloads = json.loads(subprocess.check_output(cmd, text=True))

    for item in payloads:
        subprocess.run([
            "/Users/vimboom/.npm-global/bin/openclaw",
            "message",
            "send",
            "--channel", args.channel,
            "--target", args.target,
            "--message", item["text"],
        ], check=True)

    print(json.dumps({"sent": len(payloads), "channel": args.channel, "target": args.target}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
