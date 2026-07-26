# Computer Care

[![Validate Skill](https://github.com/88lin/computer-care/actions/workflows/validate.yml/badge.svg)](https://github.com/88lin/computer-care/actions/workflows/validate.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

一个可直接安装到 Agent 的跨平台电脑诊断与修复 Skill。它把经过整理的公开排障知识转换为独立的 `SKILL.md` 包，不需要安装配套桌面应用，不启动额外模型，也不调用专用云端 API。

宿主 Agent 负责推理和调用本机工具；本 Skill 提供只读优先的工作流、安全边界、平台命令映射和 43 个可按需加载的 Playbook。

## 能力范围

| 平台 | 主要覆盖 |
|---|---|
| Windows | 网络、性能、磁盘空间、Windows Update、打印机、通用安全与备份检查 |
| macOS | 网络、VPN、性能、磁盘、应用、系统更新、打印机、Homebrew、Time Machine |
| Linux | 网络、性能、磁盘与 inode、CUDA、通用安全与备份检查 |
| 跨平台 | DNS、邮件、身份服务、SSH、Wi-Fi、Outlook、OpenClaw、凭据与本地数据审计 |

核心设计：

- 先读取系统事实，再判断根因，不根据症状直接执行修复。
- 普通只读诊断可直接运行；安装、删除、提权、重启和其他状态变更先展示计划并等待确认。
- 只加载当前问题需要的平台参考和 Playbook，避免把全部知识塞入上下文。
- 所有命令都映射到宿主 Agent 已有的终端、文件和网络能力。
- Skill 运行时只有 Markdown/YAML 文件，没有 Python、Node.js 或桌面应用依赖。

## 安装

先克隆仓库：

```bash
git clone https://github.com/88lin/computer-care.git
cd computer-care
```

### Windows / PowerShell

```powershell
# Codex: %CODEX_HOME%\skills 或 ~/.codex/skills
.\scripts\install.ps1 -Target codex

# Claude Code: %CLAUDE_HOME%\skills 或 ~/.claude/skills
.\scripts\install.ps1 -Target claude

# 通用 Agent Skills 目录: ~/.agents/skills
.\scripts\install.ps1 -Target agents
```

### macOS / Linux

```bash
# Codex: $CODEX_HOME/skills 或 ~/.codex/skills
./scripts/install.sh --target codex

# Claude Code: $CLAUDE_HOME/skills 或 ~/.claude/skills
./scripts/install.sh --target claude

# 通用 Agent Skills 目录: ~/.agents/skills
./scripts/install.sh --target agents
```

其他 Agent 使用自定义 Skills 根目录：

```powershell
.\scripts\install.ps1 -Target custom -Destination "D:\path\to\skills"
```

```bash
./scripts/install.sh --target custom --destination "/path/to/skills"
```

`Destination` 指向 Skills 根目录，安装器会在其中创建 `computer-care`。目标已存在时默认停止；显式传入 `-Force` 或 `--force` 才会更新，并先把旧版本移动到相邻的 `external/computer-care/backups` 目录。

也可以手动把 [`skills/computer-care`](skills/computer-care) 整个目录复制到任意兼容 Agent 的 Skills 根目录。

## 使用

安装后重启或刷新 Agent 的 Skills 列表，然后直接描述问题，例如：

```text
用 computer-care 检查这台 Windows 电脑为什么经常断网。
```

```text
这台 Linux 服务器磁盘满了，先找出原因，不要直接删除文件。
```

“任意 Agent”需要满足两个条件：能够识别基于 `SKILL.md` 的 Skills，并具有完成目标所需的本机文件或终端工具。纯聊天客户端仍可读取流程并提供人工步骤，但无法自动操作电脑。

## 项目结构

```text
skills/computer-care/
├── SKILL.md                 # 核心路由与强制安全工作流
├── agents/openai.yaml       # Codex 展示元数据
├── references/              # 平台工具映射与 43 个 Playbook
├── LICENSE                  # 随 Skill 分发的 AGPL-3.0 许可证
└── NOTICE                   # 随 Skill 分发的上游归属记录
scripts/
├── install.ps1              # Windows 安装器
└── install.sh               # macOS/Linux 安装器
tests/validate_skill.py      # 无第三方依赖的仓库验证器
```

## 开发与验证

修改后运行：

```bash
python tests/validate_skill.py
```

验证器检查 Skill frontmatter、Agent 元数据、43 个 Playbook 的唯一性和索引覆盖、本地 Markdown 链接、许可证一致性、占位符与疑似凭据。GitHub Actions 会在 Windows 和 Ubuntu 上重复验证，并实际测试对应安装器的首次安装、拒绝覆盖、备份与强制更新路径。

新增或修改 Playbook 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## 来源与许可证

本项目包含 37 个经宿主 Agent 适配的上游 Playbook，以及 6 个由本项目维护的 Windows/Linux 扩展：

- 上游 Playbook 标记为 `author: upstream-maintainers` 和 `source: bundled`。
- 6 个 Windows/Linux 扩展标记为 `author: computer-care-maintainers` 和 `source: local`。

上游项目、基准提交和原作者归属记录在 [NOTICE](NOTICE) 中。项目按 [GNU AGPL-3.0](LICENSE) 分发。
