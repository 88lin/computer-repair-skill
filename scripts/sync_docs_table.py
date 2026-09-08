#!/usr/bin/env python3
"""按 docs/assets/js/playbooks.js 重建官网的无 JavaScript 回退表格。

回退表格是 CRS_DATA 的纯派生产物：行序、序号、标题、描述、分类、平台标签和路由 ID
都来自站点数据。手工维护 60 多行 HTML 很容易漏改，因此新增或调整 Playbook 后运行：

    python scripts/sync_docs_table.py

校验器会检查表格与站点数据一致，所以忘记运行会在 CI 里被拦下。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = REPO_ROOT / "docs" / "assets" / "js" / "playbooks.js"
SITE_PAGE = REPO_ROOT / "docs" / "index.html"
TBODY_OPEN = '<tbody id="pbBody">'
TBODY_CLOSE = "</tbody>"
# 与 docs/assets/js/site.js 的 PLAT_TAGCLASS 保持一致。
PLATFORM_TAGCLASS = {"all": "tagp-all", "windows": "tagp-win", "macos": "tagp-mac", "linux": "tagp-lin"}


def escape(value: object) -> str:
    """复刻 site.js 的 esc()，让静态回退与 JS 渲染结果一致。"""
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def load_site_data() -> dict:
    """读取并解析 window.CRS_DATA。"""
    blob = re.search(r"window\.CRS_DATA\s*=\s*(\{.*\});", SITE_DATA.read_text(encoding="utf-8"), re.S)
    if not blob:
        raise SystemExit(f"未能在 {SITE_DATA.name} 中解析 window.CRS_DATA。")
    return json.loads(blob.group(1))


def build_row(entry: dict, number: int) -> str:
    """生成单行回退表格，字段顺序与现有静态表格一致。"""
    tagclass = PLATFORM_TAGCLASS.get(entry["platform"])
    if tagclass is None:
        raise SystemExit(f"未知 platform：{entry['platform']}（{entry['id']}）")
    return (
        f'<tr class="pb-row" data-id="{escape(entry["id"])}">'
        f'<td class="pb-i">{number:02d}</td>'
        f'<td class="pb-t"><span class="pb-t-e" aria-hidden="true">{escape(entry["emoji"])}</span>'
        f'<button type="button" class="pb-open">{escape(entry["title_zh"])}</button>'
        f'<span class="pb-t-d">{escape(entry["detail_zh"])}</span></td>'
        f'<td class="pb-c">{escape(entry["category_zh"])}</td>'
        f'<td class="pb-p"><span class="tagp {tagclass}">{escape(entry["platform_zh"])}</span></td>'
        f'<td class="pb-r">{escape(entry["route"])}</td></tr>'
    )


def main() -> int:
    """重建回退表格并同步页面上的 Playbook 总数徽标。"""
    data = load_site_data()
    rows = [build_row(entry, number) for number, entry in enumerate(data["playbooks"], start=1)]

    page = SITE_PAGE.read_text(encoding="utf-8")
    start = page.index(TBODY_OPEN) + len(TBODY_OPEN)
    end = page.index(TBODY_CLOSE, start)
    rebuilt = page[:start] + "\n" + "\n".join(rows) + "\n" + page[end:]
    rebuilt = re.sub(
        r'(<b class="pill-n">)\d+(</b>)',
        lambda m: f"{m.group(1)}{data['total']}{m.group(2)}",
        rebuilt,
        count=1,
    )

    if rebuilt == page:
        print(f"回退表格已是最新：{len(rows)} 行")
        return 0

    SITE_PAGE.write_text(rebuilt, encoding="utf-8")
    print(f"回退表格已重建：{len(rows)} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
