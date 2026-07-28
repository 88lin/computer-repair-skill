#!/usr/bin/env python3
"""跨平台可移植性静态守卫。

前三条规则对应三个真实故障：都只在 CI 的非 Linux 机器上才会炸，在 Linux 上本地
跑一万遍也复现不出来，所以只能靠静态检查在 lint 阶段拦住。第四条是同一类问题在
PowerShell 侧的镜像，目前零违规，纯粹用来防止以后写回来。

1. macOS 自带的 Bash 是 3.2.57（Apple 因为 GPLv3 不再跟进新版本）。它判断
   变量名合法字符用的是 C 库的 `isalnum()`，而 BSD libc 在 UTF-8 locale 下
   会把 0x80-0xFF 当成 Latin-1 字母返回真。于是 `"版本 $skill_version（旧）"`
   里的变量名被解析成 `skill_version\\xef`，在 `set -u` 下直接以
   `skill_version\\xef: unbound variable` 退出。glibc 不会这样，所以同一份
   脚本在 Ubuntu 上完全正常。
   规则：Shell 脚本和工作流的 bash 步骤里，`$var` 后面紧跟非 ASCII 字符时
   必须写成 `${var}`。

2. GitHub Actions 会把 `shell: powershell` 步骤的 run 块写成**不带 BOM** 的
   临时 `.ps1`，Windows PowerShell 5.1 按系统 ANSI 代码页（en-US 镜像是
   CP1252）解码它。CP1252 把 0x91-0x94 映射成 `‘ ’ “ ”`，而 PowerShell 把这些
   排版引号当作字符串定界符 —— 例如「错」的 UTF-8 是 E9 94 99，中间的 0x94
   会变成右双引号，字符串提前闭合，整个脚本解析失败。
   规则：`shell: powershell` 的 run 块必须是纯 ASCII；需要中文断言就另起一个
   `shell: pwsh` 步骤（PowerShell 7 按 UTF-8 读临时脚本，不受影响）。

3. `Path.write_text()` 在 Windows 上默认做行尾翻译，把 `\\n` 写成 `\\r\\n`。
   测试与登记生成器写出的 `.md` 会立刻违反 `.gitattributes` 的 LF 约束，
   校验器随即报「含 CRLF 行尾」。
   规则：`tests/` 下的 `write_text()` 必须显式传 `newline="\\n"`。

4. PowerShell 的裸变量引用 `$name` 会一直吞掉 Unicode 字母（L*）、十进制数字（Nd）
   和组合记号（Mn）；实测 `"$name的"` 展开成空串，而 `Set-StrictMode -Version Latest`
   下直接抛 `The variable '$name的' cannot be retrieved`。全角标点（。：（）—）和空格
   会终止变量名，所以本仓库现有的中文消息恰好都安全 —— 但这完全是运气。
   规则：`.ps1` 与 `shell: pwsh` 的 run 块里，`$var` 紧跟非 ASCII 字母/数字/组合记号时
   必须写成 `${var}`。

用法：python tests/check_portability.py [仓库根目录]
"""

from __future__ import annotations

import ast
import re
import sys
import unicodedata
from pathlib import Path

VAR_BEFORE_NON_ASCII = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)(?=[^\x00-\x7f])")
# PowerShell 允许 `$scope:name` 形式，所以名字部分要接受一个可选的作用域限定符。
PS_VAR_BEFORE_NON_ASCII = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z_][A-Za-z0-9_]*)?)([^\x00-\x7f])")
# PowerShell 判定「还算变量名」的 Unicode 类别，实测得出。
PS_NAME_CATEGORIES = ("Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Mn")
STEP_START = re.compile(r"^(?P<indent>[ ]*)-[ ]+name:")
BASH_SHELLS = {"", "bash", "sh"}
POWERSHELL_SHELLS = {"powershell"}
PWSH_SHELLS = {"pwsh"}


def iter_steps(lines: list[str]) -> list[tuple[int, int, int]]:
    """切出工作流里的每个步骤，返回 (起始行下标, 结束行下标, 短横线缩进)。"""
    steps: list[tuple[int, int, int]] = []
    index = 0
    while index < len(lines):
        match = STEP_START.match(lines[index])
        if match is None:
            index += 1
            continue
        dash_indent = len(match.group("indent"))
        end = index + 1
        while end < len(lines):
            line = lines[end]
            if line.strip() and len(line) - len(line.lstrip()) <= dash_indent:
                break
            end += 1
        steps.append((index, end, dash_indent))
        index = end
    return steps


def step_shell_and_run(
    lines: list[str], start: int, end: int, dash_indent: int
) -> tuple[str, int, list[str]]:
    """取出一个步骤声明的 shell 与 run 块正文。没有 run 块时返回空正文。"""
    key_indent = dash_indent + 2
    shell = ""
    run_line = -1
    for index in range(start, end):
        line = lines[index]
        if not line.strip() or len(line) - len(line.lstrip()) != key_indent:
            continue
        stripped = line.strip()
        if stripped.startswith("shell:"):
            shell = stripped.split(":", 1)[1].strip().strip("\"'")
        elif stripped.startswith("run:"):
            run_line = index
    if run_line < 0:
        return shell, -1, []
    body: list[str] = []
    for index in range(run_line + 1, end):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip()) <= key_indent:
            break
        body.append(line)
    return shell, run_line, body


def check_braced_variables(path: Path, text: str, offset: int = 0) -> list[str]:
    """规则 1：变量引用紧跟非 ASCII 字符时必须带花括号。"""
    problems = []
    for number, line in enumerate(text.splitlines(), start=1 + offset):
        for match in VAR_BEFORE_NON_ASCII.finditer(line):
            name = match.group(1)
            problems.append(
                f"{path}:{number}: `${name}` 后面紧跟非 ASCII 字符，"
                f"macOS 的 Bash 3.2 会把它并进变量名；请写成 `${{{name}}}`。\n"
                f"    {line.strip()}"
            )
    return problems


def check_ascii_only(path: Path, lines: list[str], first_line: int) -> list[str]:
    """规则 2：Windows PowerShell 5.1 步骤的 run 块必须是纯 ASCII。"""
    problems = []
    for offset, line in enumerate(lines):
        bad = [char for char in line if ord(char) > 127]
        if not bad:
            continue
        problems.append(
            f"{path}:{first_line + offset}: `shell: powershell` 的 run 块出现非 ASCII 字符 "
            f"{''.join(sorted(set(bad)))}；Windows PowerShell 5.1 会按 ANSI 代码页解码这段临时脚本，"
            f"中文里的 0x91-0x94 字节会变成排版引号并提前闭合字符串。"
            f"请把这段断言挪到 `shell: pwsh` 步骤。\n    {line.strip()}"
        )
    return problems


def check_powershell_braced_variables(path: Path, text: str, offset: int = 0) -> list[str]:
    """规则 4：PowerShell 裸变量名会吞掉 Unicode 字母/数字/组合记号。"""
    problems = []
    for number, line in enumerate(text.splitlines(), start=1 + offset):
        for match in PS_VAR_BEFORE_NON_ASCII.finditer(line):
            name, following = match.group(1), match.group(2)
            category = unicodedata.category(following)
            if category not in PS_NAME_CATEGORIES:
                continue
            problems.append(
                f"{path}:{number}: `${name}` 后面紧跟 {following!r}（Unicode 类别 {category}），"
                f"PowerShell 会把它并进变量名；`Set-StrictMode -Version Latest` 下会抛"
                f"「cannot be retrieved」。请写成 `${{{name}}}`。\n    {line.strip()}"
            )
    return problems


def check_write_text_newline(path: Path, text: str) -> list[str]:
    """规则 3：write_text() 必须显式指定 LF，否则 Windows 会写出 CRLF。"""
    problems = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr != "write_text":
            continue
        if any(keyword.arg == "newline" for keyword in node.keywords):
            continue
        problems.append(
            f"{path}:{node.lineno}: write_text() 没有显式 newline；Windows 上会把 \\n 写成 \\r\\n，"
            f'违反 .gitattributes 的 LF 约束。请加 newline="\\n"。'
        )
    return problems


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    problems: list[str] = []
    checked = 0

    for script in sorted((root / "scripts").glob("*.sh")):
        checked += 1
        problems += check_braced_variables(script.relative_to(root), script.read_text(encoding="utf-8"))

    for script in sorted((root / "scripts").glob("*.ps1")):
        checked += 1
        # 这两个脚本带 UTF-8 BOM，用 utf-8-sig 读，否则 BOM 会进第一行。
        problems += check_powershell_braced_variables(
            script.relative_to(root), script.read_text(encoding="utf-8-sig")
        )

    workflows = sorted((root / ".github" / "workflows").glob("*.yml"))
    for workflow in workflows:
        checked += 1
        relative = workflow.relative_to(root)
        lines = workflow.read_text(encoding="utf-8").splitlines()
        for start, end, dash_indent in iter_steps(lines):
            shell, run_line, body = step_shell_and_run(lines, start, end, dash_indent)
            if run_line < 0:
                continue
            if shell in BASH_SHELLS:
                problems += check_braced_variables(relative, "\n".join(body), offset=run_line + 1)
            elif shell in POWERSHELL_SHELLS:
                problems += check_ascii_only(relative, body, run_line + 2)
            elif shell in PWSH_SHELLS:
                problems += check_powershell_braced_variables(relative, "\n".join(body), offset=run_line + 1)

    for module in sorted((root / "tests").glob("*.py")):
        checked += 1
        problems += check_write_text_newline(module.relative_to(root), module.read_text(encoding="utf-8"))

    if problems:
        for problem in problems:
            print(f"[error] {problem}", file=sys.stderr)
        print(
            f"\n可移植性检查失败：{len(problems)} 项问题（已检查 {checked} 个文件）。",
            file=sys.stderr,
        )
        return 1
    print(f"可移植性检查通过：{checked} 个文件，4 条规则全部满足。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
