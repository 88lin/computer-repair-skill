#!/usr/bin/env python3
"""验证 Computer Repair Skill 的结构、来源、链接和发布完整性。"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACT_DATA = REPO_ROOT / "tools" / "extract_data.py"
SKILL_DIR = REPO_ROOT / "skills" / "computer-repair-skill"
REFERENCES_DIR = SKILL_DIR / "references"
EXPECTED_PLAYBOOK_COUNT = 62
EXPECTED_BUNDLED_COUNT = 37
REQUIRED_SKILL_FIELDS = {"name", "description", "version"}
OPTIONAL_SKILL_FIELDS = {"when_to_use"}
MAX_SKILL_DESCRIPTION_CHARS = 600
MAX_SKILL_DESCRIPTION_WORDS = 80
# Claude Code 把 description 与 when_to_use 一起注入系统提示，超出上限会被截断。
MAX_SKILL_TRIGGER_CHARS = 1536
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
MAX_PLAYBOOK_DESCRIPTION_CHARS = 120
OPTIONAL_PLAYBOOK_FIELDS = {"emoji"}
EXPECTED_LOCAL_PLAYBOOKS = {
    "playbook-windows-application-cleanup.md",
    "playbook-windows-application-migration.md",
    "playbook-windows-application-lifecycle-audit.md",
    "playbook-windows-large-folder-management.md",
    "playbook-windows-migration-history-recovery.md",
    "playbook-windows-browser-policy-audit.md",
    "playbook-windows-configuration-review.md",
    "playbook-windows-data-recovery-triage.md",
    "playbook-linux-disk-space-recovery.md",
    "playbook-linux-network-diagnostics.md",
    "playbook-linux-performance-forensics.md",
    "playbook-windows-persistence-audit.md",
    "playbook-windows-disk-space-recovery.md",
    "playbook-windows-network-diagnostics.md",
    "playbook-windows-performance-forensics.md",
    "playbook-windows-storage-inventory.md",
    "playbook-windows-driver-lifecycle-audit.md",
    "playbook-windows-av-input-triage.md",
    "playbook-windows-boot-failure-triage.md",
    "playbook-windows-winre-system-repair.md",
    "playbook-windows-bitlocker-recovery-triage.md",
    "playbook-windows-partition-resize-audit.md",
    "playbook-windows-new-device-intake.md",
    "playbook-windows-hardware-maintenance-safety.md",
    "playbook-windows-uninstall-residue-cleanup.md",
}
REQUIRED_PLAYBOOK_FIELDS = {
    "name",
    "description",
    "platform",
    "last_reviewed",
    "author",
    "source",
}
ALLOWED_PLATFORMS = {"all", "linux", "macos", "windows"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
INDEX_ROW = re.compile(r"(?m)^\|\s*`([^`]+)`\s*\|.*?\]\(([^)\s]+)\)\s*\|\s*$")
INDEX_SECTION = re.compile(r"(?ms)^## (.+?)\r?\n(.*?)(?=^## |\Z)")
README_SUMMARY_ROW = re.compile(r"(?m)^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|")
INDEX_TABLE_HEADER = re.compile(r"^\|\s*Playbook\s*\|")
TOOL_SECTION = re.compile(r"(?ms)^## Tools referenced\s*(.*?)(?=^## |\Z)")
TOOL_BULLET = re.compile(r"(?m)^\s*-\s+`([a-z][a-z0-9_]*)`")
TOOL_ALIAS = re.compile(r"`([a-z][a-z0-9_]*)`")
REMOTE_SHELL_EXECUTION = re.compile(
    r"(?im)^\s*(?:curl|wget|irm|iwr|Invoke-WebRequest)\b[^\r\n]*\|\s*(?:bash|sh|pwsh|powershell|iex)\b"
)
REMOTE_SHELL_COMMAND_SUBSTITUTION = re.compile(
    r"(?im)(?:/bin/)?(?:bash|sh)\s+-c\s+[\"']?\$\(\s*(?:curl|wget)\b"
)
PLACEHOLDER = re.compile(r"\b(?:TODO|FIXME|TBD)\b|YOUR_GITHUB_USER|<owner>", re.IGNORECASE)
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "private key": re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
}
FORBIDDEN_PRODUCT_MARKER = re.compile(r"noah", re.IGNORECASE)
PRODUCT_MARKER_SCAN_EXCLUSIONS = {Path(__file__).resolve()}


def is_single_emoji(value: str) -> bool:
    """Accept one emoji, optionally followed by a variation selector."""
    value = value.strip()
    if not value or any(character.isspace() for character in value):
        return False

    base = [
        character
        for character in value
        if ord(character) not in {0xFE0E, 0xFE0F, 0x200D}
    ]
    if len(base) != 1:
        return False

    codepoint = ord(base[0])
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2300 <= codepoint <= 0x23FF
        or 0x2600 <= codepoint <= 0x27BF
    )


def configure_console_encoding() -> None:
    """在 Windows CI 等非 UTF-8 终端中稳定输出中文验证结果。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


class Validation:
    """集中收集错误，确保一次运行能报告全部问题。"""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        """条件不满足时记录一条稳定、可定位的中文错误。"""
        if not condition:
            self.errors.append(message)

    def finish(self) -> int:
        """打印最终结果并返回适合 CI 的退出码。"""
        if self.errors:
            print(f"验证失败，共 {len(self.errors)} 项：")
            for error in self.errors:
                print(f"  - {error}")
            return 1

        print(f"验证通过：{EXPECTED_PLAYBOOK_COUNT} 个 Playbook，结构、索引、链接、许可证和安全扫描均正常。")
        return 0


def read_text(path: Path, validation: Validation) -> str:
    """按 UTF-8 读取文本；编码或读取失败会进入统一错误列表。"""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        validation.errors.append(f"无法按 UTF-8 读取 {path.relative_to(REPO_ROOT)}：{exc}")
        return ""


def parse_frontmatter(path: Path, validation: Validation) -> dict[str, str]:
    """解析本项目使用的简单单层 YAML frontmatter，不引入第三方依赖。"""
    text = read_text(path, validation)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        validation.errors.append(f"缺少 frontmatter：{path.relative_to(REPO_ROOT)}")
        return {}

    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        validation.errors.append(f"frontmatter 未闭合：{path.relative_to(REPO_ROOT)}")
        return {}

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            validation.errors.append(f"frontmatter 行格式错误：{path.relative_to(REPO_ROOT)} -> {line}")
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata


def find_playbooks() -> list[Path]:
    """返回可执行 Playbook，排除路由索引和编写规范。"""
    excluded = {"playbook-authoring.md", "playbook-index.md"}
    return sorted(path for path in REFERENCES_DIR.glob("playbook-*.md") if path.name not in excluded)


def validate_skill_metadata(validation: Validation) -> None:
    """检查 Skill 触发元数据、长度和 Codex 展示元数据。"""
    skill_path = SKILL_DIR / "SKILL.md"
    metadata = parse_frontmatter(skill_path, validation)
    allowed = REQUIRED_SKILL_FIELDS | OPTIONAL_SKILL_FIELDS
    unexpected = set(metadata) - allowed
    missing = REQUIRED_SKILL_FIELDS - set(metadata)
    validation.check(
        not unexpected,
        "SKILL.md frontmatter 只允许 " + "、".join(sorted(allowed)) + f"；发现多余字段：{', '.join(sorted(unexpected))}。",
    )
    validation.check(not missing, f"SKILL.md frontmatter 缺少字段：{', '.join(sorted(missing))}。")
    validation.check(metadata.get("name") == "computer-repair-skill", "SKILL.md 的 name 必须是 computer-repair-skill。")
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

    when_to_use = metadata.get("when_to_use", "").strip()
    trigger_chars = len(description) + len(when_to_use)
    validation.check(
        trigger_chars <= MAX_SKILL_TRIGGER_CHARS,
        f"SKILL.md 的 description 与 when_to_use 合计 {trigger_chars} 字符，"
        f"超过宿主注入上限 {MAX_SKILL_TRIGGER_CHARS} 字符，会被截断。",
    )

    skill_lines = read_text(skill_path, validation).splitlines()
    validation.check(len(skill_lines) <= 500, f"SKILL.md 超过 500 行：{len(skill_lines)}。")

    agent_path = SKILL_DIR / "agents" / "openai.yaml"
    agent_text = read_text(agent_path, validation)
    for field in ("display_name:", "short_description:", "default_prompt:"):
        validation.check(field in agent_text, f"agents/openai.yaml 缺少 {field[:-1]}。")
    validation.check("$computer-repair-skill" in agent_text, "agents/openai.yaml 的 default_prompt 必须显式调用 Skill。")

    skill_version = metadata.get("version", "")
    validation.check(
        bool(SEMVER.match(skill_version)),
        f"SKILL.md 的 version 必须是 MAJOR.MINOR.PATCH：{skill_version or '缺失'}。",
    )
    agent_version_match = re.search(r"(?m)^\s*version:\s*[\"']?([^\"'\s]+)[\"']?\s*$", agent_text)
    agent_version = agent_version_match.group(1) if agent_version_match else ""
    validation.check(
        bool(agent_version), "agents/openai.yaml 缺少 version，无法与 SKILL.md 对齐。"
    )
    validation.check(
        agent_version == skill_version,
        f"版本号不一致：SKILL.md 为 {skill_version or '缺失'}，agents/openai.yaml 为 {agent_version or '缺失'}。",
    )

    changelog_path = REPO_ROOT / "CHANGELOG.md"
    changelog_text = read_text(changelog_path, validation)
    validation.check(
        f"## [{skill_version}]" in changelog_text,
        f"CHANGELOG.md 缺少当前版本条目：## [{skill_version}]。",
    )


def validate_playbooks(validation: Validation) -> None:
    """检查 Playbook 数量、元数据、名称唯一性与上游/扩展边界。"""
    playbooks = find_playbooks()
    validation.check(
        len(playbooks) == EXPECTED_PLAYBOOK_COUNT,
        f"可执行 Playbook 应为 {EXPECTED_PLAYBOOK_COUNT} 个，实际为 {len(playbooks)} 个。",
    )

    names: dict[str, Path] = {}
    descriptions: dict[str, Path] = {}
    bundled_count = 0
    local_files: set[str] = set()

    for path in playbooks:
        metadata = parse_frontmatter(path, validation)
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

        description = metadata.get("description", "").strip()
        validation.check(bool(description), f"{path.name} 缺少非空 description。")
        validation.check(
            len(description) <= MAX_PLAYBOOK_DESCRIPTION_CHARS,
            f"{path.name} 的 description 过长：{len(description)} 字符，最多 {MAX_PLAYBOOK_DESCRIPTION_CHARS} 字符。",
        )
        description_key = re.sub(r"\s+", " ", description).casefold()
        if description_key in descriptions:
            validation.errors.append(
                f"Playbook description 重复：{path.name}、{descriptions[description_key].name}。"
            )
        elif description_key:
            descriptions[description_key] = path

        name = metadata.get("name", "")
        if name in names:
            validation.errors.append(f"Playbook name 重复：{name}（{names[name].name}、{path.name}）。")
        elif name:
            names[name] = path

        platform = metadata.get("platform")
        validation.check(platform in ALLOWED_PLATFORMS, f"{path.name} 的 platform 无效：{platform}。")

        reviewed = metadata.get("last_reviewed", "")
        try:
            date.fromisoformat(reviewed)
        except ValueError:
            validation.errors.append(f"{path.name} 的 last_reviewed 不是 YYYY-MM-DD：{reviewed}。")

        source = metadata.get("source")
        if source == "bundled":
            bundled_count += 1
            validation.check(metadata.get("author") == "upstream-maintainers", f"{path.name} 的上游 author 应为 upstream-maintainers。")
            validation.check("emoji" in metadata, f"{path.name} 应保留 bundled 上游 Playbook 的 emoji。")
        elif source == "local":
            local_files.add(path.name)
            validation.check(
                metadata.get("author") == "computer-repair-skill-maintainers",
                f"{path.name} 的本地扩展 author 无效。",
            )
            body = read_text(path, validation)
            validation.check("## Verification" in body, f"{path.name} 缺少 Verification 段落。")
            validation.check("## Escalation" in body, f"{path.name} 缺少 Escalation 段落。")
        else:
            validation.errors.append(f"{path.name} 的 source 必须是 bundled 或 local。")

        body = read_text(path, validation)
        validation.check(
            not REMOTE_SHELL_EXECUTION.search(body)
            and not REMOTE_SHELL_COMMAND_SUBSTITUTION.search(body),
            f"{path.name} 包含不允许的远程脚本直接执行；请先下载、审阅并在确认后执行本地文件。",
        )

    validation.check(
        bundled_count == EXPECTED_BUNDLED_COUNT,
        f"上游 Playbook 应为 {EXPECTED_BUNDLED_COUNT} 个，实际为 {bundled_count} 个。",
    )
    validation.check(
        local_files == EXPECTED_LOCAL_PLAYBOOKS,
        "本地扩展文件集合不符合预期：" + ", ".join(sorted(local_files)),
    )


def normalize_link_target(raw_target: str) -> str:
    """移除 Markdown 链接标题、尖括号和锚点，得到本地路径。"""
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    return unquote(target.split("#", 1)[0])


def validate_links(validation: Validation) -> None:
    """检查全部本地 Markdown 链接，并确认路由索引覆盖全部 Playbook。"""
    for path in sorted(REPO_ROOT.rglob("*.md")):
        text = read_text(path, validation)
        for raw_target in MARKDOWN_LINK.findall(text):
            target = normalize_link_target(raw_target)
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            resolved = (path.parent / target).resolve()
            validation.check(resolved.exists(), f"本地链接不存在：{path.relative_to(REPO_ROOT)} -> {target}")

    index_path = REFERENCES_DIR / "playbook-index.md"
    index_text = read_text(index_path, validation)
    indexed = {
        Path(normalize_link_target(target)).name
        for target in MARKDOWN_LINK.findall(index_text)
        if normalize_link_target(target).startswith("playbook-")
    }
    actual = {path.name for path in find_playbooks()}
    missing = actual - indexed
    extra = indexed - actual
    validation.check(not missing, "路由索引缺少：" + ", ".join(sorted(missing)))
    validation.check(not extra, "路由索引包含不存在的 Playbook：" + ", ".join(sorted(extra)))

    metadata_by_file = {
        path.name: parse_frontmatter(path, validation).get("name", "")
        for path in find_playbooks()
    }
    indexed_rows: dict[str, str] = {}
    indexed_names: dict[str, str] = {}
    for match in INDEX_ROW.finditer(index_text):
        name, raw_target = match.groups()
        target = Path(normalize_link_target(raw_target)).name
        if target in indexed_rows:
            validation.errors.append(f"路由索引重复登记：{target}。")
        indexed_rows[target] = name
        if name in indexed_names:
            validation.errors.append(f"路由索引名称重复：{name}。")
        indexed_names[name] = target

    for filename, name in indexed_rows.items():
        if filename in metadata_by_file:
            validation.check(
                name == metadata_by_file[filename],
                f"路由索引名称与 frontmatter 不一致：{filename} -> {name}（应为 {metadata_by_file[filename]}）。",
            )


def validate_tool_references(validation: Validation) -> None:
    """确保 Playbook 声明的语义工具在契约或平台映射中有定义。"""
    mapping_files = [
        REFERENCES_DIR / "tool-contract.md",
        REFERENCES_DIR / "tools-windows.md",
        REFERENCES_DIR / "tools-macos.md",
        REFERENCES_DIR / "tools-linux.md",
    ]
    mapping_text = "\n".join(read_text(path, validation) for path in mapping_files)
    mapped = set(TOOL_ALIAS.findall(mapping_text))

    for path in find_playbooks():
        text = read_text(path, validation)
        section = TOOL_SECTION.search(text)
        if not section:
            continue
        for tool in sorted(set(TOOL_BULLET.findall(section.group(1)))):
            validation.check(
                tool in mapped,
                f"{path.name} 引用了未登记的工具别名：{tool}。",
            )


def validate_readme_summary(validation: Validation) -> None:
    """确保 README 的分类数量跟随路由索引，而不是停留在旧版本。"""
    index_text = read_text(REFERENCES_DIR / "playbook-index.md", validation)
    index_counts = {
        heading: len(INDEX_ROW.findall(body))
        for heading, body in INDEX_SECTION.findall(index_text)
        if heading != "未命中专项流程"
    }

    readme_text = read_text(REPO_ROOT / "README.md", validation)
    readme_counts = {
        category: int(count)
        for category, count in README_SUMMARY_ROW.findall(readme_text)
        if category in index_counts
    }
    validation.check(
        readme_counts == index_counts,
        "README 的 Playbook 分类数量与路由索引不一致。",
    )
    validation.check(
        sum(readme_counts.values()) == EXPECTED_PLAYBOOK_COUNT,
        f"README 的 Playbook 分类合计应为 {EXPECTED_PLAYBOOK_COUNT}，实际为 {sum(readme_counts.values())}。",
    )


def validate_index_table_shape(validation: Validation) -> None:
    """确保路由索引的每张表都用同一组表头，避免某些分类漏掉平台或症状列。"""
    index_text = read_text(REFERENCES_DIR / "playbook-index.md", validation)
    headers = [line.strip() for line in index_text.splitlines() if INDEX_TABLE_HEADER.match(line)]
    validation.check(bool(headers), "playbook-index.md 未找到任何路由表表头。")
    distinct = sorted(set(headers))
    validation.check(
        len(distinct) <= 1,
        "playbook-index.md 的路由表表头不一致：" + " / ".join(distinct),
    )

    expected_columns = len(headers[0].strip("|").split("|")) if headers else 0
    for match in INDEX_ROW.finditer(index_text):
        row = match.group(0).strip()
        columns = len(row.strip("|").split("|"))
        validation.check(
            columns == expected_columns,
            f"路由索引行的列数应为 {expected_columns}，实际为 {columns}：{row[:60]}",
        )


def load_site_data(validation: Validation) -> dict:
    """从站点数据文件中取出内嵌的 JSON，供一致性检查使用。"""
    path = REPO_ROOT / "docs" / "assets" / "js" / "playbooks.js"
    text = read_text(path, validation)
    if not text:
        return {}
    marker = "window.CRS_DATA"
    if marker not in text:
        validation.errors.append("docs/assets/js/playbooks.js 缺少 window.CRS_DATA。")
        return {}
    payload = text[text.index("{", text.index(marker)) :].rstrip().rstrip(";")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        validation.errors.append(f"docs/assets/js/playbooks.js 不是合法 JSON：{exc}")
        return {}


def validate_site_data(validation: Validation) -> None:
    """站点数据必须与 Playbook frontmatter 和路由索引同步，否则网页会展示过期信息。"""
    data = load_site_data(validation)
    if not data:
        return

    entries = data.get("playbooks", [])
    validation.check(
        data.get("total") == EXPECTED_PLAYBOOK_COUNT and len(entries) == EXPECTED_PLAYBOOK_COUNT,
        f"站点数据的 Playbook 数量应为 {EXPECTED_PLAYBOOK_COUNT}，"
        f"实际 total={data.get('total')}、条目 {len(entries)} 个。",
    )

    frontmatter = {path.name: parse_frontmatter(path, validation) for path in find_playbooks()}
    site_files = {entry.get("file", "") for entry in entries}
    missing = set(frontmatter) - site_files
    extra = site_files - set(frontmatter)
    validation.check(not missing, "站点数据缺少 Playbook：" + ", ".join(sorted(missing)))
    validation.check(not extra, "站点数据包含不存在的 Playbook：" + ", ".join(sorted(extra)))

    for entry in entries:
        filename = entry.get("file", "")
        meta = frontmatter.get(filename)
        if not meta:
            continue
        for field in ("last_reviewed", "platform", "source"):
            validation.check(
                entry.get(field) == meta.get(field),
                f"站点数据与 frontmatter 不一致：{filename} 的 {field} 为 {entry.get(field)}，应为 {meta.get(field)}。",
            )
        route = meta.get("name", "")
        validation.check(
            entry.get("route") == route,
            f"站点数据的 route 与 frontmatter name 不一致：{filename} -> {entry.get('route')}（应为 {route}）。",
        )
        # id 是 DOM/锚点用的 slug，把 name 里的斜杠换成连字符。
        validation.check(
            entry.get("id") == route.replace("/", "-"),
            f"站点数据的 id 应为 name 的 slug 形式：{filename} -> {entry.get('id')}"
            f"（应为 {route.replace('/', '-')}）。",
        )

    index_text = read_text(REFERENCES_DIR / "playbook-index.md", validation)
    index_routes = {name for name, _ in INDEX_ROW.findall(index_text)}
    site_routes = {entry.get("route", "") for entry in entries}
    validation.check(
        index_routes == site_routes,
        "路由索引与站点数据的路由集合不一致：仅索引有 "
        + ", ".join(sorted(index_routes - site_routes))
        + "；仅站点有 "
        + ", ".join(sorted(site_routes - index_routes)),
    )

    index_counts = {
        heading: len(INDEX_ROW.findall(body))
        for heading, body in INDEX_SECTION.findall(index_text)
        if heading != "未命中专项流程"
    }
    site_counts = {item.get("zh", ""): item.get("count") for item in data.get("categories", [])}
    validation.check(
        site_counts == index_counts,
        "站点分类计数与路由索引不一致。",
    )


def validate_generated_site_data(validation: Validation) -> None:
    """官网压缩数据必须由仓库内的可重复生成器产生。"""
    validation.check(EXTRACT_DATA.is_file(), "缺少 tools/extract_data.py，官网数据无法重复生成。")
    if not EXTRACT_DATA.is_file():
        return
    try:
        result = subprocess.run(
            [sys.executable, str(EXTRACT_DATA), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as exc:
        validation.errors.append(f"无法运行 tools/extract_data.py --check：{exc}")
        return
    validation.check(
        result.returncode == 0,
        "docs/assets/js/playbooks.js 不是 tools/extract_data.py 的最新生成结果："
        + (result.stderr.strip() or result.stdout.strip()),
    )


def validate_review_regressions(validation: Validation) -> None:
    """防止已修复的平台命令和敏感数据处理问题回归。"""
    wifi = read_text(REFERENCES_DIR / "playbook-setup-wifi-profile.md", validation)
    validation.check("SSID_HERE" not in wifi, "Wi-Fi Playbook 仍包含未替换的 SSID_HERE 占位符。")
    validation.check("wlan-<ssid>" not in wifi, "Wi-Fi 临时路径不能直接使用用户提供的 SSID。")
    validation.check(
        "SecurityElement]::Escape" in wifi and "finally" in wifi,
        "Wi-Fi XML 必须转义用户输入，并在失败时清理临时秘密。",
    )

    browser = read_text(REFERENCES_DIR / "playbook-browser-security-audit.md", validation)
    validation.check("/tmp/ld.db" not in browser, "浏览器审计不能使用固定的 /tmp/ld.db。")
    validation.check("mktemp" in browser and "trap" in browser, "浏览器审计必须使用唯一临时文件并注册清理 trap。")

    credentials = read_text(REFERENCES_DIR / "playbook-credential-cleanup.md", validation)
    validation.check("Check size of" not in credentials, "凭据清理不能通过 Login Data 文件大小推断密码数量。")
    validation.check("COUNT(*)" in credentials, "凭据清理必须按数据库行数统计保存的密码。")

    health = read_text(REFERENCES_DIR / "playbook-health-baseline-check.md", validation)
    validation.check("State = 1" in health and "State = 2" in health, "健康基线必须把 macOS 防火墙 State 1 和 State 2 都视为启用。")

    china_models = read_text(REFERENCES_DIR / "playbook-setup-openclaw-china-models.md", validation)
    validation.check(
        "doubao-seed-1-8-251228" not in china_models,
        "国产模型 Playbook 仍包含已过时的 doubao-seed-1-8-251228。",
    )
    validation.check(
        "openclaw models status" in china_models and "dated model ID" in china_models,
        "国产模型 Playbook 必须要求从当前 catalog 确认模型 ID。",
    )
    validation.check(
        "deepseek-v4-pro-260425" not in china_models and "deepseek-v4-flash-260425" not in china_models,
        "国产模型 Playbook 不能残留带日期的过期 DeepSeek 模型 ID。",
    )

    uninstall = read_text(REFERENCES_DIR / "playbook-setup-openclaw-uninstall.md", validation)
    validation.check("always run 2c and 2d" in uninstall, "OpenClaw --all 成功后仍必须执行 CLI 和桌面应用清理。")
    validation.check("OPENCLAW_CONFIG_PATH" in uninstall and "Refusing to delete" in uninstall, "OpenClaw 自定义路径必须单独处理并做路径安全保护。")
    validation.check("openclaw*.service" in uninstall and "OpenClaw Gateway" in uninstall, "OpenClaw 卸载必须覆盖多 profile 服务和计划任务。")
    validation.check("where.exe openclaw" in uninstall and "which openclaw" not in uninstall, "Windows OpenClaw 验证不能使用 Unix which/redirection。")

    config_reference = read_text(REFERENCES_DIR / "playbook-setup-openclaw-config-reference.md", validation)
    validation.check("typingIndicator" not in config_reference and "resolveSenderNames" not in config_reference, "OpenClaw 配置参考不能包含未注册字段。")

    homebrew = read_text(REFERENCES_DIR / "playbook-setup-homebrew.md", validation)
    validation.check("if [ -z \"$BREW\" ]" in homebrew and "stop before editing" in homebrew, "Homebrew 找不到 brew 时必须停止写 profile。")

    updates = read_text(REFERENCES_DIR / "playbook-windows-update-troubleshooting.md", validation)
    validation.check("net stop bits && net start bits" not in updates and "net start wuauserv" in updates, "Windows Update 服务重启不能用失败即短路的 &&。")

    validation.check("profileImported" in wifi and "wlan delete profile" in wifi and "connectivity verification fails" in wifi, "Wi-Fi 连接失败后必须删除已导入的临时 profile。")

    network = read_text(REFERENCES_DIR / "playbook-windows-network-diagnostics.md", validation)
    validation.check("A mismatch is not itself" in network and "a fault" in network, "WinHTTP/WinINET 不一致不能无条件判定为故障。")


def validate_release_files(validation: Validation) -> None:
    """检查发布所需文件、许可证一致性、占位符和高置信度凭据模式。"""
    required = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "NOTICE",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "LICENSE",
        SKILL_DIR / "NOTICE",
        REPO_ROOT / ".github" / "workflows" / "validate.yml",
        REPO_ROOT / "scripts" / "install.ps1",
        REPO_ROOT / "scripts" / "install.sh",
        REPO_ROOT / "tools" / "extract_data.py",
        REPO_ROOT / "tools" / "site_catalog.json",
        REPO_ROOT / "tools" / "site_catalog.json",
    ]
    for path in required:
        validation.check(path.is_file(), f"缺少发布文件：{path.relative_to(REPO_ROOT)}")

    root_license = read_text(REPO_ROOT / "LICENSE", validation)
    skill_license = read_text(SKILL_DIR / "LICENSE", validation)
    validation.check(root_license == skill_license, "根目录 LICENSE 与 Skill 内 LICENSE 不一致。")
    validation.check("GNU AFFERO GENERAL PUBLIC LICENSE" in root_license, "LICENSE 不是完整的 GNU AGPL 文本。")

    root_notice = read_text(REPO_ROOT / "NOTICE", validation)
    skill_notice = read_text(SKILL_DIR / "NOTICE", validation)
    validation.check(root_notice == skill_notice, "根目录 NOTICE 与 Skill 内 NOTICE 不一致。")

    powershell_installer = REPO_ROOT / "scripts" / "install.ps1"
    validation.check(
        powershell_installer.read_bytes().startswith(b"\xef\xbb\xbf"),
        "scripts/install.ps1 应保留 UTF-8 BOM，以兼容 Windows PowerShell 5.1 的中文文本。",
    )

    authored_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "NOTICE",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        SKILL_DIR / "SKILL.md",
        SKILL_DIR / "references" / "playbook-index.md",
        REPO_ROOT / "scripts" / "install.ps1",
        REPO_ROOT / "scripts" / "install.sh",
        REPO_ROOT / "tools" / "extract_data.py",
    ] + [REFERENCES_DIR / name for name in EXPECTED_LOCAL_PLAYBOOKS]

    for path in authored_files:
        text = read_text(path, validation)
        match = PLACEHOLDER.search(text)
        validation.check(not match, f"发现未完成占位符：{path.relative_to(REPO_ROOT)} -> {match.group(0) if match else ''}")

    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {"", ".md", ".py", ".ps1", ".sh", ".yaml", ".yml"}:
            continue
        text = read_text(path, validation)
        # NOTICE preserves required attribution. This validator contains the
        # literal marker by definition, so exclude it from its own scan.
        if path.name != "NOTICE" and path.resolve() not in PRODUCT_MARKER_SCAN_EXCLUSIONS:
            validation.check(
                not FORBIDDEN_PRODUCT_MARKER.search(text),
                f"发现旧产品标识：{path.relative_to(REPO_ROOT)}",
            )
        for label, pattern in SECRET_PATTERNS.items():
            match = pattern.search(text)
            validation.check(not match, f"发现疑似 {label}：{path.relative_to(REPO_ROOT)}")


def main() -> int:
    """按依赖顺序执行所有验证，并以单一退出码交给本地终端或 CI。"""
    configure_console_encoding()
    validation = Validation()
    validate_skill_metadata(validation)
    validate_playbooks(validation)
    validate_links(validation)
    validate_tool_references(validation)
    validate_readme_summary(validation)
    validate_index_table_shape(validation)
    validate_site_data(validation)
    validate_generated_site_data(validation)
    validate_review_regressions(validation)
    validate_release_files(validation)
    return validation.finish()


if __name__ == "__main__":
    sys.exit(main())
