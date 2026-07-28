#!/usr/bin/env python3
"""Playbook 分类登记与派生内容生成器。

单一真源是每个 `playbook-*.md` 的 frontmatter（`category` 与 `source` 字段）。
仓库里所有"数量"类文字都由本脚本据此派生，避免新增 Playbook 时漏改：

* `references/playbook-index.md` 的登记摘要句（总数 / 上游数 / 本地数）
* `README.md` 的分类统计表（数量列；说明列由人维护，会被保留）
* `README.md` 中 `### ... 分类名（N）` 形式的小节计数
* `README.md` 正文里"N 个专项 Playbook"一类的总数表述

用法：

    python tests/playbook_registry.py --check    # CI 默认，只比对不写入
    python tests/playbook_registry.py --write    # 重新生成派生内容
    python tests/playbook_registry.py --json     # 输出机器可读的登记快照

仅使用标准库，与 validate_skill.py 保持同一依赖约束。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "computer-repair-skill"
REFERENCES_DIR = SKILL_DIR / "references"
INDEX_PATH = REFERENCES_DIR / "playbook-index.md"
README_PATH = REPO_ROOT / "README.md"

EXCLUDED_PLAYBOOKS = {"playbook-authoring.md", "playbook-index.md"}

# 分类 slug -> (索引章节标题, README 表格显示名)
# 顺序即索引与 README 中的呈现顺序。新增分类时只在这里登记一次。
CATEGORIES: list[tuple[str, str, str]] = [
    ("health-performance-storage-backup", "健康、性能、存储与备份", "健康、性能、存储与备份"),
    ("hardware-crash-diagnostics", "硬件健康与崩溃分析", "硬件健康与崩溃分析"),
    ("network-identity-email", "网络、DNS、VPN、身份与邮件", "网络、DNS、VPN、身份与邮件"),
    ("apps-updates-printing", "应用、系统更新与打印", "应用、系统更新与打印"),
    ("peripherals-display", "外设、蓝牙与显示", "外设、蓝牙与显示"),
    ("windows-repair-boot-hardware", "Windows 维修、启动与硬件", "Windows 维修、启动与硬件"),
    ("windows-data-recovery", "Windows 数据恢复", "Windows 数据恢复"),
    ("macos-linux-repair", "macOS 与 Linux 维修", "macOS 与 Linux 维修"),
    ("security-credentials", "安全与凭据", "安全与凭据"),
    ("incident-response", "安全事件响应", "安全事件响应"),
    ("dev-environment-setup", "开发环境与基础设置", "开发环境与基础设置"),
    ("openclaw", "OpenClaw", "OpenClaw"),
]

CATEGORY_SLUGS = [slug for slug, _, _ in CATEGORIES]
CATEGORY_HEADINGS = {slug: heading for slug, heading, _ in CATEGORIES}
CATEGORY_LABELS = {slug: label for slug, _, label in CATEGORIES}
HEADING_TO_SLUG = {heading: slug for slug, heading, _ in CATEGORIES}
LABEL_TO_SLUG = {label: slug for slug, _, label in CATEGORIES}

MARKER = "<!-- registry:{state}:{key} -->"
TABLE_ROW = re.compile(
    r"^\|\s*(?P<label>[^|]+?)\s*\|\s*(?P<count>\*{0,2}\d+\*{0,2})\s*\|\s*(?P<note>.*?)\s*\|$"
)
# README 小节计数：`### 🩺 健康、性能、存储与备份（15）`
# 行尾只允许空格/制表符（不能用 `\s*`，否则在 re.M 下会吞掉标题后的空行）。
SECTION_COUNT = re.compile(r"(?m)^(?P<prefix>###[ \t]+)(?P<title>[^\n]*?)（(?P<count>\d+)）[ \t]*$")
# README 正文总数：`58 个专项 Playbook` / `58 个可按需加载的专项 Playbook` / `58 个 Playbook`
PROSE_TOTAL = re.compile(r"(?<![0-9])\d+(?=\s*个(?:可按需加载的)?(?:专项)?\s*Playbook)")


class RegistryError(RuntimeError):
    """登记数据本身不可用时抛出，调用方据此给出非零退出码。"""


def parse_frontmatter(path: Path) -> dict[str, str]:
    """解析单层 YAML frontmatter，行为与 validate_skill.py 保持一致。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise RegistryError(f"缺少 frontmatter：{path.name}")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise RegistryError(f"frontmatter 未闭合：{path.name}") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata


def find_playbooks() -> list[Path]:
    """返回可执行 Playbook，排除索引与编写规范。"""
    return sorted(
        path for path in REFERENCES_DIR.glob("playbook-*.md") if path.name not in EXCLUDED_PLAYBOOKS
    )


def collect() -> dict[str, object]:
    """从 frontmatter 汇总登记快照，供生成与校验共用。"""
    entries = []
    for path in find_playbooks():
        metadata = parse_frontmatter(path)
        entries.append(
            {
                "file": path.name,
                "name": metadata.get("name", ""),
                "platform": metadata.get("platform", ""),
                "category": metadata.get("category", ""),
                "source": metadata.get("source", ""),
                "last_reviewed": metadata.get("last_reviewed", ""),
            }
        )

    counts: dict[str, int] = dict.fromkeys(CATEGORY_SLUGS, 0)
    unknown: list[str] = []
    for entry in entries:
        category = str(entry["category"])
        if category in counts:
            counts[category] += 1
        else:
            unknown.append(f"{entry['file']} -> {category or '(缺失)'}")

    return {
        "total": len(entries),
        "bundled": sum(1 for entry in entries if entry["source"] == "bundled"),
        "local": sum(1 for entry in entries if entry["source"] == "local"),
        "counts": counts,
        "unknown": unknown,
        "entries": entries,
    }


def render_index_summary(snapshot: dict[str, object]) -> str:
    """索引开头的登记摘要句。"""
    return (
        f"本索引登记 {snapshot['total']} 个可执行 Playbook："
        f"{snapshot['bundled']} 个来自 `NOTICE` 记录的上游基准，"
        f"{snapshot['local']} 个由本项目补充，用于覆盖 Windows、macOS 和 Linux 的网络、"
        "性能、存储、安全、启动、硬件、崩溃分析、事件响应和恢复诊断。"
    )


def render_readme_table(snapshot: dict[str, object], existing: str) -> str:
    """重算数量列，保留人工维护的说明列。"""
    counts = snapshot["counts"]
    assert isinstance(counts, dict)

    notes: dict[str, str] = {}
    for line in existing.splitlines():
        match = TABLE_ROW.match(line.strip())
        if not match:
            continue
        label = match.group("label").strip().strip("*")
        if label in LABEL_TO_SLUG:
            notes[LABEL_TO_SLUG[label]] = match.group("note")

    rows = ["| 分类 | 数量 | 主要内容 |", "|---|---|---|"]
    for slug in CATEGORY_SLUGS:
        count = counts.get(slug, 0)
        if not count:
            continue
        note = notes.get(slug) or f"{CATEGORY_HEADINGS[slug]}相关流程"
        rows.append(f"| {CATEGORY_LABELS[slug]} | {count} | {note} |")
    rows.append(f"| **合计** | **{snapshot['total']}** | 可执行 Playbook 总数 |")
    return "\n".join(rows)


def extract_block(text: str, key: str, path: Path) -> str:
    """取出标记之间的现有内容。"""
    begin = MARKER.format(state="begin", key=key)
    end = MARKER.format(state="end", key=key)
    pattern = re.compile(re.escape(begin) + r"\r?\n(.*?)" + re.escape(end), re.DOTALL)
    match = pattern.search(text)
    if not match:
        raise RegistryError(f"{path.name} 缺少 registry 标记：{key}")
    return match.group(1)


def replace_block(text: str, key: str, payload: str, path: Path) -> str:
    """替换标记之间的内容；标记缺失时报错而不是静默追加。"""
    begin = MARKER.format(state="begin", key=key)
    end = MARKER.format(state="end", key=key)
    pattern = re.compile(re.escape(begin) + r"\r?\n.*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise RegistryError(f"{path.name} 缺少 registry 标记：{key}")
    return pattern.sub(lambda _: f"{begin}\n{payload}\n{end}", text)


def rewrite_readme(text: str, snapshot: dict[str, object]) -> str:
    """更新 README 的分类表、小节计数和正文总数。"""
    counts = snapshot["counts"]
    assert isinstance(counts, dict)

    existing = extract_block(text, "category-table", README_PATH)
    text = replace_block(text, "category-table", render_readme_table(snapshot, existing), README_PATH)

    def fix_section(match: re.Match[str]) -> str:
        # 标题形如 `### 🩺 健康、性能、存储与备份（15）`：先整体匹配，再剥掉可选的 emoji 前缀，
        # 这样正则不必贪婪跨行，也不会误改与分类无关的带括号标题。
        title = match.group("title").strip()
        candidates = [title]
        _, _, tail = title.partition(" ")
        if tail.strip():
            candidates.append(tail.strip())
        for candidate in candidates:
            slug = LABEL_TO_SLUG.get(candidate) or HEADING_TO_SLUG.get(candidate)
            if slug is not None:
                return f"{match.group('prefix')}{title}（{counts.get(slug, 0)}）"
        return match.group(0)

    text = SECTION_COUNT.sub(fix_section, text)
    return PROSE_TOTAL.sub(str(snapshot["total"]), text)


def run(mode: str) -> int:
    """按模式执行生成、比对或快照输出。"""
    snapshot = collect()

    if snapshot["unknown"]:
        print("以下 Playbook 的 category 未登记（请在 CATEGORIES 中登记或修正 frontmatter）：")
        for item in snapshot["unknown"]:  # type: ignore[union-attr]
            print(f"  - {item}")
        return 1

    if mode == "json":
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    index_text = INDEX_PATH.read_text(encoding="utf-8")
    readme_text = README_PATH.read_text(encoding="utf-8")
    updates = [
        (
            INDEX_PATH,
            index_text,
            replace_block(index_text, "index-summary", render_index_summary(snapshot), INDEX_PATH),
        ),
        (README_PATH, readme_text, rewrite_readme(readme_text, snapshot)),
    ]

    drift: list[str] = []
    for path, original, updated in updates:
        if original == updated:
            continue
        if mode == "write":
            path.write_text(updated, encoding="utf-8", newline="\n")
            print(f"已更新：{path.relative_to(REPO_ROOT)}")
        else:
            drift.append(str(path.relative_to(REPO_ROOT)))

    if drift:
        print("派生内容与 frontmatter 不一致，请运行 python tests/playbook_registry.py --write：")
        for item in drift:
            print(f"  - {item}")
        return 1

    counts = snapshot["counts"]
    assert isinstance(counts, dict)
    active = sum(1 for value in counts.values() if value)
    print(
        f"登记一致：{snapshot['total']} 个 Playbook，{active} 个分类，"
        f"{snapshot['bundled']} 上游 / {snapshot['local']} 本地。"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """命令行入口。默认 --check，便于直接用于 CI。"""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="只比对派生内容，不写入（默认）")
    group.add_argument("--write", action="store_true", help="重新生成派生内容")
    group.add_argument("--json", action="store_true", help="输出登记快照 JSON")
    args = parser.parse_args(argv)

    mode = "write" if args.write else "json" if args.json else "check"
    try:
        return run(mode)
    except RegistryError as exc:
        print(f"登记生成失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
