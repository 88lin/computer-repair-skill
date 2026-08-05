#!/usr/bin/env python3
"""Generate the website playbook data from Markdown metadata and the current copy catalog.

The compressed JavaScript file remains a generated artifact. Its descriptive copy lives
in the explicit JSON catalog because those strings have no single Markdown source yet;
structural and review metadata always comes from the repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "computer-repair-skill" / "references"
OUTPUT = ROOT / "docs" / "assets" / "js" / "playbooks.js"
CATALOG = ROOT / "tools" / "site_catalog.json"
INDEX = REFERENCES / "playbook-index.md"
INDEX_SECTION = re.compile(r"(?ms)^## (.+?)\r?\n(.*?)(?=^## |\Z)")
INDEX_ROW = re.compile(r"(?m)^\|\s*`([^`]+)`\s*\|.*?\]\(([^)\s]+)\)\s*\|\s*$")

PLATFORM_LABELS = {
    "all": ("跨平台", "Cross-platform"),
    "windows": ("Windows", "Windows"),
    "macos": ("macOS", "macOS"),
    "linux": ("Linux", "Linux"),
}


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"missing frontmatter: {path}")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError(f"unclosed frontmatter: {path}") from exc
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line in {path}: {line}")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("\"'")
    return result


def normalize_link(raw: str) -> str:
    return raw.split(maxsplit=1)[0].split("#", 1)[0]


def read_index() -> list[tuple[str, str, str]]:
    text = INDEX.read_text(encoding="utf-8")
    rows: list[tuple[str, str, str]] = []
    for heading, body in INDEX_SECTION.findall(text):
        if heading == "未命中专项流程":
            continue
        for match in INDEX_ROW.finditer(body):
            route, raw_target = match.groups()
            filename = Path(normalize_link(raw_target)).name
            rows.append((route, filename, heading))
    return rows


def load_catalog() -> dict:
    if not CATALOG.is_file():
        raise ValueError(f"missing {CATALOG}")
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def build_data() -> dict:
    catalog = load_catalog()
    rows = read_index()
    by_file = catalog.get("playbooks", {})
    metadata = {
        path.name: parse_frontmatter(path)
        for path in sorted(REFERENCES.glob("playbook-*.md"))
        if path.name not in {"playbook-authoring.md", "playbook-index.md"}
    }
    categories = {item["zh"]: item for item in catalog.get("categories", [])}
    if set(by_file) != set(metadata):
        missing = sorted(set(metadata) - set(by_file))
        extra = sorted(set(by_file) - set(metadata))
        raise ValueError(f"content catalog mismatch; missing={missing}, extra={extra}")

    ordered: list[dict] = []
    seen: set[str] = set()
    for route, filename, heading in rows:
        if filename not in metadata:
            raise ValueError(f"index references unknown playbook: {filename}")
        meta = metadata[filename]
        existing_item = by_file[filename]
        if meta.get("name") != route:
            raise ValueError(f"index route does not match frontmatter name for {filename}: {route}")
        category = categories.get(heading)
        if category is None:
            raise ValueError(f"index section has no existing category metadata: {heading}")
        platform = meta.get("platform", "")
        if platform not in PLATFORM_LABELS:
            raise ValueError(f"invalid platform for {filename}: {platform}")
        item = {
            "id": route.replace("/", "-"),
            "route": route,
            # Local Playbooks may omit the optional frontmatter field; keep the
            # previously published icon from the explicit catalog in that case.
            "emoji": meta.get("emoji") or existing_item.get("emoji", ""),
            "platform": platform,
            "platform_zh": PLATFORM_LABELS[platform][0],
            "platform_en": PLATFORM_LABELS[platform][1],
            "category_zh": category["zh"],
            "category_en": category["en"],
            "category_slug": category["slug"],
            **{field: existing_item.get(field, "") for field in (
                "title_zh", "title_en", "detail_zh", "detail_en", "triggers_zh",
                "prompt_zh", "prompt_en", "when_en",
            )},
            "last_reviewed": meta.get("last_reviewed", ""),
            "source": meta.get("source", ""),
            "file": filename,
        }
        ordered.append(item)
        seen.add(filename)
    if seen != set(metadata):
        raise ValueError("playbook index does not cover every playbook")

    category_counts: dict[str, int] = {}
    for item in ordered:
        category_counts[item["category_slug"]] = category_counts.get(item["category_slug"], 0) + 1
    output_categories = []
    for category in catalog.get("categories", []):
        item = dict(category)
        item["count"] = category_counts.get(item["slug"], 0)
        output_categories.append(item)
    platform_counts = {platform: sum(item["platform"] == platform for item in ordered) for platform in PLATFORM_LABELS}
    return {
        "generated_from": catalog.get("generated_from", "88lin/computer-repair-skill @ main"),
        "total": len(ordered),
        "categories": output_categories,
        "platform_counts": platform_counts,
        "playbooks": ordered,
    }


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return "/* Generated from the repository — do not edit by hand.\n   Regenerate with: python3 tools/extract_data.py */\nwindow.CRS_DATA = " + payload + ";\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the generated artifact is stale")
    args = parser.parse_args()
    try:
        generated = render(build_data())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"extract_data: {exc}", file=sys.stderr)
        return 1
    try:
        current = OUTPUT.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"extract_data: cannot read {OUTPUT}: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if current != generated:
            print(f"{OUTPUT.relative_to(ROOT)} is stale; run python tools/extract_data.py", file=sys.stderr)
            return 1
        print("generated site data is up to date")
        return 0
    OUTPUT.write_text(generated, encoding="utf-8", newline="")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
