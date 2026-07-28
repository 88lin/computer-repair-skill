# Changelog

本文件记录本仓库所有值得注意的变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

仓库根目录的 `VERSION` 是版本号的唯一真源；`tests/validate_skill.py`
会交叉核对 `VERSION` 与本文件顶部条目，两者不一致时 CI 失败。

## [Unreleased]

## [1.1.0] - 2026-07-28

首个带版本号的发布。主题是**跨平台正确性**与**可验证性**：把"看起来通过"的校验
换成真正能抓到问题的校验，并修掉一批用户会实际踩到的内容缺陷。

### Added

- `VERSION` 与本 `CHANGELOG.md`：版本号真源 + 变更记录，由校验器交叉核对。
- `tests/playbook_registry.py`：Playbook 登记生成器（仅标准库）。在标记注释之间
  重新生成 `playbook-index.md` 的登记摘要与 `README.md` 的分类计数表，
  支持 `--check`（CI 默认）/ `--write` / `--json` 三种模式。
- Playbook frontmatter 新增 `category` 字段，作为分类归属的唯一真源；
  数量与分类不再需要人工在多处同步。
- `SKILL.md` frontmatter 新增 `license: AGPL-3.0`（扁平单行，Agent Skills 规范允许的可选字段）。
- `SKILL.md` 新增"平台路由硬规则"：禁止把 Windows/Linux 用户路由进 macOS 专属 Playbook。
- `playbook-health-baseline-check.md` 顶部新增平台路由提示块与诚实的 Caveat 段。
- `playbook-local-data-audit.md` 新增跨平台路径映射表、云同步/应用数据表、
  Windows Known Folder 重定向检查与 WSL 路径说明。
- `tool-contract.md` 为 `options` 与 `text_input` 补齐独立登记行。

### Changed

- `tests/validate_skill.py` 重写。行为差异：
  - 删除全部硬编码簿记（Playbook 总数、上游/本地数量、21 项本地文件字面量集合），
    改为从 frontmatter 派生并与登记生成器交叉核对。
  - 新增 error / warning 分级与 `--strict` 开关（CI 用 `--strict`）。
  - 工具契约改为**双向**校验：声明的别名必须已在映射表登记，正文用到的登记别名
    必须声明，且每个 Playbook 至少声明一个已登记别名。
  - 工具别名宇宙改为只从映射表**表格首列**解析，不再把正文里的原始命令
    （`rm`、`sudo`、`nc`、`vm_stat` 等）误认为语义别名。
  - 新增规则：`name` 必须与文件名 slug 一致；`platform` 必须与文件名前缀一致；
    `category` 必须已登记；`last_reviewed` 未来日期报错、超 365 天告警；
    必须存在 `## Tools referenced`；frontmatter 不得出现缩进行（朴素解析器无法处理嵌套）。
  - 新增链接校验：图片链接、`<img>` / `<source>` / `<a>` 的本地路径、Markdown 锚点
    （近似 GitHub slug 算法）。此前 `assets/*.svg` 从未被校验。
  - 新增格式卫生：CRLF、行尾空白、EOF 换行、代码围栏语言标注、围栏未闭合、
    表格行内代码的 `|` 转义、重复标题。
  - 远程执行检查改为**上下文感知**：围栏代码块内命中即报错；散文行命中时，
    若同行含否定语义（`Do not` / `Never` / `禁止` / `不得` 等）则放行 ——
    否则安全策略里"禁止 `irm | iex`"这类红线条款本身会被误判为违规。
    检查范围从 Playbook 扩大到 `SKILL.md` 与全部参考文档。
  - 远程执行正则补齐 `iex (irm ...)`、`New-Object Net.WebClient).DownloadString`、
    `bash <(curl ...)` 三种此前漏检的形态。
- 全部 58 个 Playbook 的代码围栏补齐语言标注（64 处此前未标注）。
- `README.md` 赞助商段落移除无法核实的大模型版本号，改为泛化措辞并保留推广链接。

### Fixed

- **跨平台路由死路（5 处）**：`platform: all` 的 Playbook 把 Windows/Linux 用户
  指向 macOS 专属 Playbook。涉及 `backup-verify-restore` → `setup-backup`、
  `email-connectivity-test` / `health-baseline-check` / `identity-provider-test`
  → `network-diagnostics`、`health-baseline-check` → `disk-space-recovery`。
  现在全部按平台条件路由，或显式标注 macOS 限定并给出其他平台的替代做法。
- **`playbook-health-baseline-check.md` 实质上只对 macOS 可用**：步骤 1–7 只有
  macOS 命令（`softwareupdate --list`、`defaults read ...com.apple.alf`、`tmutil status`），
  且步骤 3 让 Windows 用户执行 Windows 上不存在的 `uptime`。七个步骤现已全部补齐
  三平台等价只读命令。
- **`playbook-windows-update-troubleshooting.md` 的命令在目标平台上跑不通**：
  - `net stop bits && net start bits` 中的 `&&` 在 Windows PowerShell 5.1 不受支持，
    改为 `Restart-Service`。
  - Quick check 使用第三方 `PSWindowsUpdate` 模块的 `Get-WindowsUpdate`
    却未说明来源，改为内置 `Get-HotFix` + 只读 COM 搜索，并注明第三方模块身份。
  - 步骤 4 依赖的 MSDT 疑难解答平台已被 Microsoft 弃用（2023 起重定向，2025 移除平台本身），
    现加入存在性守卫并给出"设置 → 系统 → 疑难解答"替代入口。
- `references/tools-windows.md` 表格行内代码的 `|` 未转义导致该行在 GitHub 上渲染错位。
- 正文使用但未在 `## Tools referenced` 声明的工具别名（`mac-tune-up` 缺 `ui_done`、
  `performance-forensics` 缺三项等），以及 5 个 Playbook 的 `## Tools referenced`
  只有泛化措辞、未声明任何规范别名。
- `playbook-setup-openclaw-uninstall.md` 的删除步骤改为"先列出、再逐项删"，
  并移除盲杀进程的 `kill $(pgrep -f ...)` 写法。
- `playbook-setup-wifi-profile.md` 补齐 Linux NetworkManager 分支，并改用 `nmcli --ask`
  避免 PSK 出现在命令行与 shell 历史中。

## [1.0.0] - 2026-07-26

### Added

- 首次开源发布：58 个可按需加载的 Playbook（37 个改编自上游仓库，21 个本地新增），
  覆盖 Windows / macOS / Linux 的诊断、修复、清理、恢复、配置与加固。
- `SKILL.md` 主流程、`references/safety-policy.md` 安全红线、
  `references/tool-contract.md` 工具契约、三份平台工具映射表。
- `scripts/install.sh` 与 `scripts/install.ps1` 安装器（原子暂存 + 失败回滚，
  默认拒绝覆盖，`--force` 才备份更新）。
- `tests/validate_skill.py` 结构校验器与 GitHub Actions 验证流水线。
- AGPL-3.0 许可证；上游与第三方署名记录在 `NOTICE`。

[Unreleased]: https://github.com/88lin/computer-repair-skill/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/88lin/computer-repair-skill/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/88lin/computer-repair-skill/releases/tag/v1.0.0
