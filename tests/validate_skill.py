#!/usr/bin/env python3
"""验证 Computer Repair Skill 的结构、来源、链接、跨平台一致性和发布完整性。

设计约束：

* **零第三方依赖** —— 只用标准库，便于在任何平台的干净 Python 上直接跑。
* **单一真源** —— 数量、分类、上游/本地划分全部从各 Playbook 的 frontmatter 派生，
  并与 `tests/playbook_registry.py` 的登记快照交叉核对，不在本文件里写死字面量。
* **一次运行报告全部问题** —— 收集式校验，不在第一条失败就退出。
* **error / warning 分级** —— `--strict` 时 warning 也会导致非零退出码。

用法：

    python tests/validate_skill.py            # error 才失败
    python tests/validate_skill.py --strict   # warning 也失败（CI 用）
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

# 生成器与校验器共用同一份分类真源；上面的 sys.path.insert 让直接执行脚本时也能导入。
import playbook_registry as registry

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "computer-repair-skill"
REFERENCES_DIR = SKILL_DIR / "references"

REQUIRED_SKILL_FIELDS = {"name", "description"}
OPTIONAL_SKILL_FIELDS = {"license"}
EXPECTED_LICENSE = "AGPL-3.0"
MAX_SKILL_DESCRIPTION_CHARS = 600
MAX_SKILL_DESCRIPTION_WORDS = 80
MAX_SKILL_LINES = 500
MAX_PLAYBOOK_DESCRIPTION_CHARS = 120
STALE_REVIEW_DAYS = 365

REQUIRED_PLAYBOOK_FIELDS = {
    "name",
    "description",
    "platform",
    "category",
    "last_reviewed",
    "author",
    "source",
}
OPTIONAL_PLAYBOOK_FIELDS = {"emoji"}
ALLOWED_PLATFORMS = {"all", "linux", "macos", "windows"}
PLATFORM_PREFIXES = {"windows": "windows", "linux": "linux", "macos": "macos"}
# 提到某平台专属 Playbook 时，同一行必须出现的平台词（用于防止把用户路由进不匹配的平台）。
PLATFORM_MENTIONS = {
    "windows": ("Windows", "WinRE", "PE"),
    "macos": ("macOS", "Mac", "OS X"),
    "linux": ("Linux", "Ubuntu", "Debian", "Fedora", "RHEL", "Arch"),
}
UPSTREAM_AUTHOR = "upstream-maintainers"
LOCAL_AUTHOR = "computer-repair-skill-maintainers"

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_SRC = re.compile(r"<(?:img|source)\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
HTML_HREF = re.compile(r"<a\b[^>]*?\bhref\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(\S*)")
INDEX_ROW = re.compile(r"(?m)^\|\s*`([^`]+)`\s*\|.*?\]\(([^)\s]+)\)\s*\|\s*$")
INDEX_SECTION = re.compile(r"(?ms)^## (.+?)\r?\n(.*?)(?=^## |\Z)")
IGNORED_INDEX_SECTIONS = {"未命中专项流程"}
TOOL_SECTION = re.compile(r"(?ms)^## Tools referenced\s*(.*?)(?=^## |\Z)")
# 语义工具映射表首列：`alias` 或 `alias` / `alias`
TOOL_TABLE_ROW = re.compile(r"(?m)^\|\s*`([a-z][a-z0-9_]*)`(?:\s*/\s*`([a-z][a-z0-9_]*)`)?\s*\|")
CODE_TOKEN = re.compile(r"`([^`\n]+)`")

REMOTE_SHELL_PATTERNS = {
    "远程脚本直接管道执行": re.compile(
        r"(?im)(?:curl|wget|irm|iwr|Invoke-WebRequest|Invoke-RestMethod)\b[^\r\n|]*\|\s*"
        r"(?:sudo\s+)?(?:bash|sh|zsh|pwsh|powershell|python3?|iex|Invoke-Expression)\b"
    ),
    "远程脚本命令替换执行": re.compile(r"(?im)(?:/bin/)?(?:bash|sh|zsh)\s+-c\s+[\"']?\$\(\s*(?:curl|wget)\b"),
    "PowerShell 下载即执行": re.compile(
        r"(?im)(?:iex|Invoke-Expression)\s*\(?\s*(?:irm|iwr|Invoke-WebRequest|Invoke-RestMethod|"
        r"\(?New-Object\s+Net\.WebClient\)?\.DownloadString)"
    ),
    "进程替换执行远程脚本": re.compile(r"(?im)(?:bash|sh|zsh)\s+<\(\s*(?:curl|wget)\b"),
}
# 散文里出现"禁止 `irm | iex`"是安全策略本身，不是可执行命令。
# 只有当同一行没有任何否定语义时才判为违规；围栏代码块内命中一律判违规。
NEGATION_MARKERS = re.compile(
    r"(?i)\b(?:do\s+not|don't|never|avoid|refuse|forbidden|prohibited|disallow|"
    r"instead\s+of|rather\s+than|no\s+remote)\b|不执行|不运行|不得|不要|不允许|不使用|禁止|避免|严禁|拒绝",
)

PLACEHOLDER = re.compile(r"\b(?:TODO|FIXME|TBD)\b|YOUR_GITHUB_USER|<owner>", re.IGNORECASE)
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "private key": re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
}
FORBIDDEN_PRODUCT_MARKER = re.compile(r"noah", re.IGNORECASE)
SELF_PATH = Path(__file__).resolve()
TEXT_SUFFIXES = {"", ".md", ".py", ".ps1", ".sh", ".yaml", ".yml", ".json", ".svg", ".cfg", ".toml"}
HYGIENE_SUFFIXES = {".md", ".py", ".sh", ".ps1", ".yaml", ".yml"}
# 与 .gitignore 对齐：版本控制目录与工具缓存不是仓库产物，任何遍历都必须跳过。
IGNORED_DIR_NAMES = frozenset(
    {
        ".eggs",
        ".git",
        ".hg",
        ".idea",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)
# 需要保留 CRLF 或制表符的例外文件（当前为空，保留结构以便将来登记）。
HYGIENE_EXEMPT: set[str] = set()
# Keep a Changelog 约定每个版本都重复 `### Added` / `### Changed` / `### Fixed`，
# 这是格式要求而非作者疏漏；锚点校验本身已能解析 `-N` 后缀，因此只豁免告警。
DUPLICATE_HEADING_EXEMPT = {"CHANGELOG.md"}


def is_single_emoji(value: str) -> bool:
    """Accept one emoji, optionally followed by a variation selector."""
    value = value.strip()
    if not value or any(character.isspace() for character in value):
        return False

    base = [character for character in value if ord(character) not in {0xFE0E, 0xFE0F, 0x200D}]
    if len(base) != 1:
        return False

    codepoint = ord(base[0])
    return 0x1F000 <= codepoint <= 0x1FAFF or 0x2300 <= codepoint <= 0x23FF or 0x2600 <= codepoint <= 0x27BF


def configure_console_encoding() -> None:
    """在 Windows CI 等非 UTF-8 终端中稳定输出中文验证结果。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def heading_slug(text: str) -> str:
    """近似 GitHub 的标题锚点算法：去装饰、去标点、空格转连字符。"""
    text = MARKDOWN_IMAGE.sub("", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "").replace("*", "").replace("_", "_")
    slug: list[str] = []
    for character in text.strip().lower():
        if character in {"-", "_"}:
            slug.append(character)
        elif character.isspace():
            slug.append("-")
        elif unicodedata.category(character)[0] in {"P", "S", "C", "Z"}:
            continue
        else:
            slug.append(character)
    return "".join(slug)


def strip_code_fences(text: str) -> list[tuple[int, str]]:
    """返回 (行号, 行内容)，跳过围栏代码块内部，避免把示例当成正文规则。"""
    result: list[tuple[int, str]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if match:
            marker = match.group(2)
            if fence is None:
                fence = marker[0] * 3
                continue
            if line.strip().startswith(fence):
                fence = None
                continue
        if fence is None:
            result.append((number, line))
    return result


def iter_code_fences(text: str) -> list[tuple[int, str, str]]:
    """返回 (开栏行号, 语言标注, 块内容)；未闭合的块语言标注记为 None 由调用方处理。"""
    blocks: list[tuple[int, str, str]] = []
    fence: str | None = None
    start = 0
    language = ""
    body: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if match and fence is None:
            fence = match.group(2)[0] * 3
            start = number
            language = match.group(3)
            body = []
            continue
        if fence is not None and line.strip().startswith(fence):
            blocks.append((start, language, "\n".join(body)))
            fence = None
            continue
        if fence is not None:
            body.append(line)
    if fence is not None:
        blocks.append((start, "\x00unclosed", "\n".join(body)))
    return blocks


def find_remote_execution_hits(text: str) -> list[tuple[int, str, str, str]]:
    """定位"下载即执行"违规，返回 (行号, 标签, 片段, 上下文)。

    上下文感知的理由：安全策略文档必须能写出被禁止的命令形态（如"禁止 `irm | iex`"），
    否则校验器会把红线条款本身判成违规。判定规则：

    * 围栏代码块内命中 -> 一律违规（代码块就是给人照抄执行的）；
    * 散文行命中 -> 仅当同行没有否定语义时才违规。
    """
    hits: list[tuple[int, str, str, str]] = []
    for start, _language, body in iter_code_fences(text):
        for offset, line in enumerate(body.splitlines()):
            for label, pattern in REMOTE_SHELL_PATTERNS.items():
                match = pattern.search(line)
                if match:
                    hits.append((start + 1 + offset, label, match.group(0), "代码块"))
    for number, line in strip_code_fences(text):
        if NEGATION_MARKERS.search(line):
            continue
        for label, pattern in REMOTE_SHELL_PATTERNS.items():
            match = pattern.search(line)
            if match:
                hits.append((number, label, match.group(0), "正文"))
    return sorted(hits)


def split_table_cells(line: str) -> list[str]:
    """按未转义的 `|` 切分表格行。"""
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\":
            escaped = True
            current.append(character)
            continue
        if character == "|":
            cells.append("".join(current))
            current = []
            continue
        current.append(character)
    cells.append("".join(current))
    return cells


class Validation:
    """集中收集 error 与 warning，确保一次运行能报告全部问题。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def check(self, condition: bool, message: str) -> None:
        """条件不满足时记录一条稳定、可定位的中文 error。"""
        if not condition:
            self.errors.append(message)

    def check_warn(self, condition: bool, message: str) -> None:
        """条件不满足时记录 warning（默认不阻塞，`--strict` 下阻塞）。"""
        if not condition:
            self.warnings.append(message)

    def finish(self, *, strict: bool, total: int) -> int:
        """打印最终结果并返回适合 CI 的退出码。"""
        if self.errors:
            print(f"验证失败，共 {len(self.errors)} 项 error：")
            for message in self.errors:
                print(f"  - [error] {message}")
        if self.warnings:
            print(f"另有 {len(self.warnings)} 项 warning：")
            for message in self.warnings:
                print(f"  - [warn] {message}")

        if self.errors:
            return 1
        if self.warnings and strict:
            print("--strict 模式下 warning 也视为失败。")
            return 1
        print(
            f"验证通过：{total} 个 Playbook，结构、分类登记、索引、链接、工具契约、"
            f"格式、许可证和安全扫描均正常（warning {len(self.warnings)} 项）。"
        )
        return 0


def read_text(path: Path, validation: Validation) -> str:
    """按 UTF-8 读取文本；编码或读取失败会进入统一错误列表。"""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        validation.error(f"无法按 UTF-8 读取 {path.relative_to(REPO_ROOT)}：{exc}")
        return ""


def parse_frontmatter(path: Path, validation: Validation) -> dict[str, str]:
    """解析本项目使用的简单单层 YAML frontmatter，不引入第三方依赖。"""
    text = read_text(path, validation)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        validation.error(f"缺少 frontmatter：{path.relative_to(REPO_ROOT)}")
        return {}

    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        validation.error(f"frontmatter 未闭合：{path.relative_to(REPO_ROOT)}")
        return {}

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            validation.error(f"frontmatter 行格式错误：{path.relative_to(REPO_ROOT)} -> {line}")
            continue
        key, value = line.split(":", 1)
        if line[:1].isspace():
            validation.error(
                f"frontmatter 不支持嵌套字段（解析器是单层的）：{path.relative_to(REPO_ROOT)} -> {line.strip()}"
            )
            continue
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata


def find_playbooks() -> list[Path]:
    """返回可执行 Playbook，排除路由索引和编写规范。"""
    return registry.find_playbooks()


def iter_repo_files() -> list[Path]:
    """遍历仓库内的普通文件，跳过版本控制目录与各类工具缓存。

    缓存目录（`.ruff_cache/`、`__pycache__/` 等）里存在二进制文件，
    一旦被纳入格式卫生扫描就会以「无法按 UTF-8 读取」误报，
    而这些路径本来就在 .gitignore 里，不是仓库产物。
    """
    return [
        path
        for path in sorted(REPO_ROOT.rglob("*"))
        if path.is_file() and IGNORED_DIR_NAMES.isdisjoint(path.parts)
    ]


def validate_skill_metadata(validation: Validation) -> None:
    """检查 Skill 触发元数据、长度限制和 Codex 展示元数据。"""
    skill_path = SKILL_DIR / "SKILL.md"
    metadata = parse_frontmatter(skill_path, validation)

    unexpected = set(metadata) - REQUIRED_SKILL_FIELDS - OPTIONAL_SKILL_FIELDS
    validation.check(
        not unexpected,
        f"SKILL.md frontmatter 含未登记字段：{', '.join(sorted(unexpected))}；"
        f"允许 {', '.join(sorted(REQUIRED_SKILL_FIELDS | OPTIONAL_SKILL_FIELDS))}。",
    )
    missing = REQUIRED_SKILL_FIELDS - set(metadata)
    validation.check(not missing, f"SKILL.md frontmatter 缺少字段：{', '.join(sorted(missing))}。")

    validation.check(
        metadata.get("name") == SKILL_DIR.name,
        f"SKILL.md 的 name 必须等于所在目录名 {SKILL_DIR.name}（规范要求），实际为 {metadata.get('name')}。",
    )
    if "license" in metadata:
        validation.check(
            metadata["license"] == EXPECTED_LICENSE,
            f"SKILL.md 的 license 应为 {EXPECTED_LICENSE}，实际为 {metadata['license']}。",
        )

    description = metadata.get("description", "").strip()
    validation.check(bool(description), "SKILL.md 缺少非空 description。")
    validation.check(
        len(description) <= MAX_SKILL_DESCRIPTION_CHARS,
        f"SKILL.md description 过长：{len(description)} 字符，最多 {MAX_SKILL_DESCRIPTION_CHARS} 字符。",
    )
    validation.check(
        len(description.split()) <= MAX_SKILL_DESCRIPTION_WORDS,
        f"SKILL.md description 过长：{len(description.split())} 个空格分词，最多 {MAX_SKILL_DESCRIPTION_WORDS} 个。",
    )
    validation.check(
        description.startswith("Use this skill when "),
        "SKILL.md description 应使用 'Use this skill when ...' 表达触发意图。",
    )

    skill_lines = read_text(skill_path, validation).splitlines()
    validation.check(
        len(skill_lines) <= MAX_SKILL_LINES,
        f"SKILL.md 超过 {MAX_SKILL_LINES} 行：{len(skill_lines)}。",
    )

    agent_path = SKILL_DIR / "agents" / "openai.yaml"
    agent_text = read_text(agent_path, validation)
    for field in ("display_name:", "short_description:", "default_prompt:"):
        validation.check(field in agent_text, f"agents/openai.yaml 缺少 {field[:-1]}。")
    validation.check(
        "$computer-repair-skill" in agent_text,
        "agents/openai.yaml 的 default_prompt 必须显式调用 Skill。",
    )


def collect_playbook_metadata(validation: Validation) -> dict[Path, dict[str, str]]:
    """一次性解析全部 Playbook frontmatter，供后续多条规则复用。"""
    return {path: parse_frontmatter(path, validation) for path in find_playbooks()}


def validate_playbooks(validation: Validation, catalog: dict[Path, dict[str, str]]) -> None:
    """检查 Playbook 元数据、命名约定、平台一致性与上游/扩展边界。"""
    today = date.today()
    names: dict[str, Path] = {}
    descriptions: dict[str, Path] = {}

    for path, metadata in catalog.items():
        unexpected = set(metadata) - REQUIRED_PLAYBOOK_FIELDS - OPTIONAL_PLAYBOOK_FIELDS
        validation.check(
            not unexpected,
            f"{path.name} 包含未登记的 frontmatter 字段：{', '.join(sorted(unexpected))}。",
        )
        missing = REQUIRED_PLAYBOOK_FIELDS - set(metadata)
        validation.check(not missing, f"{path.name} 缺少字段：{', '.join(sorted(missing))}。")

        if "emoji" in metadata:
            validation.check(
                is_single_emoji(metadata["emoji"]),
                f"{path.name} 的 emoji 必须是单个 emoji；没有合适图标时请省略该字段。",
            )

        name = metadata.get("name", "")
        if name:
            expected_file = f"playbook-{name.replace('/', '-')}.md"
            validation.check(
                expected_file == path.name,
                f"{path.name} 的 name 与文件名不一致：name={name} 期望文件名 {expected_file}。",
            )
            if name in names:
                validation.error(f"Playbook name 重复：{name}（{names[name].name}、{path.name}）。")
            else:
                names[name] = path

        description = metadata.get("description", "").strip()
        validation.check(bool(description), f"{path.name} 缺少非空 description。")
        validation.check(
            len(description) <= MAX_PLAYBOOK_DESCRIPTION_CHARS,
            f"{path.name} 的 description 过长：{len(description)} 字符，最多 {MAX_PLAYBOOK_DESCRIPTION_CHARS} 字符。",
        )
        description_key = re.sub(r"\s+", " ", description).casefold()
        if description_key and description_key in descriptions:
            validation.error(
                f"Playbook description 重复：{path.name}、{descriptions[description_key].name}。"
            )
        elif description_key:
            descriptions[description_key] = path

        platform = metadata.get("platform", "")
        validation.check(platform in ALLOWED_PLATFORMS, f"{path.name} 的 platform 无效：{platform}。")
        for prefix, expected_platform in PLATFORM_PREFIXES.items():
            if name.startswith(f"{prefix}-"):
                validation.check(
                    platform == expected_platform,
                    f"{path.name} 以 {prefix}- 开头，platform 应为 {expected_platform}，实际为 {platform}。",
                )

        category = metadata.get("category", "")
        validation.check(
            category in registry.CATEGORY_SLUGS,
            f"{path.name} 的 category 未在 tests/playbook_registry.py 的 CATEGORIES 中登记：{category or '(缺失)'}。",
        )

        reviewed = metadata.get("last_reviewed", "")
        try:
            reviewed_date = date.fromisoformat(reviewed)
        except ValueError:
            validation.error(f"{path.name} 的 last_reviewed 不是 YYYY-MM-DD：{reviewed}。")
        else:
            validation.check(
                reviewed_date <= today,
                f"{path.name} 的 last_reviewed 是未来日期：{reviewed}。",
            )
            validation.check_warn(
                reviewed_date >= today - timedelta(days=STALE_REVIEW_DAYS),
                f"{path.name} 的 last_reviewed 已超过 {STALE_REVIEW_DAYS} 天未复核：{reviewed}。",
            )

        body = read_text(path, validation)
        source = metadata.get("source", "")
        if source == "bundled":
            validation.check(
                metadata.get("author") == UPSTREAM_AUTHOR,
                f"{path.name} 的上游 author 应为 {UPSTREAM_AUTHOR}。",
            )
            validation.check("emoji" in metadata, f"{path.name} 应保留 bundled 上游 Playbook 的 emoji。")
        elif source == "local":
            validation.check(
                metadata.get("author") == LOCAL_AUTHOR,
                f"{path.name} 的本地扩展 author 应为 {LOCAL_AUTHOR}。",
            )
            validation.check("## Verification" in body, f"{path.name} 缺少 Verification 段落。")
            validation.check("## Escalation" in body, f"{path.name} 缺少 Escalation 段落。")
        else:
            validation.error(f"{path.name} 的 source 必须是 bundled 或 local，实际为 {source or '(缺失)'}。")

        validation.check(
            bool(TOOL_SECTION.search(body)),
            f"{path.name} 缺少 '## Tools referenced' 段落，工具契约无法双向校验。",
        )


def validate_remote_execution(validation: Validation) -> None:
    """全仓扫描"下载即执行"：覆盖 SKILL.md 与所有参考文档，而不只是 Playbook。"""
    scanned = 0
    for path in sorted(SKILL_DIR.rglob("*.md")):
        scanned += 1
        for number, label, snippet, context in find_remote_execution_hits(read_text(path, validation)):
            validation.error(
                f"{path.name}:{number} 在{context}中出现{label}：{snippet[:80]}；"
                "请先下载、审阅并在用户确认后执行本地文件。"
            )
    validation.check(scanned > 0, "未扫描到任何 Skill Markdown 文件，远程执行检查形同虚设。")


def validate_platform_routing(validation: Validation, catalog: dict[Path, dict[str, str]]) -> None:
    """禁止把用户路由进不匹配平台的 Playbook：跨平台引用必须在同一行点明平台。"""
    platform_by_name = {
        metadata.get("name", ""): metadata.get("platform", "")
        for metadata in catalog.values()
        if metadata.get("name")
    }

    for path, metadata in catalog.items():
        own_platform = metadata.get("platform", "")
        text = read_text(path, validation)
        for number, line in strip_code_fences(text):
            for token in CODE_TOKEN.findall(line):
                target_platform = platform_by_name.get(token.strip())
                if not target_platform or target_platform == "all":
                    continue
                if target_platform == own_platform:
                    continue
                # platform 值非法时由 validate_playbooks 报错；这里不能因未知取值而崩溃，
                # 否则一处 frontmatter 打错字会让整轮校验只剩一条 traceback。
                mentions = PLATFORM_MENTIONS.get(target_platform)
                if not mentions:
                    continue
                if any(word in line for word in mentions):
                    continue
                validation.error(
                    f"{path.name}:{number} 引用了 {target_platform} 专属 Playbook `{token}`，"
                    f"但同一行没有点明平台（需出现 {mentions[0]} 之类的限定词），"
                    f"其他平台的用户会被路由进死路。"
                )


def normalize_link_target(raw_target: str) -> tuple[str, str]:
    """移除 Markdown 链接标题与尖括号，返回 (本地路径, 锚点)。"""
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif target:
        target = target.split(maxsplit=1)[0]
    path_part, _, anchor = target.partition("#")
    return unquote(path_part), unquote(anchor)


def heading_slugs(text: str) -> set[str]:
    """收集文件里所有标题锚点（跳过代码块中的示例标题）。"""
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for _, line in strip_code_fences(text):
        match = HEADING.match(line)
        if not match:
            continue
        base = heading_slug(match.group(2))
        if not base:
            continue
        index = counts.get(base, 0)
        slugs.add(base if index == 0 else f"{base}-{index}")
        counts[base] = index + 1
    return slugs


def validate_links(validation: Validation) -> None:
    """检查全部本地链接（含图片与 HTML）、锚点，并确认路由索引覆盖全部 Playbook。"""
    slug_cache: dict[Path, set[str]] = {}

    def slugs_for(path: Path) -> set[str]:
        if path not in slug_cache:
            slug_cache[path] = heading_slugs(read_text(path, validation))
        return slug_cache[path]

    for path in sorted(REPO_ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = read_text(path, validation)
        targets = [
            (kind, raw)
            for kind, pattern in (
                ("链接", MARKDOWN_LINK),
                ("图片", MARKDOWN_IMAGE),
                ("HTML src", HTML_SRC),
                ("HTML href", HTML_HREF),
            )
            for raw in pattern.findall(text)
            for kind in (kind,)
        ]
        for kind, raw_target in targets:
            target, anchor = normalize_link_target(raw_target)
            if target and re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            if target.startswith("//"):
                continue
            resolved = (path.parent / target).resolve() if target else path
            if not resolved.exists():
                validation.error(f"本地{kind}不存在：{path.relative_to(REPO_ROOT)} -> {raw_target}")
                continue
            if anchor and resolved.suffix.lower() == ".md":
                validation.check(
                    anchor.lower() in slugs_for(resolved),
                    f"锚点不存在：{path.relative_to(REPO_ROOT)} -> {raw_target}",
                )

    index_path = REFERENCES_DIR / "playbook-index.md"
    index_text = read_text(index_path, validation)
    indexed = {
        Path(normalize_link_target(target)[0]).name
        for target in MARKDOWN_LINK.findall(index_text)
        if normalize_link_target(target)[0].startswith("playbook-")
    }
    actual = {path.name for path in find_playbooks()}
    missing = actual - indexed
    extra = indexed - actual
    validation.check(not missing, "路由索引缺少：" + ", ".join(sorted(missing)))
    validation.check(not extra, "路由索引包含不存在的 Playbook：" + ", ".join(sorted(extra)))


def validate_index_consistency(validation: Validation, catalog: dict[Path, dict[str, str]]) -> None:
    """索引的登记名、章节归属必须与 frontmatter 的 name / category 一致。"""
    index_path = REFERENCES_DIR / "playbook-index.md"
    index_text = read_text(index_path, validation)
    metadata_by_file = {path.name: metadata for path, metadata in catalog.items()}

    seen_files: dict[str, str] = {}
    seen_names: dict[str, str] = {}
    for heading, body in INDEX_SECTION.findall(index_text):
        heading = heading.strip()
        if heading in IGNORED_INDEX_SECTIONS:
            continue
        slug = registry.HEADING_TO_SLUG.get(heading)
        validation.check(
            slug is not None,
            f"路由索引章节未在 CATEGORIES 中登记：{heading}。",
        )
        for name, raw_target in INDEX_ROW.findall(body):
            filename = Path(normalize_link_target(raw_target)[0]).name
            if filename in seen_files:
                validation.error(f"路由索引重复登记：{filename}。")
            seen_files[filename] = heading
            if name in seen_names:
                validation.error(f"路由索引名称重复：{name}。")
            seen_names[name] = filename

            metadata = metadata_by_file.get(filename)
            if metadata is None:
                continue
            validation.check(
                name == metadata.get("name"),
                f"路由索引名称与 frontmatter 不一致：{filename} -> {name}（应为 {metadata.get('name')}）。",
            )
            if slug is not None:
                validation.check(
                    metadata.get("category") == slug,
                    f"{filename} 的 category={metadata.get('category')} 与索引章节「{heading}」"
                    f"（{slug}）不一致。",
                )


def build_tool_universe(validation: Validation) -> set[str]:
    """从平台映射表首列构建规范工具别名集合（不吃正文里的原始命令）。"""
    mapping_files = [
        REFERENCES_DIR / "tool-contract.md",
        REFERENCES_DIR / "tools-windows.md",
        REFERENCES_DIR / "tools-macos.md",
        REFERENCES_DIR / "tools-linux.md",
    ]
    universe: set[str] = set()
    for path in mapping_files:
        for primary, secondary in TOOL_TABLE_ROW.findall(read_text(path, validation)):
            universe.add(primary)
            if secondary:
                universe.add(secondary)
    validation.check(bool(universe), "未能从工具映射表解析出任何语义工具别名。")
    return universe


def validate_tool_references(validation: Validation) -> None:
    """工具契约双向校验：声明必须已登记，正文用到的登记别名必须声明。"""
    universe = build_tool_universe(validation)
    used_anywhere: set[str] = set()

    for path in find_playbooks():
        text = read_text(path, validation)
        section = TOOL_SECTION.search(text)
        if not section:
            continue
        declared = {alias for alias in CODE_TOKEN.findall(section.group(1)) if alias in universe}
        unknown = {
            token
            for token in re.findall(r"(?m)^\s*-\s+`([a-z][a-z0-9_]*)`", section.group(1))
            if token not in universe
        }
        for alias in sorted(unknown):
            validation.error(f"{path.name} 声明了未登记的工具别名：{alias}。")

        # declared 与 used 同时为空时双向检查会静默通过，等于没有工具契约。
        validation.check(
            bool(declared),
            f"{path.name} 的 '## Tools referenced' 没有声明任何已登记的语义工具别名，"
            "工具契约无法生效（泛化措辞不算声明）。",
        )

        body = text[: section.start()] + text[section.end() :]
        used = {alias for alias in CODE_TOKEN.findall(body) if alias in universe}
        used_anywhere |= used | declared
        for alias in sorted(used - declared):
            validation.error(f"{path.name} 正文使用了 `{alias}` 但未在 '## Tools referenced' 中声明。")

    for alias in sorted(universe - used_anywhere):
        validation.check_warn(False, f"工具别名 `{alias}` 已登记但没有任何 Playbook 使用。")


def validate_registry_consistency(validation: Validation, catalog: dict[Path, dict[str, str]]) -> None:
    """派生计数必须与生成器一致：README / 索引里的数字不能靠手改。"""
    try:
        snapshot = registry.collect()
    except registry.RegistryError as exc:
        validation.error(f"分类登记不可用：{exc}")
        return

    for item in snapshot["unknown"]:  # type: ignore[union-attr]
        validation.error(f"Playbook 的 category 未登记：{item}")

    validation.check(
        snapshot["total"] == len(catalog),
        f"登记快照与实际 Playbook 数不一致：{snapshot['total']} vs {len(catalog)}。",
    )
    derived_bundled = sum(1 for m in catalog.values() if m.get("source") == "bundled")
    derived_local = sum(1 for m in catalog.values() if m.get("source") == "local")
    validation.check(
        snapshot["bundled"] == derived_bundled and snapshot["local"] == derived_local,
        f"上游/本地划分不一致：快照 {snapshot['bundled']}/{snapshot['local']}，"
        f"实际 {derived_bundled}/{derived_local}。",
    )

    index_text = read_text(REFERENCES_DIR / "playbook-index.md", validation)
    readme_text = read_text(REPO_ROOT / "README.md", validation)
    try:
        expected_index = registry.replace_block(
            index_text, "index-summary", registry.render_index_summary(snapshot), registry.INDEX_PATH
        )
        expected_readme = registry.rewrite_readme(readme_text, snapshot)
    except registry.RegistryError as exc:
        validation.error(f"派生内容标记缺失或损坏：{exc}")
        return

    validation.check(
        index_text == expected_index,
        "playbook-index.md 的登记摘要已漂移，请运行 python tests/playbook_registry.py --write。",
    )
    validation.check(
        readme_text == expected_readme,
        "README.md 的分类计数已漂移，请运行 python tests/playbook_registry.py --write。",
    )


def validate_formatting(validation: Validation) -> None:
    """格式卫生：行尾、EOF 换行、代码块语言标注、表格行内代码的管道转义。"""
    for path in iter_repo_files():
        if path.suffix.lower() not in HYGIENE_SUFFIXES:
            continue
        relative = path.relative_to(REPO_ROOT)
        if str(relative) in HYGIENE_EXEMPT:
            continue
        raw = path.read_bytes()
        if not raw:
            continue
        validation.check(b"\r\n" not in raw, f"{relative} 含 CRLF 行尾，.gitattributes 要求 LF。")
        validation.check(raw.endswith(b"\n"), f"{relative} 缺少文件末尾换行。")

        text = read_text(path, validation)
        for number, line in enumerate(text.splitlines(), start=1):
            if line != line.rstrip():
                validation.check(False, f"{relative}:{number} 存在行尾空白。")

        if path.suffix.lower() != ".md":
            continue

        for start, language, _ in iter_code_fences(text):
            if language == "\x00unclosed":
                validation.error(f"{relative}:{start} 围栏代码块未闭合。")
            else:
                validation.check(
                    bool(language),
                    f"{relative}:{start} 围栏代码块缺少语言标注（用 text 表示纯输出）。",
                )

        for number, line in strip_code_fences(text):
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            for cell in split_table_cells(stripped):
                if cell.count("`") % 2:
                    validation.error(
                        f"{relative}:{number} 表格行内代码跨越了单元格边界，代码中的 `|` 需要写成 `\\|`。"
                    )
                    break

        if str(relative) in DUPLICATE_HEADING_EXEMPT:
            continue
        duplicates: dict[tuple[int, str], int] = {}
        for _, line in strip_code_fences(text):
            match = HEADING.match(line)
            if match:
                key = (len(match.group(1)), match.group(2).strip())
                duplicates[key] = duplicates.get(key, 0) + 1
        for (level, title), count in duplicates.items():
            validation.check_warn(
                count == 1,
                f"{relative} 存在重复标题（{'#' * level} {title}）×{count}，锚点会被自动加后缀。",
            )


def validate_release_files(validation: Validation, catalog: dict[Path, dict[str, str]]) -> None:
    """检查发布所需文件、许可证一致性、占位符和高置信度凭据模式。"""
    required = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "NOTICE",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "LICENSE",
        REPO_ROOT / "VERSION",
        REPO_ROOT / "CHANGELOG.md",
        SKILL_DIR / "NOTICE",
        SKILL_DIR / "LICENSE",
        REPO_ROOT / ".github" / "workflows" / "validate.yml",
        REPO_ROOT / "scripts" / "install.ps1",
        REPO_ROOT / "scripts" / "install.sh",
    ]
    for path in required:
        validation.check(path.is_file(), f"缺少发布文件：{path.relative_to(REPO_ROOT)}")

    root_license = read_text(REPO_ROOT / "LICENSE", validation)
    skill_license = read_text(SKILL_DIR / "LICENSE", validation)
    validation.check(root_license == skill_license, "根目录 LICENSE 与 Skill 内 LICENSE 不一致。")
    validation.check(
        "GNU AFFERO GENERAL PUBLIC LICENSE" in root_license, "LICENSE 不是完整的 GNU AGPL 文本。"
    )

    root_notice = read_text(REPO_ROOT / "NOTICE", validation)
    skill_notice = read_text(SKILL_DIR / "NOTICE", validation)
    validation.check(root_notice == skill_notice, "根目录 NOTICE 与 Skill 内 NOTICE 不一致。")

    installer = REPO_ROOT / "scripts" / "install.ps1"
    if installer.is_file():
        validation.check(
            installer.read_bytes().startswith(b"\xef\xbb\xbf"),
            "scripts/install.ps1 应保留 UTF-8 BOM，以兼容 Windows PowerShell 5.1 的中文文本。",
        )

    version_path = REPO_ROOT / "VERSION"
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    if version_path.is_file() and changelog_path.is_file():
        version = read_text(version_path, validation).strip()
        validation.check(
            bool(re.fullmatch(r"\d+\.\d+\.\d+", version)),
            f"VERSION 必须是 SemVer（如 1.2.0），实际为 {version!r}。",
        )
        changelog = read_text(changelog_path, validation)
        validation.check(
            f"## [{version}]" in changelog,
            f"CHANGELOG.md 缺少与 VERSION（{version}）对应的条目标题 `## [{version}]`。",
        )

    local_playbooks = [path for path, meta in catalog.items() if meta.get("source") == "local"]
    authored_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "NOTICE",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "CHANGELOG.md",
        SKILL_DIR / "SKILL.md",
        REFERENCES_DIR / "playbook-index.md",
        REPO_ROOT / "scripts" / "install.ps1",
        REPO_ROOT / "scripts" / "install.sh",
        *local_playbooks,
    ]
    for path in authored_files:
        if not path.is_file():
            continue
        match = PLACEHOLDER.search(read_text(path, validation))
        validation.check(
            not match,
            f"发现未完成占位符：{path.relative_to(REPO_ROOT)} -> {match.group(0) if match else ''}",
        )

    for path in iter_repo_files():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = read_text(path, validation)
        # NOTICE 保留必要的上游署名；校验器本身按定义包含该字面量。
        if path.name != "NOTICE" and path.resolve() != SELF_PATH:
            validation.check(
                not FORBIDDEN_PRODUCT_MARKER.search(text),
                f"发现旧产品标识：{path.relative_to(REPO_ROOT)}",
            )
        for label, pattern in SECRET_PATTERNS.items():
            validation.check(not pattern.search(text), f"发现疑似 {label}：{path.relative_to(REPO_ROOT)}")


def main(argv: list[str] | None = None) -> int:
    """按依赖顺序执行所有验证，并以单一退出码交给本地终端或 CI。"""
    parser = argparse.ArgumentParser(description="校验 computer-repair-skill 仓库。")
    parser.add_argument("--strict", action="store_true", help="warning 也视为失败（CI 用）")
    args = parser.parse_args(argv)

    configure_console_encoding()
    validation = Validation()
    catalog = collect_playbook_metadata(validation)

    checks = (
        ("Skill 元数据", lambda: validate_skill_metadata(validation)),
        ("Playbook frontmatter", lambda: validate_playbooks(validation, catalog)),
        ("远程执行", lambda: validate_remote_execution(validation)),
        ("平台路由", lambda: validate_platform_routing(validation, catalog)),
        ("链接与锚点", lambda: validate_links(validation)),
        ("路由索引", lambda: validate_index_consistency(validation, catalog)),
        ("工具契约", lambda: validate_tool_references(validation)),
        ("分类登记", lambda: validate_registry_consistency(validation, catalog)),
        ("格式卫生", lambda: validate_formatting(validation)),
        ("发布完整性", lambda: validate_release_files(validation, catalog)),
    )
    for label, check in checks:
        try:
            check()
        except Exception as exc:
            # 单个检查崩溃不能丢弃其余检查的结论：CI 里一条 traceback
            # 比一份完整问题清单难用得多。
            validation.error(f"{label}检查因内部异常中断：{type(exc).__name__}: {exc}")

    return validation.finish(strict=args.strict, total=len(catalog))


if __name__ == "__main__":
    sys.exit(main())
