# Changelog

本文件记录本仓库所有值得注意的变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

仓库根目录的 `VERSION` 是版本号的唯一真源；`tests/validate_skill.py`
会交叉核对 `VERSION` 与本文件顶部条目，两者不一致时 CI 失败。

## [Unreleased]

### Added

- `SECURITY.md` 新增 `scripts/` 威胁模型：安装器的三处写入范围（目标 Skills 目录、
  `.computer-repair-skill-backups`、安装清单 `.computer-repair-skill-install.json`）、
  采集脚本的只读边界（不改状态、不联网、除 `--output` 外不写盘、逐行过滤疑似凭据），
  以及"脚本不是权限边界、请先审阅再运行"的明确声明。
- `NOTICE` 新增"Deviations from the upstream baseline"章节，逐类记录 37 个
  `source: bundled` 文件相对基准提交 `e5e5536` 的行为偏离：元数据与工具契约规范化、
  跨平台分支与平台匹配路由、Windows Update 流程（移除第三方 `PSWindowsUpdate`
  cmdlet、`net stop && net start` 改 `Stop-Service`/`Start-Service`、MSDT 可用性探测、
  `Get-HotFix` 列选修正）、OpenClaw 卸载前的配置快照与去通配删除、安全措辞对齐，
  以及纯格式改动。
- `CONTRIBUTING.md` 新增"新增分类"章节，写明分类登记的真源顺序：先在
  `tests/playbook_registry.py` 的 `CATEGORIES` 登记，再填 frontmatter，再手工加索引
  章节与 README 能力小节，最后跑生成器回写数字。
- 安装器新增 `--verify` / `--uninstall`（含 `--purge`）/ `--list-targets` / `--link` /
  `--dry-run` / `--backup-dir` / `--quiet`，PowerShell 版为对应的 `-Verify` / `-Uninstall` /
  `-Purge` / `-ListTarget` / `-Link` / `-DryRun` / `-BackupDir` / `-Quiet`。
- 安装清单 `<Skills 根目录>/.computer-repair-skill-install.json`（`schema: 1`）：
  记录版本、来源目录、来源 commit、安装方式与每个文件的 sha256。两个安装器写出的
  清单逐行同构，可以互相校验（PowerShell 装的副本能用 `install.sh --verify` 复核）。
  `--verify` 靠它判断文件是否被改动，`--uninstall` 靠它确认目录归属，因此不会误删
  用户自己放进去的文件（遇到清单外文件先列出并要求 `--force`）。
- 安装器预设从 3 个扩到 21 个 Agent 目标，覆盖 Claude Code、Codex、Cursor、Gemini CLI、
  GitHub Copilot、Windsurf、OpenCode、OpenClaw、Antigravity、Augment、Qwen Code、Trae、
  Roo Code、Crush、Goose、Droid、Continue、OpenHands 等，另有 `custom` 走 `--destination`。
- `scripts/collect-health.sh` 与 `scripts/collect-health.ps1`：只读健康证据采集脚本。
  11 个小节，输出结构化 JSON 或 Markdown，支持 `--sections` / `--timeout` / `--output` /
  `--no-identity`。严格只查不改、不联网、逐行过滤疑似凭据，除 `--output` 外不写任何路径。
- CI 新增 `installer` 与 `collector` 两个三平台 job：安装器跑完整序列（dry-run 零副作用、
  首装、清单校验、拒绝覆盖、篡改检出、`--force` 备份、幂等、清单外文件拦截、卸载无残留、
  链接模式），采集脚本在三平台真实执行并断言输出合法；两个 job 最后都断言
  `git status --porcelain` 为空，作为"只写目标目录"的证据。Windows 侧额外用
  Windows PowerShell 5.1 再跑一遍采集脚本。
- 新增 12 个专项 Playbook，总数 58 → 70，同时新增 4 个分类：
  - 硬件健康与崩溃分析（4）：`storage-health-smart`、`windows-crash-dump-triage`、
    `memory-diagnostics`、`thermal-battery-health`。
  - 外设、蓝牙与显示（2）：`bluetooth-peripheral-triage`、`display-gpu-triage`。
  - macOS 与 Linux 维修（4）：`macos-persistence-audit`、`linux-persistence-audit`、
    `macos-filevault-recovery-triage`、`linux-boot-failure-triage`。
  - 安全事件响应（2）：`malware-triage`、`ransomware-first-response`。

  补上的是此前只有 Windows 版本、或三平台都缺的场景：磁盘 SMART 健康、崩溃与内存分析、
  温度与电池损耗、macOS/Linux 持久化审计、Linux 启动失败、FileVault 恢复分诊，
  以及恶意软件与勒索软件的第一响应。安全红线沿用既有约束：转储文件只列元数据不读正文、
  恢复密钥不回显不入报告、SMART 自检与引导链改写不进只读流程、勒索事件先隔离再取证。
- `references/tools-{windows,macos,linux}.md` 新增 28 个只读工具别名（别名宇宙 96 → 124），
  按硬件与存储健康、崩溃与启动证据、持久化与软件清单、显示与蓝牙外设分组。每个别名都给出
  推荐实现与风险标注，并显式列出**不属于**该别名的状态变更命令（`smartctl -t`、
  `grub-install`、`fdesetup changerecovery`、`verifier.exe` 等），以及字段不可信的已知情况
  （`AdapterRAM` 32 位截断、USB 桥接盒不透传 SMART、Apple silicon 无内存插槽明细）。
- lint 工具链接入：`.markdownlint-cli2.jsonc`（每条规则决策附中文理由）、`ruff.toml`
  （target py39、line-length 110、E/F/W/I/UP/B/C4/SIM/RET/PTH/RUF）、shellcheck、
  PSScriptAnalyzer 和 actionlint，五套检查全部进 CI。首次接入时修复 markdownlint
  1888 条违规、shellcheck 4 条（SC1007 ×3、SC2088）与 PSScriptAnalyzer 4 条
  （`PSAvoidUsingWriteHost`，改为可重定向的 `Write-Status` 包装）。
- `tests/check_portability.py`：跨平台可移植性静态守卫，接入 CI 的 lint job。前三条规则
  各自对应一个只在非 Linux runner 上才会炸的真实故障：Bash 脚本里紧跟非 ASCII 字符的
  `$var` 必须写成 `${var}`；`shell: powershell` 步骤的 run 块必须是纯 ASCII；
  `tests/` 里的 `write_text()` 必须显式传 `newline="\n"`。第四条规则防的是同一类问题在
  PowerShell 侧的镜像：裸变量引用会吞掉紧随其后的 Unicode 字母（L\*）、数字（Nd）和组合
  记号（Mn），`Set-StrictMode -Version Latest` 下直接抛「cannot be retrieved」。现有中文
  消息因为全角标点恰好终止变量名而全部安全，这条规则把「恰好」变成「保证」。

### Fixed

- 更正 `NOTICE` 中过时的本地 Playbook 数量：`21 Windows/Linux playbooks` 改为
  `33 playbooks`，与 frontmatter 派生的 37 上游 / 33 本地一致。
- `CONTRIBUTING.md` 原先声明"只使用 `name` 和 `description`"，与已加入的
  `license: AGPL-3.0` 矛盾，现按实际允许字段更正；同时删掉正文里写死的 Playbook
  总数，改为指向生成器派生，避免再次漂移。

- 备份目录从仓库相邻的 `external/computer-repair-skill/backups` 改为
  `<Skills 根目录>/.computer-repair-skill-backups/<时间戳>/`。旧路径会在仓库外
  凭空造出目录树，且与 `--destination` 无关，用户很难预料备份去了哪里。
- `install.ps1` 现在拒绝多余的位置参数（`[CmdletBinding(PositionalBinding = $false)]`）。
  此前 `install.ps1 -Target claude foo` 会静默忽略 `foo`，而 `install.sh` 是明确报错的。
  `collect-health.ps1` 同样收紧。
- `install.ps1` 遇到预期内的错误（尚未安装就 `-Verify`、`-Purge` 单独使用、
  `-Verify` 与 `-Uninstall` 互斥等）不再向用户抛出完整 PowerShell 异常堆栈。
  脚本作用域 `trap` 把消息收敛为单行 `错误：<原因>` 写入 stderr 并以 1 退出，
  与 `install.sh` 的 `fail()` 输出逐字对齐；主入口分派之后显式 `exit 0`，避免脚本
  内部调用过 `git` 之后 `$LASTEXITCODE` 残留而被调用方误判为失败。CI 的
  `Assert-InstallerFails` 相应改为按退出码判定 —— 同进程 `& ./install.ps1` 调用时
  子脚本的 `exit 1` 不是异常，`catch` 不会触发，只看异常会漏掉真实失败。
- 重复安装不再无条件产生备份：已安装版本与仓库内容逐字节一致时，`--force` 直接报告
  "无需变更"并退出。
- 校验器会读入 `.ruff_cache/` 等工具缓存目录里的二进制文件并报 UTF-8 解码失败，
  导致整体判失败。新增 `IGNORED_DIR_NAMES`，遍历时按路径分量剔除 15 类缓存目录，
  并补参数化回归测试：在缓存目录里写入非 UTF-8 字节、CRLF、缺末尾换行和无语言标注的
  代码围栏，断言校验器仍退出 0。
- macOS 自带的 Bash 3.2 会把紧跟在 `$var` 后面的中文首字节并进变量名（BSD libc 的
  `isalnum()` 在 UTF-8 locale 下对 0x80-0xFF 返回真），于是 `set -u` 下
  `fail "目标已存在：$target_path。"` 不会打印那句提示，而是以
  `target_path\xef: unbound variable` 退出。`install.sh` 12 处、`collect-health.sh`
  7 处全部改写为 `${var}`。glibc 不复现这个行为，所以只有 macOS runner 能抓到它。
- `tests/playbook_registry.py --write` 和校验器回归测试在 Windows 上会写出 CRLF
  —— `Path.write_text()` 默认做行尾翻译 —— 生成的 `README.md` / `playbook-index.md`
  随即被 `.gitattributes` 的 LF 约束判失败。所有文本写入显式传 `newline="\n"`。
- `.github/workflows/validate.yml` 里两个 `shell: powershell` 步骤的 run 块改为纯 ASCII，
  中文断言挪到紧随其后的 `shell: pwsh` 步骤。Actions 把 5.1 步骤的正文写成不带 BOM 的
  临时 `.ps1`，5.1 按系统 ANSI 代码页解码，CP1252 把「错」的 0x94 字节读成右双引号，
  字符串提前闭合，整段脚本解析失败。

### Changed

- `SKILL.md` 的 `description` 扩写到覆盖本版新增的路由域（崩溃与转储、SMART 磁盘健康、
  内存故障、过热与电池损耗、蓝牙外设、显示与显卡、恶意软件与勒索软件、Linux 启动失败、
  BitLocker/FileVault、launchd/systemd 持久化），586 字符 / 75 分词，仍在自设的
  600 字符 / 80 分词上限内。
- `README.md` 能力范围表补齐四个新增覆盖面；`CONTRIBUTING.md` 的"本地验证"从单条
  `python tests/validate_skill.py` 扩为完整清单：`--strict`、生成器 `--check`/`--write`、
  `pytest tests/`、五套 lint（markdownlint-cli2 / ruff / shellcheck / PSScriptAnalyzer /
  actionlint），以及安装器和采集脚本的平台自测命令。

- README 安装章节重写：补齐全部新选项、更正备份路径、说明安装清单，并诚实标注
  `scripts/` 是可选辅助工具 —— Skill 的核心仍然是 Markdown Playbook。
- CI 的校验器调用收紧为 `python tests/validate_skill.py --strict`。1.1.0 时仓库还有
  10 个"已登记但没有任何 Playbook 使用"的工具别名，只能作为 warning 放行；本次新增的
  12 个 Playbook 把这 10 个别名全部消耗完，`--strict` 下 0 error / 0 warning。
- `.github/workflows/validate.yml` 重写为 5 个 job（validate / lint / powershell /
  installer / collector）。validate 跑 ubuntu、windows、macos 三平台矩阵，并断言登记生成器
  幂等（`--write` 之后 `git diff --exit-code` 必须干净）；全部 action 固定到 commit SHA，
  下载的 shellcheck 与 actionlint 用 `sha256sum --check --strict` 校验完整性；顶层收紧
  `permissions: contents: read` 并加 `concurrency` 取消同分支重复运行。`star-history.yml`
  同样收紧权限、固定 SHA，并在缺少 token 时写 job summary 跳过，而不是每周失败。
- `tests/test_validate_skill.py` 的 README 计数漂移用例改为从 README 现值推导总数，
  不再写死数字，避免每次增删 Playbook 都要同步改测试。

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
  - 新增 error / warning 分级与 `--strict` 开关。本版 CI **不加** `--strict`：
    当时仓库里还有 10 个"已登记但无人使用"的工具别名，只能先作为 warning 放行
    （后续已补齐并收紧，见 `[Unreleased]`）。
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
