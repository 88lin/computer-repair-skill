#!/usr/bin/env python3
"""从中文原稿生成官网的英文页面、结构化数据、站点地图和 llms.txt。

docs/index.html 是中文原稿，`data-i18n` 系列属性标记了可翻译节点；英文译文在
tools/i18n_en.json，64 条 Playbook 数据在 docs/assets/js/playbooks.js。
本脚本把三者合成 docs/en/index.html，让两种语言都是纯静态 HTML——不执行
JavaScript 的 AI 爬虫（GPTBot、PerplexityBot、ClaudeBot）也能读到英文版。

    python tools/build_site.py            # 重建
    python tools/build_site.py --check    # 只校验，CI 用

产物：docs/en/index.html、docs/sitemap.xml、docs/llms.txt，以及两个页面里
`structured-data` 与 `site-updated` 标记之间的内容。Playbook 回退表格由
scripts/sync_docs_table.py 维护，本脚本只负责把它翻译到英文页。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
ZH_PAGE = DOCS / "index.html"
EN_PAGE = DOCS / "en" / "index.html"
SITEMAP = DOCS / "sitemap.xml"
LLMS_TXT = DOCS / "llms.txt"
SITE_DATA = DOCS / "assets" / "js" / "playbooks.js"
I18N_EN = REPO_ROOT / "tools" / "i18n_en.json"
SKILL_MANIFEST = REPO_ROOT / "skills" / "computer-repair-skill" / "SKILL.md"

ORIGIN = "https://repair.88lin.eu.org"
REPO_URL = "https://github.com/88lin/computer-repair-skill"
AUTHOR_URL = "https://github.com/88lin"
LICENSE_URL = "https://www.gnu.org/licenses/agpl-3.0.html"
OG_IMAGE = f"{ORIGIN}/assets/img/og-image.png"
PUBLISHED = "2026-07-26"

# HTML 空元素没有结束标签，改写时不能计入嵌套深度。
VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)
# 与 docs/assets/js/site.js 的 PLAT_TAGCLASS 保持一致。
PLATFORM_TAGCLASS = {"all": "tagp-all", "windows": "tagp-win", "macos": "tagp-mac", "linux": "tagp-lin"}

# 文案里写死的 Playbook 总数（「64 个按需加载的专项 Playbook」「64 focused playbooks」）。
# 总数变了就得跟着改，漏改会让页面和路由索引对不上，所以重建时按数据统一改写。
# 64 条 Playbook 的标题和描述都不含「数字 + Playbook」，不会被误伤。
COUNT_IN_COPY = (
    re.compile(r"\d+(?= ?[个条][^<>\"\n]{0,10}?Playbook\b)"),
    re.compile(r"\d+(?=(?: [a-z-]+){0,2} playbooks\b)"),
)


# --------------------------------------------------------------------- 数据读取

def normalize_js(source: str) -> str:
    """把 JS 对象字面量整理成 JSON：去注释、补引号、删尾逗号，且不碰字符串字面量。"""
    out: list[str] = []
    i, n = 0, len(source)
    while i < n:
        ch = source[i]

        if ch in "\"'":
            quote = ch
            out.append('"')
            i += 1
            while i < n:
                if source[i] == "\\":
                    out.append(source[i : i + 2])
                    i += 2
                    continue
                if source[i] == quote:
                    i += 1
                    break
                # 单引号字符串里的裸双引号在 JSON 里必须转义。
                out.append('\\"' if source[i] == '"' else source[i])
                i += 1
            out.append('"')
            continue

        if source.startswith("//", i):
            nl = source.find("\n", i)
            i = n if nl < 0 else nl
            continue

        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue

        # 裸标识符做键时补上引号（ui、zh、langOn 这类）。
        if ch.isalpha() or ch in "_$":
            j = i
            while j < n and (source[j].isalnum() or source[j] in "_$"):
                j += 1
            word = source[i:j]
            k = j
            while k < n and source[k].isspace():
                k += 1
            out.append(f'"{word}"' if k < n and source[k] == ":" else word)
            i = j
            continue

        # 尾逗号。
        if ch == ",":
            k = i + 1
            while k < n and source[k].isspace():
                k += 1
            if k < n and source[k] in "}]":
                i += 1
                continue

        out.append(ch)
        i += 1
    return "".join(out)


def load_js_object(path: Path, global_name: str) -> dict:
    """解析 `window.<global_name> = {...};` 这类赋值语句。"""
    source = normalize_js(path.read_text(encoding="utf-8"))
    match = re.search(rf"window\.{global_name}\s*=\s*(\{{.*\}})\s*;", source, re.S)
    if not match:
        raise SystemExit(f"未能在 {path.name} 中解析 window.{global_name}。")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as err:
        raise SystemExit(f"{path.name} 里的 window.{global_name} 不是合法 JSON：{err}") from err


def load_english_copy() -> dict[str, str]:
    """把按前缀分组的英文译文摊平成 `前缀.键` 形式，和页面上的 data-i18n 对齐。"""
    grouped = json.loads(I18N_EN.read_text(encoding="utf-8"))
    return {f"{prefix}.{name}": text for prefix, group in grouped.items() for name, text in group.items()}


def sync_playbook_count(text: str, total: int) -> str:
    """把文案里写死的 Playbook 总数对齐到站点数据。"""
    for pattern in COUNT_IN_COPY:
        text = pattern.sub(str(total), text)
    return text


def sync_hero_pills(page: str, data: dict) -> str:
    """首屏徽标上的数字同样来自站点数据，而不是手工维护。"""
    counts = {
        "hero.pill1": data["total"],
        "hero.pill2": len([key for key in data["platform_counts"] if key != "all"]),
    }
    for key, value in counts.items():
        slot = re.compile(
            r'(<b class="pill-n">)[^<]*(</b><span class="pill-t" data-i18n="' + re.escape(key) + '")'
        )
        page, hits = slot.subn(rf"\g<1>{value}\g<2>", page)
        if hits != 1:
            raise SystemExit(f"首屏徽标 {key} 的数字槽位命中 {hits} 次，应当只有一处——检查 hero-pills 的结构。")
    return page


def skill_version() -> str:
    """从 SKILL.md 的 frontmatter 读取版本号。"""
    match = re.search(r"^version:\s*(\S+)\s*$", SKILL_MANIFEST.read_text(encoding="utf-8"), re.M)
    if not match:
        raise SystemExit(f"未能在 {SKILL_MANIFEST.name} 中解析 version。")
    return match.group(1)


def site_updated(data: dict) -> str:
    """用最新的 Playbook 复核日期作为站点的 dateModified。"""
    dates = [p["last_reviewed"] for p in data["playbooks"] if p.get("last_reviewed")]
    if not dates:
        raise SystemExit("站点数据里没有 last_reviewed，无法推导 dateModified。")
    return max(dates)


# ------------------------------------------------------------------- 中文原稿抽取

class ChineseExtractor(HTMLParser):
    """按 data-i18n 键收集中文原文，避免结构化数据与页面文案脱节。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.texts: dict[str, str] = {}
        self._key: str | None = None
        self._depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        bag = dict(attrs)
        for spec in (bag.get("data-i18n-attr") or "").split(","):
            bits = spec.split("|")
            if len(bits) == 2 and bag.get(bits[0].strip()) is not None:
                self.texts.setdefault(bits[1].strip(), bag[bits[0].strip()])
        if self._key is not None:
            if tag not in VOID_TAGS:
                self._depth += 1
            return
        key = bag.get("data-i18n") or bag.get("data-i18n-html")
        if key and tag not in VOID_TAGS:
            self._key, self._depth, self._buffer = key, 1, []

    def handle_endtag(self, tag: str) -> None:
        if self._key is None:
            return
        self._depth -= 1
        if self._depth:
            return
        self.texts.setdefault(self._key, re.sub(r"\s+", " ", "".join(self._buffer)).strip())
        self._key = None

    def handle_data(self, data: str) -> None:
        if self._key is not None:
            self._buffer.append(data)


def extract_chinese(page: str) -> dict[str, str]:
    """返回 {data-i18n 键: 中文纯文本}。"""
    parser = ChineseExtractor()
    parser.feed(page)
    parser.close()
    return parser.texts


# --------------------------------------------------------------------- 英文页改写

class EnglishRewriter(HTMLParser):
    """逐 token 重写中文页：替换可翻译节点、改写链接与语言相关的 meta。"""

    def __init__(self, strings: dict[str, str], rows_html: str) -> None:
        super().__init__(convert_charrefs=False)
        self.strings = strings
        self.rows_html = rows_html
        self.missing: set[str] = set()
        self.used: set[str] = set()
        # 只改写一次的槽位。改名或换标签会让改写静默失效，所以数出来在最后校验。
        self.slots = {"langBtn": 0, "pbBody": 0}
        self.out: list[str] = []
        self.skip = 0

    # -- 输出 --------------------------------------------------------------
    def _emit(self, chunk: str) -> None:
        if not self.skip:
            self.out.append(chunk)

    @staticmethod
    def _render_start(tag: str, attrs: dict[str, str | None], self_closing: bool) -> str:
        parts = [tag]
        for name, value in attrs.items():
            parts.append(name if value is None else f'{name}="{html.escape(value, quote=True)}"')
        return "<" + " ".join(parts) + (" />" if self_closing else ">")

    # -- 改写规则 ----------------------------------------------------------
    def _rewrite_attrs(self, tag: str, attrs: dict[str, str | None]) -> dict[str, str | None]:
        # 英文页在 /en/ 子目录下，同源静态资源要回退一级。
        for name in ("href", "src"):
            value = attrs.get(name)
            if value and value.startswith("assets/"):
                attrs[name] = "../" + value

        for spec in (attrs.get("data-i18n-attr") or "").split(","):
            bits = spec.split("|")
            if len(bits) != 2:
                continue
            name, key = bits[0].strip(), bits[1].strip()
            if key in self.strings:
                attrs[name] = self.strings[key]
                self.used.add(key)
            else:
                self.missing.add(key)

        if tag == "html":
            attrs["lang"] = "en"
            attrs["data-page-lang"] = "en"
        elif tag == "a" and attrs.get("id") == "langBtn":
            attrs["href"] = "../"
            attrs["hreflang"] = "zh-CN"
            attrs["class"] = "langbtn is-en"
            self.slots["langBtn"] += 1
        elif tag == "link" and attrs.get("rel") == "canonical":
            attrs["href"] = f"{ORIGIN}/en/"
        elif tag == "meta":
            if attrs.get("property") == "og:url":
                attrs["content"] = f"{ORIGIN}/en/"
            elif attrs.get("property") == "og:locale":
                attrs["content"] = "en_US"
            elif attrs.get("property") == "og:locale:alternate":
                attrs["content"] = "zh_CN"
        return attrs

    def _replacement(self, tag: str, attrs: dict[str, str | None]) -> str | None:
        if attrs.get("id") == "pbBody":
            self.slots["pbBody"] += 1
            return self.rows_html
        key = attrs.get("data-i18n") or attrs.get("data-i18n-html")
        if not key:
            return None
        if key in self.strings:
            self.used.add(key)
            return self.strings[key]
        self.missing.add(key)
        return None

    # -- HTMLParser 回调 ---------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip:
            if tag not in VOID_TAGS:
                self.skip += 1
            return
        bag = self._rewrite_attrs(tag, dict(attrs))
        self.out.append(self._render_start(tag, bag, self_closing=False))
        if tag in VOID_TAGS:
            return
        replacement = self._replacement(tag, bag)
        if replacement is not None:
            self.out.append(replacement)
            self.skip = 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip:
            return
        self.out.append(self._render_start(tag, self._rewrite_attrs(tag, dict(attrs)), True))

    def handle_endtag(self, tag: str) -> None:
        if self.skip:
            self.skip -= 1
            if self.skip:
                return
        self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._emit(data)

    def handle_comment(self, data: str) -> None:
        self._emit(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._emit(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self._emit(f"<?{data}>")

    def handle_entityref(self, name: str) -> None:
        self._emit(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._emit(f"&#{name};")


def escape_text(value: object) -> str:
    """复刻 site.js 的 esc()，让静态英文表格与 JS 渲染结果一致。"""
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def english_rows(data: dict) -> str:
    """生成英文页的 Playbook 回退表格，字段顺序与中文页一致。"""
    rows = []
    for number, entry in enumerate(data["playbooks"], start=1):
        tagclass = PLATFORM_TAGCLASS[entry["platform"]]
        rows.append(
            f'<tr class="pb-row" data-id="{escape_text(entry["id"])}">'
            f'<td class="pb-i">{number:02d}</td>'
            f'<td class="pb-t"><span class="pb-t-e" aria-hidden="true">{escape_text(entry["emoji"])}</span>'
            f'<button type="button" class="pb-open">{escape_text(entry["title_en"])}</button>'
            f'<span class="pb-t-d">{escape_text(entry["detail_en"])}</span></td>'
            f'<td class="pb-c">{escape_text(entry["category_en"])}</td>'
            f'<td class="pb-p"><span class="tagp {tagclass}">{escape_text(entry["platform_en"])}</span></td>'
            f'<td class="pb-r">{escape_text(entry["route"])}</td></tr>'
        )
    return "\n" + "\n".join(rows) + "\n"


def translate(page: str, strings: dict[str, str], data: dict) -> str:
    """把中文页翻译成英文页。译文缺失或多余都直接失败，避免中文漏到英文站、字典长草。"""
    rewriter = EnglishRewriter(strings, english_rows(data))
    rewriter.feed(page)
    rewriter.close()
    if rewriter.skip:
        raise SystemExit("英文页改写后标签未闭合，请检查 docs/index.html 的嵌套结构。")
    for slot, hits in rewriter.slots.items():
        if hits != 1:
            raise SystemExit(
                f"英文页没能改写 #{slot}（命中 {hits} 次，应为 1 次）——"
                "检查 docs/index.html 里这个 id 是否被改名或换了标签。"
            )
    if rewriter.missing:
        raise SystemExit(
            f"{I18N_EN.name} 缺少这些 data-i18n 键的英文译文：" + "、".join(sorted(rewriter.missing))
        )
    unused = set(strings) - rewriter.used
    if unused:
        raise SystemExit(
            f"{I18N_EN.name} 里这些键在页面上已经没人用了，请删掉：" + "、".join(sorted(unused))
        )
    return "".join(rewriter.out)


# ------------------------------------------------------------------- 结构化数据

def faq_entities(texts: dict[str, str]) -> list[dict]:
    """把页面上的七条问答映射成 Question/Answer。"""
    return [
        {
            "@type": "Question",
            "name": texts[f"faq.q{n}"],
            "acceptedAnswer": {"@type": "Answer", "text": texts[f"faq.a{n}"]},
        }
        for n in range(1, 8)
    ]


def howto_steps(texts: dict[str, str], page_url: str) -> list[dict]:
    """七步排障流程与页面上的锚点一一对应。"""
    return [
        {
            "@type": "HowToStep",
            "position": n,
            "name": texts[f"flow.s{n}t"],
            "text": texts[f"flow.s{n}p"],
            "url": f"{page_url}#step{n}",
        }
        for n in range(1, 8)
    ]


def build_graph(lang: str, data: dict, texts: dict[str, str], updated: str, version: str) -> dict:
    """生成单个页面的 JSON-LD @graph。"""
    is_en = lang == "en"
    page_url = f"{ORIGIN}/en/" if is_en else f"{ORIGIN}/"
    locale = "en" if is_en else "zh-CN"
    website = f"{ORIGIN}/#website"
    author = f"{ORIGIN}/#author"
    skill = f"{ORIGIN}/#skill"
    image = f"{ORIGIN}/#primaryimage"

    keywords = (
        [
            "computer repair",
            "Agent Skill",
            "Windows diagnostics",
            "macOS diagnostics",
            "Linux diagnostics",
            "disk space recovery",
            "malware persistence audit",
            "OpenClaw setup",
        ]
        if is_en
        else [
            "电脑维修",
            "Agent Skill",
            "C 盘清理",
            "电脑卡顿",
            "流氓软件清理",
            "弹窗广告",
            "Windows 诊断",
            "macOS 诊断",
            "Linux 诊断",
            "OpenClaw 配置",
        ]
    )

    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": website,
                "url": f"{ORIGIN}/",
                "name": "Computer Repair Skill",
                "description": texts["meta.desc"],
                "inLanguage": ["zh-CN", "en"],
                "publisher": {"@id": author},
            },
            {
                "@type": "Person",
                "@id": author,
                "name": "88lin",
                "url": AUTHOR_URL,
                "sameAs": [AUTHOR_URL, REPO_URL],
            },
            {
                "@type": "ImageObject",
                "@id": image,
                "url": OG_IMAGE,
                "contentUrl": OG_IMAGE,
                "width": 1200,
                "height": 630,
                "caption": texts["meta.imgalt"],
            },
            {
                "@type": ["WebPage", "FAQPage"],
                "@id": f"{page_url}#webpage",
                "url": page_url,
                "name": texts["meta.title"],
                "description": texts["meta.desc"],
                "inLanguage": locale,
                "isPartOf": {"@id": website},
                "about": {"@id": skill},
                "primaryImageOfPage": {"@id": image},
                "author": {"@id": author},
                "publisher": {"@id": author},
                "datePublished": PUBLISHED,
                "dateModified": updated,
                "mainEntity": faq_entities(texts),
            },
            {
                "@type": ["SoftwareApplication", "SoftwareSourceCode"],
                "@id": skill,
                "name": "Computer Repair Skill",
                "url": f"{ORIGIN}/",
                "description": texts["hero.sub"],
                "applicationCategory": "DeveloperApplication",
                "applicationSubCategory": "Agent Skill",
                "operatingSystem": "Windows, macOS, Linux",
                "softwareVersion": version,
                "dateModified": updated,
                "codeRepository": REPO_URL,
                "programmingLanguage": ["Markdown", "YAML"],
                "runtimePlatform": ["Codex", "Claude Code", "OpenClaw", "Cursor"],
                "license": LICENSE_URL,
                "isAccessibleForFree": True,
                "inLanguage": ["zh-CN", "en"],
                "keywords": keywords,
                "image": {"@id": image},
                "author": {"@id": author},
                "maintainer": {"@id": author},
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                "featureList": [category[("en" if is_en else "zh")] for category in data["categories"]],
            },
            {
                "@type": "HowTo",
                "@id": f"{page_url}#workflow",
                "name": texts["flow.title"],
                "description": texts["flow.desc"],
                "inLanguage": locale,
                "step": howto_steps(texts, page_url),
            },
        ],
    }


def render_jsonld(graph: dict) -> str:
    """输出紧凑但可读的 JSON-LD script 块。"""
    body = json.dumps(graph, ensure_ascii=False, indent=2)
    # `</script>` 出现在 JSON 字符串里会提前关闭标签。
    body = body.replace("</", "<\\/")
    return f'\n<script type="application/ld+json">\n{body}\n</script>\n'


# ------------------------------------------------------------------ 标记块填充

def fill_marker(page: str, name: str, payload: str) -> str:
    """替换 `<!-- name:start ... -->` 与 `<!-- name:end -->` 之间的内容。"""
    start_token, end_token = f"<!-- {name}:start", f"<!-- {name}:end -->"
    try:
        head = page.index(start_token)
        head = page.index("-->", head) + len("-->")
        tail = page.index(end_token, head)
    except ValueError as err:
        raise SystemExit(f"页面里找不到 {name} 标记块。") from err
    return page[:head] + payload + page[tail:]


# ------------------------------------------------------------------ 其他产物

def render_sitemap(updated: str) -> str:
    """两个语言版本互相声明 hreflang，避免被当成重复内容。"""
    alternates = "\n".join(
        f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{href}"/>'
        for lang, href in (("zh-CN", f"{ORIGIN}/"), ("en", f"{ORIGIN}/en/"), ("x-default", f"{ORIGIN}/"))
    )
    urls = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n{alternates}\n    <lastmod>{updated}</lastmod>\n  </url>"
        for loc in (f"{ORIGIN}/", f"{ORIGIN}/en/")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        f"{urls}\n"
        "</urlset>\n"
    )


def render_llms_txt(data: dict, texts: dict[str, str], updated: str, version: str) -> str:
    """给 AI 爬虫的纯文本索引：能力清单、安装方式和路由 ID。"""
    lines = [
        "# Computer Repair Skill",
        "",
        "> A cross-platform computer diagnosis and repair Agent Skill for Codex, Claude Code,",
        "> OpenClaw, Cursor and other tools that support Agent Skills. Describe a symptom in",
        "> plain language; the agent gathers read-only evidence, proposes a plan, and changes",
        "> nothing until you confirm.",
        "",
        f"- Version: {version}",
        f"- Last updated: {updated}",
        f"- Repository: {REPO_URL}",
        f"- License: GNU AGPL-3.0 ({LICENSE_URL})",
        f"- Website: {ORIGIN}/ (Chinese) · {ORIGIN}/en/ (English)",
        "",
        "## What it is",
        "",
        "Computer Repair Skill is a Markdown/YAML Skill package, not a desktop application.",
        "It ships no installer, no background process and no bundled model. The agent that",
        f"reads it supplies the execution capability. {data['total']} on-demand playbooks are routed by",
        "symptom, platform and trigger words, so only the relevant procedure enters context.",
        "",
        "## Install",
        "",
        "```",
        "npx skills add 88lin/computer-repair-skill            # interactive",
        "npx skills add 88lin/computer-repair-skill --global   # global scope",
        "npx skills add 88lin/computer-repair-skill --global --agent codex",
        "npx skills add 88lin/computer-repair-skill --global --agent claude-code",
        "```",
        "",
        "Alternatives: ask an agent to install from the repository URL; clone the repository and",
        "run `scripts/install.ps1 -Target codex|claude|agents|custom` on Windows PowerShell or",
        "`scripts/install.sh --target codex|claude|agents|custom` on macOS/Linux (`custom` takes",
        "`-Destination` / `--destination`); or copy `skills/computer-repair-skill/` into",
        "`~/.codex/skills/`, `~/.claude/skills/` or `~/.agents/skills/`. The installer refuses to",
        "overwrite an existing install unless you pass `-Force` / `--force`, which backs the old",
        "version up first.",
        "",
        "## Safety model",
        "",
        "Four risk levels gate every action:",
        "",
        "- L1 read-only — observe without changing state; runs directly once scoped.",
        "- L2 reversible change — show plan, impact and rollback, then get confirmation.",
        "- L3 high-impact change — delete, kill, elevate, install, uninstall, batch move,",
        "  startup or security settings; needs exact commands plus separate confirmation.",
        "- L4 system red line — boot volume, partition table, firmware, keychains, credential",
        "  stores, whole home directory, or disabling core security; the agent stops and",
        "  escalates to the vendor or enterprise recovery path instead.",
        "",
        "Never executed: piping remote responses into a shell (`irm | iex`, `curl | bash`),",
        "wildcard or ancestor-directory sweeps over user data, hiding delete targets behind",
        "`xargs`/`eval`/encoded payloads, routing the same deletion through Python or Node to",
        "dodge host guardrails, printing secrets into chat, disabling Defender, SmartScreen,",
        "UAC, the firewall, Windows Update or core isolation, and pirated activation, unknown",
        "downloaders, force-removing Edge or unaudited one-click tuning bundles.",
        "",
        "## Workflow",
        "",
    ]
    for n in range(1, 8):
        lines.append(f"{n}. {texts[f'flow.s{n}t']} — {texts[f'flow.s{n}p']}")
    lines += ["", f"## Playbooks ({data['total']})", ""]

    by_slug = {category["slug"]: category for category in data["categories"]}
    seen: list[str] = []
    for entry in data["playbooks"]:
        if entry["category_slug"] not in seen:
            seen.append(entry["category_slug"])
    for slug in seen:
        category = by_slug[slug]
        lines += [f"### {category['en']} ({category['count']})", ""]
        for entry in data["playbooks"]:
            if entry["category_slug"] != slug:
                continue
            lines.append(
                f"- `{entry['route']}` — {entry['title_en']} / {entry['title_zh']} "
                f"[{entry['platform_en']}]: {entry['detail_en']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------------ 入口

def build() -> dict[Path, str]:
    """生成全部产物，返回 {路径: 内容}。"""
    data = load_js_object(SITE_DATA, "CRS_DATA")
    strings = load_english_copy()
    version = skill_version()
    updated = site_updated(data)
    total = data["total"]
    time_tag = f'<time datetime="{updated}">{updated}</time>'

    # 先把两种语言的文案对齐到实际 Playbook 数量，后面的结构化数据才跟着一致。
    zh_page = sync_playbook_count(ZH_PAGE.read_text(encoding="utf-8"), total)
    zh_page = sync_hero_pills(zh_page, data)
    strings = {key: sync_playbook_count(text, total) for key, text in strings.items()}
    zh_texts = extract_chinese(zh_page)

    zh_page = fill_marker(zh_page, "site-updated", time_tag)
    zh_page = fill_marker(
        zh_page, "structured-data", render_jsonld(build_graph("zh", data, zh_texts, updated, version))
    )

    en_page = translate(zh_page, strings, data)
    en_page = fill_marker(
        en_page, "structured-data", render_jsonld(build_graph("en", data, strings, updated, version))
    )

    return {
        ZH_PAGE: zh_page,
        EN_PAGE: en_page,
        SITEMAP: render_sitemap(updated),
        LLMS_TXT: render_llms_txt(data, strings, updated, version),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成官网英文页、结构化数据、站点地图和 llms.txt。")
    parser.add_argument("--check", action="store_true", help="只校验产物是否最新，不写文件")
    args = parser.parse_args()

    artifacts = build()
    stale = [
        path
        for path, content in artifacts.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]

    if args.check:
        if stale:
            names = "、".join(path.relative_to(REPO_ROOT).as_posix() for path in stale)
            print(f"站点产物已过期：{names}\n请运行 python tools/build_site.py 后提交。", file=sys.stderr)
            return 1
        print(f"站点产物已是最新：{len(artifacts)} 个文件")
        return 0

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        # 显式写 LF，跟 .gitattributes 的 eol=lf 一致，避免 Windows 上生成 CRLF。
        path.write_text(artifacts[path], encoding="utf-8", newline="\n")
    if stale:
        print("已重建：" + "、".join(path.relative_to(REPO_ROOT).as_posix() for path in stale))
    else:
        print(f"站点产物已是最新：{len(artifacts)} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
