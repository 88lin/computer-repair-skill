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

## 完整功能一览

本 Skill 内置 43 个排障 Playbook，覆盖 6 大类问题。以下是每个能做什么，以及你该怎么问：

### 一、健康、性能、存储与备份（11 个）

| 能做什么 | 你可以这样问 |
|---|---|
| 全面体检 — 系统健康基线检查，适合交接/验收 | "帮我给这台机器做个全面体检" |
| 性能诊断 — CPU/内存/IO/负载/容器限额排查 | "系统很慢，帮我查查为什么" |
| 磁盘清理 — 找出垃圾文件、释放空间 | "磁盘快满了，帮我清理一下" |
| Mac 调优 — 清缓存、修权限、安全维护 | "Mac 越来越慢了，帮我调优" |
| 本地数据审计 — 离职/设备回收前盘点敏感数据 | "这台机器要回收了，帮我查查有没有敏感数据" |
| 备份验证 — 检查备份是否完整、抽样恢复 | "帮我验证一下备份能不能正常恢复" |
| 配置备份 — 设置 Time Machine 等备份策略 | "帮我配置 Mac 的自动备份" |

### 二、网络、DNS、VPN、身份与邮件（9 个）

| 能做什么 | 你可以这样问 |
|---|---|
| 网络诊断 — 断网、Wi-Fi 掉线、DNS、路由排查 | "网连不上了，帮我排查" |
| VPN 排障 — 连不上、掉线、分流 DNS 异常 | "VPN 连不上，帮我看看" |
| DNS 记录检查 — MX/SPF/DKIM/DMARC 邮件域名记录 | "帮我查一下域名的 MX 和 SPF 记录" |
| 邮件连通性测试 — SMTP/IMAP/POP3 连通性 | "帮我测试一下邮件服务器能不能连通" |
| 身份提供商测试 — Entra ID/Google SSO 登录端点 | "帮我测一下 SSO 登录端点是否正常" |
| Wi-Fi 配置 — 新 Wi-Fi、企业 WPA2 | "帮我配置企业 Wi-Fi 连接" |
| 邮箱配置 — Apple Mail/Outlook 添加邮箱 | "帮我在 Mac 上配置 Outlook 邮箱" |

### 三、应用、系统更新与打印（6 个）

| 能做什么 | 你可以这样问 |
|---|---|
| 应用修复 — 崩溃、打不开、配置损坏 | "XXX 应用一直崩溃，帮我修一下" |
| Outlook 排障 — 同步、卡信、配置文件问题 | "Outlook 邮件不同步了，帮我排查" |
| 系统更新排障 — 更新卡住、安装失败 | "Windows 更新一直卡住，帮我解决" |
| 打印机修复 — 找不到打印机、队列卡住 | "打印机离线了，帮我修" |

### 四、安全与凭据（3 个）

| 能做什么 | 你可以这样问 |
|---|---|
| 终端安全检查 — 防病毒、防火墙、可疑活动 | "帮我检查一下系统安全状态" |
| 浏览器安全审计 — 扩展、密码、版本安全 | "帮我审计一下浏览器的安全状况" |
| 凭据清理 — 离职/事件后清理 SSH key、token 等 | "我要离职了，帮我清理机器上的凭据" |

### 五、开发环境（3 个）

| 能做什么 | 你可以这样问 |
|---|---|
| Homebrew 安装配置 | "帮我安装配置 Homebrew" |
| CUDA 安装 — Ubuntu/Debian/RHEL | "帮我在这台 Linux 上装 CUDA" |
| SSH Key 配置 — 生成、GitHub 配置、排障 | "帮我配置 SSH key 连 GitHub" |

### 六、OpenClaw 部署（11 个）

| 能做什么 | 你可以这样问 |
|---|---|
| 安装 OpenClaw — Node.js、网关、总体验证 | "帮我安装 OpenClaw" |
| 配置模型/渠道 — 会话、自动化配置 | "帮我配置 OpenClaw 的模型和飞书渠道" |
| 接入飞书 — 内置插件 / 官方插件 | "帮我给 OpenClaw 加飞书机器人" |
| 接入 Telegram / WhatsApp | "帮我给 OpenClaw 加 Telegram 渠道" |
| 接入国产模型 — 火山/Moonshot/DeepSeek/Qwen/GLM | "帮我配置 OpenClaw 用 DeepSeek 模型" |
| OpenClaw 排障 — 网关、渠道、日志 | "OpenClaw 飞书消息发不出去，帮我排查" |
| 卸载 OpenClaw | "帮我卸载 OpenClaw" |

## 使用技巧

1. 直接用自然语言描述问题就行，Agent 会自动匹配最合适的 Playbook。
2. 说清症状 + 平台，比如 "Windows 上 Chrome 一直崩溃" 比 "浏览器有问题" 更好。
3. 所有操作先诊断后执行，涉及修改的会先给你看方案，确认后才动手。
4. 可以组合问，比如 "帮我体检一下，顺便看看网络有没有问题"。
5. 没命中现成 Playbook 也没关系，会走通用排障流程帮你查。

简单来说，电脑相关的任何问题都可以问，从"太慢了"到"打印机坏了"到"帮我装 CUDA"，都能帮你诊断和修复。

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

## 🎁 AI 免费福利

<div align="center">
  <h3>把值得领取的免费 AI 资源一次收齐</h3>

  <p>
    想低成本体验更强的 AI Agent 和国产模型？这份指南整理了高校师生权益、Pro 试用、模型额度与限时活动，
    并按适用人群、领取方式和使用场景集中说明，方便学习、科研、编程、办公与内容创作时按需查找。
  </p>

  <p>
    <a href="https://blog.88lin.eu.org/article/36">
      <strong>查看免费 AI 资源与领取指南 →</strong>
    </a>
  </p>

  <a href="https://blog.88lin.eu.org/article/36">
    <img src="https://cdn.jsdmirror.com/gh/88lin/picx-images-hosting@master/qoder-cover-no-link-1600x900.webp" alt="免费 AI 资源与领取指南" width="78%" />
  </a>
</div>

> [!TIP]
> 活动名额、模型、额度和有效期可能调整，领取前请以文章中的最新说明和对应官方页面为准。

## 来源与许可证

项目按 [GNU AGPL-3.0](LICENSE) 分发。
