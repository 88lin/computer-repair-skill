#!/usr/bin/env python3
"""验证 Noah Computer Care Skill 的结构、来源、链接和发布完整性。"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "noah-computer-care"
REFERENCES_DIR = SKILL_DIR / "references"
EXPECTED_PLAYBOOK_COUNT = 43
EXPECTED_BUNDLED_COUNT = 37
EXPECTED_LOCAL_PLAYBOOKS = {
    "playbook-linux-disk-space-recovery.md",
    "playbook-linux-network-diagnostics.md",
    "playbook-linux-performance-forensics.md",
    "playbook-windows-disk-space-recovery.md",
    "playbook-windows-network-diagnostics.md",
    "playbook-windows-performance-forensics.md",
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
PLACEHOLDER = re.compile(r"\b(?:TODO|FIXME|TBD)\b|YOUR_GITHUB_USER|<owner>", re.IGNORECASE)
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "private key": re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
}


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
    validation.check(set(metadata) == {"name", "description"}, "SKILL.md frontmatter 只能包含 name 和 description。")
    validation.check(metadata.get("name") == "noah-computer-care", "SKILL.md 的 name 必须是 noah-computer-care。")
    validation.check(bool(metadata.get("description")), "SKILL.md 缺少非空 description。")

    skill_lines = read_text(skill_path, validation).splitlines()
    validation.check(len(skill_lines) <= 500, f"SKILL.md 超过 500 行：{len(skill_lines)}。")

    agent_path = SKILL_DIR / "agents" / "openai.yaml"
    agent_text = read_text(agent_path, validation)
    for field in ("display_name:", "short_description:", "default_prompt:"):
        validation.check(field in agent_text, f"agents/openai.yaml 缺少 {field[:-1]}。")
    validation.check("$noah-computer-care" in agent_text, "agents/openai.yaml 的 default_prompt 必须显式调用 Skill。")


def validate_playbooks(validation: Validation) -> None:
    """检查 Playbook 数量、元数据、名称唯一性与上游/扩展边界。"""
    playbooks = find_playbooks()
    validation.check(
        len(playbooks) == EXPECTED_PLAYBOOK_COUNT,
        f"可执行 Playbook 应为 {EXPECTED_PLAYBOOK_COUNT} 个，实际为 {len(playbooks)} 个。",
    )

    names: dict[str, Path] = {}
    bundled_count = 0
    local_files: set[str] = set()

    for path in playbooks:
        metadata = parse_frontmatter(path, validation)
        missing = REQUIRED_PLAYBOOK_FIELDS - set(metadata)
        validation.check(not missing, f"{path.name} 缺少字段：{', '.join(sorted(missing))}。")

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
            validation.check(metadata.get("author") == "noah-team", f"{path.name} 的上游 author 应为 noah-team。")
        elif source == "local":
            local_files.add(path.name)
            validation.check(
                metadata.get("author") == "noah-computer-care-maintainers",
                f"{path.name} 的本地扩展 author 无效。",
            )
            body = read_text(path, validation)
            validation.check("## Verification" in body, f"{path.name} 缺少 Verification 段落。")
            validation.check("## Escalation" in body, f"{path.name} 缺少 Escalation 段落。")
        else:
            validation.errors.append(f"{path.name} 的 source 必须是 bundled 或 local。")

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
    """检查全部本地 Markdown 链接，并确认路由索引恰好覆盖 43 个 Playbook。"""
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


def validate_release_files(validation: Validation) -> None:
    """检查发布所需文件、许可证一致性、占位符和高置信度凭据模式。"""
    required = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "NOTICE",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "LICENSE",
        REPO_ROOT / ".github" / "workflows" / "validate.yml",
        REPO_ROOT / "scripts" / "install.ps1",
        REPO_ROOT / "scripts" / "install.sh",
    ]
    for path in required:
        validation.check(path.is_file(), f"缺少发布文件：{path.relative_to(REPO_ROOT)}")

    root_license = read_text(REPO_ROOT / "LICENSE", validation)
    skill_license = read_text(SKILL_DIR / "LICENSE", validation)
    validation.check(root_license == skill_license, "根目录 LICENSE 与 Skill 内 LICENSE 不一致。")
    validation.check("GNU AFFERO GENERAL PUBLIC LICENSE" in root_license, "LICENSE 不是完整的 GNU AGPL 文本。")

    authored_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "NOTICE",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        SKILL_DIR / "SKILL.md",
        SKILL_DIR / "references" / "playbook-index.md",
        REPO_ROOT / "scripts" / "install.ps1",
        REPO_ROOT / "scripts" / "install.sh",
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
    validate_release_files(validation)
    return validation.finish()


if __name__ == "__main__":
    sys.exit(main())
