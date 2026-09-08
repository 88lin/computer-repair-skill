#!/usr/bin/env python3
"""从 SKILL.md 的 version 和 CHANGELOG.md 生成一次发布所需的元数据。

发布说明必须和仓库里的变更记录一致，所以这里只做“摘录”，不另写文案：

    python tools/release_notes.py --print-version          # 打印当前版本号
    python tools/release_notes.py --output notes.md         # 写出当前版本的发布说明
    python tools/release_notes.py --version 1.1.0 --output notes.md

CHANGELOG 里缺少对应版本条目时以非零退出码失败，避免发出一个正文为空的 Release。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "skills" / "computer-repair-skill" / "SKILL.md"
AGENT = REPO_ROOT / "skills" / "computer-repair-skill" / "agents" / "openai.yaml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
CHANGELOG_URL = "https://github.com/88lin/computer-repair-skill/blob/main/CHANGELOG.md"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_skill_version() -> str:
    """读取 SKILL.md frontmatter 的 version，并确认 Agent 元数据没有落后。"""
    lines = SKILL.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise SystemExit("SKILL.md 缺少 frontmatter。")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        raise SystemExit("SKILL.md 的 frontmatter 未闭合。") from None

    version = ""
    for line in lines[1:end]:
        if line.startswith("version:"):
            version = line.split(":", 1)[1].strip().strip("\"'")
            break
    if not SEMVER.match(version):
        raise SystemExit(f"SKILL.md 的 version 不是语义化版本：{version!r}")

    agent_text = AGENT.read_text(encoding="utf-8")
    agent_match = re.search(r'(?m)^version:\s*"?([\d.]+)"?', agent_text)
    agent_version = agent_match.group(1) if agent_match else ""
    if agent_version != version:
        raise SystemExit(
            f"版本号不一致：SKILL.md 是 {version}，agents/openai.yaml 是 {agent_version or '缺失'}。"
        )
    return version


def extract_section(version: str) -> tuple[str, str]:
    """取出 CHANGELOG 中该版本的日期和正文。"""
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        rf"(?ms)^## \[{re.escape(version)}\][^\n]*?(?:-\s*(\S+))?\n(.*?)(?=^## \[|\Z)",
        text,
    )
    if not match:
        raise SystemExit(
            f"CHANGELOG.md 缺少 {version} 的条目；请先补 '## [{version}] - YYYY-MM-DD' 再发布。"
        )
    body = match.group(2).strip()
    if not body:
        raise SystemExit(f"CHANGELOG.md 中 {version} 的条目为空，不发布空说明。")
    return match.group(1) or "", body


def build_notes(version: str, body: str) -> str:
    """拼出 Release 正文：先说明版本对应关系，再摘录变更，最后回链变更记录。"""
    return (
        f"对应 `SKILL.md` 与 `agents/openai.yaml` 的 `version: {version}`。\n\n"
        f"{body}\n\n"
        "---\n\n"
        f"完整变更记录见 [CHANGELOG.md]({CHANGELOG_URL})。\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="要发布的版本号，默认取 SKILL.md 的 version")
    parser.add_argument("--print-version", action="store_true", help="只打印版本号")
    parser.add_argument("--output", type=Path, help="发布说明的输出路径")
    args = parser.parse_args()

    version = args.version or read_skill_version()
    if args.print_version:
        print(version)
        return 0

    _, body = extract_section(version)
    notes = build_notes(version, body)
    if args.output:
        args.output.write_text(notes, encoding="utf-8")
        print(f"已写出 {version} 的发布说明：{args.output}")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
