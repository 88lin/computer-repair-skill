<div align="center">
  <img src="assets/computer-repair-cover.svg" alt="Computer Repair Skill：电脑诊断、修复与安全维护" width="100%" />
</div>

<div align="center">

# 🛠️ Computer Repair Skill

### 让 Agent 像一名谨慎的电脑维修工程师：先取证，再判断；先计划，再修改。

一个可安装到 Codex、Claude Code、OpenClaw 等 Agent 的跨平台电脑诊断与维修 Skill。

[![Validate Skill](https://github.com/88lin/computer-repair-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/88lin/computer-repair-skill/actions/workflows/validate.yml)
[![skills.sh](https://skills.sh/b/88lin/computer-repair-skill)](https://skills.sh/88lin/computer-repair-skill)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

</div>

> 电脑变慢、断网、更新失败、打印机离线、C 盘爆满、驱动异常、Windows 启动失败、OpenClaw 配置问题……直接用自然语言描述，Agent 会按平台和风险选择合适的排障流程。

## ✨ 为什么选择 Computer Repair Skill

- **证据优先**：先读取系统状态、日志、配置和硬件事实，再建立候选原因，不凭症状猜结论。
- **只读优先**：诊断和盘点可以先做；删除、安装、提权、重启、分区和服务修改会先给出影响、回滚与验证方案。
- **按需加载**：58 个专项 Playbook 通过路由索引按问题加载，减少无关上下文，也方便维护和扩展。
- **跨平台**：覆盖 Windows、macOS、Linux，并提供 DNS、邮件、身份、SSH、Wi-Fi 和 OpenClaw 等跨平台流程。
- **适合真实维修**：包含新机验收、BitLocker/PE 前置分诊、WinRE、数据恢复、拆机安全和设备回收等维修现场边界。
- **不绑定桌面应用**：Skill 本身是 Markdown/YAML 资源，不需要安装配套桌面程序、额外模型或专用云端 API。
- **可审计可回滚**：命令会映射到宿主 Agent 的终端、文件和网络工具；需要改变状态时保留计划和验证步骤。

## 🖥️ 能力范围

| 平台 | 主要覆盖 |
|---|---|
| Windows | 网络、性能、存储盘点、应用安装/卸载与清理、驱动与音视频、启动/WinRE、BitLocker/分区、硬件维护、新机验收、浏览器策略、Windows Update、配置审查、打印机、安全与数据恢复 |
| macOS | 网络、VPN、性能、磁盘、应用、系统更新、打印机、Homebrew、Time Machine、邮箱配置 |
| Linux | 网络、性能、磁盘与 inode、CUDA、通用安全与备份检查 |
| 跨平台 | DNS、邮件、身份服务、SSH、Wi-Fi、Outlook、OpenClaw、凭据与本地数据审计 |

## 🚀 安装

### 方式一：把一句话交给 Agent（最适合新手）

打开你正在使用的 Codex、Claude Code、Hermes、OpenClaw、Cursor 或其他支持 Agent Skills 的工具，把下面这句话直接发给它：

```text
请安装这个 Agent Skill：https://github.com/88lin/computer-repair-skill
先审查仓库内容和 SKILL.md，再安装到你当前 Agent 的 Skills 目录；如果已经安装旧版本，先备份再更新。
完成后告诉我实际安装路径、目标 Agent 和验证结果。
```

Agent 需要能访问 GitHub、读取本机文件并执行必要的安装命令。只支持聊天、不具备本机文件或终端能力的客户端，无法替你真正安装。

<details>
<summary>方式二：Skills CLI（适合已经安装 Node.js 的用户）</summary>

电脑已安装 Node.js 和 npm 时，在终端运行：

```bash
npx skills add 88lin/computer-repair-skill
```

第一次运行会让你选择安装范围和目标 Agent。常用的全局安装示例：

```bash
npx skills add 88lin/computer-repair-skill --global
```

只安装给 Codex，或安装给 Claude Code：

```bash
npx skills add 88lin/computer-repair-skill --global --agent codex
npx skills add 88lin/computer-repair-skill --global --agent claude-code
```

安装完成后重启或刷新 Agent 的 Skills 列表。Skills CLI 的安装范围、目标 Agent 和链接来源以其当前文档为准：<https://skills.sh/docs>。

</details>

<details>
<summary>方式三：仓库安装器（适合希望明确控制路径的用户）</summary>

先下载仓库：

```bash
git clone https://github.com/88lin/computer-repair-skill.git
cd computer-repair-skill
```

Windows PowerShell：

```powershell
.\scripts\install.ps1 -Target codex
.\scripts\install.ps1 -Target claude
.\scripts\install.ps1 -Target agents
```

macOS / Linux：

```bash
./scripts/install.sh --target codex
./scripts/install.sh --target claude
./scripts/install.sh --target agents
```

其中 `codex`、`claude`、`agents` 会使用对应的默认 Skills 根目录。需要自定义位置时：

```powershell
.\scripts\install.ps1 -Target custom -Destination "D:\path\to\skills"
```

```bash
./scripts/install.sh --target custom --destination "/path/to/skills"
```

目标目录已存在时，安装器默认拒绝覆盖；确认升级时显式加 `-Force` 或 `--force`，旧版本会先备份到相邻的 `external/computer-repair-skill/backups`。

</details>

<details>
<summary>方式四：手动复制（适合无法使用命令行的用户）</summary>

把仓库中的 [`skills/computer-repair-skill`](skills/computer-repair-skill) 整个目录复制到目标 Agent 的 Skills 根目录。例如：

```text
~/.codex/skills/computer-repair-skill/
~/.claude/skills/computer-repair-skill/
~/.agents/skills/computer-repair-skill/
```

目录中必须保留 `SKILL.md`、`agents/` 和 `references/`，不要只复制某一个 Playbook。

</details>

## ❤️赞助商

这里可以免费体验多种主流大模型（通义千问、智谱 GLM、月之暗面 Kimi 等系列）。具体可用型号和额度会随上游调整，点击前往[免费 AI 福利指南](https://blog.88lin.eu.org/article/36)查看当前列表。

## 🧭 如何使用

安装后直接说问题，不需要记 Playbook 名称。描述越具体，路由越准确：**平台 + 症状 + 约束 + 期望动作**。

```text
Windows 11 最近经常断网，先只读检查网卡、DHCP、DNS、代理和 VPN，不要重置网络。
```

```text
这台 Linux 服务器磁盘满了，先按挂载点和 inode 找原因，不要删除日志或容器数据。
```

```text
Mac 越来越慢，先做健康基线和性能取证，修复前把发现的问题和预计影响列出来。
```

```text
打印机显示离线，先检查队列、Spooler 和连接方式，清空卡住的作业前先让我确认。
```

你也可以组合多个目标：

```text
帮我做一次 Windows 维修前体检，同时检查 C 盘空间、启动项和备份状态；全部先只读。
```

标准工作顺序是：确认平台和约束 → 读取证据 → 说明候选原因 → 给出最小变更计划 → 等待确认 → 执行 → 验证并记录结果。

## 🧰 功能总览

本 Skill 内置 58 个可按需加载的专项 Playbook。下面的分类数量与[完整路由索引](skills/computer-repair-skill/references/playbook-index.md)一致。

| 分类 | 数量 | 主要内容 |
|---|---|---|
| 健康、性能、存储与备份 | 15 | 体检、性能、磁盘/目录盘点、应用缓存、备份和新机验收 |
| 网络、DNS、VPN、身份与邮件 | 9 | Wi-Fi、路由、DNS、VPN、邮件连通性、SSO 和邮箱配置 |
| 应用、系统更新与打印 | 7 | 应用崩溃、Outlook、macOS/Windows 更新、打印机和 Windows 配置审查 |
| Windows 维修、启动与硬件 | 7 | 驱动、摄像头/音频、启动失败、WinRE、BitLocker、分区和拆机安全 |
| Windows 数据恢复 | 1 | 镜像优先、只读扫描和独立目标恢复 |
| 安全与凭据 | 5 | 终端安全、浏览器、浏览器策略、持久化和凭据清理 |
| 开发环境与基础设置 | 3 | Homebrew、CUDA 和 SSH Key |
| OpenClaw | 11 | 安装、配置、渠道、国产模型、排障和卸载 |

## 💬 能做什么｜你可以这样问

### 🩺 健康、性能、存储与备份（15）

| 能力 | 你可以这样问 |
|---|---|
| 全面体检 — 建立系统健康基线，适合交接、验收和维修前留档 | “帮我给这台电脑做一次全面体检，先只读并输出报告。” |
| macOS 性能取证 — CPU、内存压力、IO、风扇和无响应 | “Mac 风扇一直转，帮我判断是 CPU、内存还是磁盘 IO。” |
| Windows 性能取证 — CPU、内存、磁盘瓶颈、启动慢和应用无响应 | “Windows 很卡，先找出最占 CPU、内存和磁盘的进程。” |
| Linux 性能取证 — 负载、CPU、内存、交换、IO 等待和容器限额 | “服务器负载很高，区分是 CPU 饱和、IO 等待还是容器限额。” |
| Mac 调优 — 缓存、权限和基础安全维护 | “Mac 变慢了，先做低风险维护，不要删我的个人文件。” |
| macOS 磁盘恢复 — 大文件、缓存和可释放空间审计 | “Mac 磁盘快满了，先列出可以安全释放的空间。” |
| Windows 磁盘恢复 — 系统盘爆满、更新空间不足和安全释放 | “C 盘只剩 5GB，先按风险分级给出清理计划。” |
| Windows 存储盘点 — 按路径和大小解释空间分配 | “帮我找出 C 盘最大的目录，但不要删除任何东西。” |
| Windows 应用清理 — 微信重复文件、浏览器缓存和包缓存 | “帮我清理微信重复文件，聊天记录和原文件不能动。” |
| Windows 应用生命周期审计 — WinGet、Chocolatey、Appx、来源、发布者和残留 | “审计这台电脑装了什么应用，先不要卸载。” |
| Windows 新机验收 — 本地硬件、序列号、配置、开箱证据和首次设置 | “先做新机本地验收，不联网激活；查保修前先问我。” |
| Linux 磁盘恢复 — 文件系统、inode、日志和容器存储增长 | “Linux 根分区满了，先判断是 inode、日志还是容器占用。” |
| 本地数据审计 — 离职、设备回收前盘点敏感数据 | “这台电脑要回收，先盘点敏感数据和残留账号，不要删除。” |
| 备份验证与抽样恢复 — 时间戳、完整性、可读性和独立目标恢复 | “验证备份能不能恢复一个测试文件，不要覆盖现有数据。” |
| macOS 备份设置 — Time Machine 和基础备份策略 | “帮我规划 Mac 的自动备份，先检查现有磁盘和空间。” |

### 🌐 网络、DNS、VPN、身份与邮件（9）

| 能力 | 你可以这样问 |
|---|---|
| macOS 网络诊断 — Wi-Fi、地址、路由、DNS 和网页访问 | “Mac 能连 Wi-Fi 但打不开网页，按层排查。” |
| Windows 网络诊断 — 网卡、DHCP、路由、DNS、代理、VPN 和 HTTP | “Windows 只有部分网站打不开，先区分 DNS、代理还是路由。” |
| Linux 网络诊断 — 链路、地址、路由、DNS、防火墙和命名空间 | “容器不能联网，先检查宿主和容器的网络边界。” |
| macOS VPN 排障 — 连接、掉线、分流和 DNS 异常 | “VPN 能连接但内网域名打不开，先查分流和 DNS。” |
| DNS 记录检查 — MX、SPF、DKIM、DMARC 和邮件域名记录 | “检查 example.com 的 MX 和 SPF，告诉我哪些记录缺失。” |
| 邮件连通性测试 — SMTP、IMAP、POP3 和邮件服务器 | “只测试邮件服务器端口和 TLS，不要发送真实邮件。” |
| 身份提供商测试 — Entra ID、Google Workspace 和 SSO 端点 | “SSO 登录失败，先测试端点和时间/证书问题。” |
| Wi-Fi 配置 — 家庭或企业 WPA2/WPA3 配置 | “配置企业 Wi-Fi；密码不要出现在输出和日志里。” |
| macOS 邮箱配置 — Apple Mail 或 Outlook 添加邮箱 | “帮我配置邮箱，先确认服务器和认证方式，不要把密码发出来。” |

### 🧩 应用、系统更新与打印（7）

| 能力 | 你可以这样问 |
|---|---|
| macOS 应用修复 — 崩溃、打不开、权限和配置损坏 | “某个 Mac 应用一打开就崩，先收集日志和配置证据。” |
| Outlook 排障 — 同步、卡信、崩溃和配置文件 | “Outlook 邮件不同步，先判断是网络、账户还是配置文件。” |
| macOS 更新排障 — 下载、安装和更新卡住 | “macOS 更新失败，先检查错误原因，不要抹掉系统。” |
| Windows Update 排障 — 错误码、服务、待重启和更新缓存 | “Windows 更新卡住，先修复更新链路，不要关闭更新。” |
| macOS 打印机修复 — 队列、CUPS 和设备发现 | “Mac 打印队列卡住了，先保留作业内容再处理。” |
| Windows 打印机修复 — 离线状态、打印队列和 Spooler | “Windows 打印机离线，清除卡住作业前先告诉我影响。” |
| Windows 配置审查 — 隐私、电源、去臃肿设置的差异、风险和回滚 | “审查这份 Windows 优化配置，不要直接套用，给我 diff。” |

### 🪟 Windows 维修、启动与硬件（7）

| 能力 | 你可以这样问 |
|---|---|
| 驱动生命周期审计 — 硬件 ID、官方来源、重装、回滚和兼容性 | “未知 USB 设备找不到驱动，先识别硬件 ID 和官方来源。” |
| 摄像头与音视频输入分诊 — 开关、权限、系统设备和会议软件 | “Teams 找不到麦克风，按硬件、权限、驱动、应用四层排查。” |
| 启动失败分诊 — No Boot Device、启动循环、UEFI/Legacy 和启动界面 | “开机提示 No Boot Device，不能改 BIOS，先判断磁盘还是启动项。” |
| WinRE 系统修复 — SFC、DISM、安全模式、启动修复和还原 | “Windows 进不了桌面，先做无损修复分诊，不要重装。” |
| BitLocker/PE 前置分诊 — 加密状态、TPM/BIOS、恢复密钥和离线清单 | “我准备进入 PE，请先在当前 Windows 检查 BitLocker 状态；不要输出恢复密钥。” |
| 分区扩容审计 — 邻接空间、备份、移动分区和离线操作边界 | “C 盘太小，先评估能否安全扩容，不要立即移动分区。” |
| 硬件维护安全 — 断电放电、ESD、清灰、换件和停工条件 | “笔记本发热，先判断是否值得拆机清灰，并列出停工条件。” |

> **新机和 PE/BitLocker 的正确使用方式**：新机验收先执行本地离线检查；联网查厂商支持、保修或激活信息必须等宿主有网络且用户确认。进入 PE/WinRE 前，在当前可用系统中完成 BitLocker 分诊、备份和清单保存；PE/WinRE 阶段不假设有网络或 Agent，按清单由用户/技师操作，回到可用宿主后再让 Agent 复核。

### 🧯 Windows 数据恢复（1）

| 能力 | 你可以这样问 |
|---|---|
| Windows 数据恢复分诊 — 先成像、只读扫描、报告，再写入独立目标 | “误删文件了，先不要动原硬盘，先规划成像和恢复目标。” |

### 🔐 安全与凭据（5）

| 能力 | 你可以这样问 |
|---|---|
| 终端安全检查 — 防病毒、防火墙、更新和可疑活动 | “检查系统安全状态，但不要关闭 Defender、防火墙或 UAC。” |
| 浏览器安全审计 — 扩展、密码存储、版本和安全设置 | “审计浏览器安全性，不要读取或输出已保存密码。” |
| Windows 浏览器策略审计 — Chrome、Edge、Firefox、Brave 策略和遥测 | “检查浏览器策略，不能影响密码、自动更新和企业策略。” |
| Windows 持久化审计 — 启动项、服务、计划任务、右键菜单和文件关联 | “查找可疑后台和启动残留，先只读列证据。” |
| 凭据清理 — SSH key、token、云凭据和事件后残留 | “我要离职了，先列出需要轮换的凭据，不要把 secret 打印出来。” |

### 🧑‍💻 开发环境与基础设置（3）

| 能力 | 你可以这样问 |
|---|---|
| Homebrew — 安装、配置和基础诊断 | “帮我安装 Homebrew，先检查系统版本和现有路径。” |
| CUDA — Ubuntu、Debian、RHEL/Fedora 的驱动与工具链 | “在 Linux 上安装 CUDA，先核对 GPU、驱动和发行版版本。” |
| SSH Key — 生成、GitHub 配置和 publickey 排障 | “配置 SSH 连接 GitHub，私钥不要离开本机。” |

### 🦞 OpenClaw（11）

| 能力 | 你可以这样问 |
|---|---|
| OpenClaw 总体安装 — Node.js、网关、渠道和安装验证 | “帮我安装 OpenClaw，先检查 Node.js 和端口。” |
| Node.js 22+ — 安装或核对 OpenClaw 所需运行时 | “OpenClaw 启动不了，先确认 Node.js 版本和来源。” |
| OpenClaw 配置 — 模型、渠道、会话和自动化 | “配置 OpenClaw 的模型和会话，密钥只写入本机配置。” |
| OpenClaw 配置字段参考 — 查询配置项和安全默认值 | “这个 OpenClaw 配置字段是什么意思，先给我解释不要修改。” |
| 飞书内置插件 — 机器人身份接入 | “给 OpenClaw 加飞书机器人，凭据不要出现在聊天记录里。” |
| 飞书官方插件 — 用户身份和文档能力 | “配置飞书官方插件，先说明权限范围和回滚方法。” |
| Telegram 渠道 — Bot 接入和连通性 | “给 OpenClaw 接入 Telegram，token 不要显示在输出。” |
| WhatsApp 渠道 — 登录、重新配置和会话状态 | “WhatsApp 渠道掉线了，先诊断会话，不要清除现有登录。” |
| 国产模型 — 火山、Moonshot、DeepSeek、Qwen、GLM | “让 OpenClaw 使用 DeepSeek，先比较接口、费用和密钥存放方式。” |
| OpenClaw 排障 — 网关、渠道、模型和日志 | “OpenClaw 飞书消息发不出去，先查网关状态和相关日志。” |
| OpenClaw 卸载 — 停止服务、移除配置和验证残留 | “卸载 OpenClaw，先列出服务、配置和数据目录，确认后再删。” |

## 🛡️ 安全边界

- 只读检查可以先做；安装、删除、提权、重启、服务/启动项修改、分区、清空队列和其他状态变更，必须先展示影响、回滚和验证，得到本次动作确认后再执行。
- 不执行远程脚本管道、未知二进制、盗版激活、强制卸载 Edge，也不主动关闭 Defender、SmartScreen、UAC、防火墙、Windows Update 或核心隔离。
- 不在聊天中输出密码、恢复密钥、私钥、token 或完整敏感路径；需要验证时使用脱敏结果、哈希、状态和本机保存的证据。
- 进入 PE/WinRE、修改 BIOS/UEFI/TPM、移动分区、拆机或处理原盘恢复前，先确认备份、BitLocker 恢复密钥、厂商保修和企业管理边界。
- Skill 不假设 PE/WinRE/安装介质内有网络或可调用 AI。离线阶段使用提前保存的清单和证据，回到可用宿主后再复核。
- Skill 不等于维修资质或数据恢复承诺。涉及冒烟、进液、异响、过热、电池鼓包、原盘物理故障或重要数据时，立即停工并升级给专业人员。

## 🧱 项目结构

```text
skills/computer-repair-skill/
├── SKILL.md                 # 核心路由与强制安全工作流
├── agents/openai.yaml       # Codex 展示元数据
├── references/              # 平台工具映射与 58 个专项 Playbook
├── LICENSE                  # 随 Skill 分发的 AGPL-3.0 许可证
└── NOTICE                   # 来源与归属记录
assets/
└── computer-repair-cover.svg  # README 封面图
scripts/
├── install.ps1              # Windows 安装器
└── install.sh               # macOS/Linux 安装器
tests/validate_skill.py      # 无第三方依赖的仓库验证器
```

## 🧪 开发与验证

修改 Skill 或 Playbook 后，在仓库根目录运行：

Windows PowerShell：

```powershell
$env:PYTHONUTF8 = "1"
python tests\validate_skill.py
```

macOS / Linux：

```bash
PYTHONUTF8=1 python tests/validate_skill.py
```

验证器会检查 Skill frontmatter、Agent 元数据、58 个 Playbook 的描述唯一性、工具契约、路由索引、README 分类数量、本地 Markdown 链接、许可证一致性、占位符和疑似凭据。GitHub Actions 会在 Windows 和 Ubuntu 上重复验证，并测试安装器的首次安装、拒绝覆盖、备份和强制更新路径。

新增或修改 Playbook 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## ❓ 常见问题

**这是一个桌面软件吗？**

不是。它是给 Agent 读取的 Skill 包，提供流程、工具契约和安全边界。实际执行依赖你的 Agent 是否有本机终端、文件、网络和确认机制。

**能不能只用聊天窗口？**

可以让 Agent 解释流程、生成检查清单和人工步骤；但没有本机工具时，它不能替你读取真实系统，也不能声称已经修复或验证。

**为什么不直接“一键优化 Windows”？**

因为优化配置可能影响更新、隐私、驱动、企业策略和回滚。Computer Repair Skill 会先审查差异、风险和回滚路径，再在你确认后执行最小变更。

**进入 PE 后还能继续问 Agent 吗？**

不要假设可以。进入 PE/WinRE 前让 Agent 把 BitLocker 状态、备份检查、命令清单和停工条件保存下来；离线阶段由人按清单处理，回到正常系统后再让 Agent 复核。

## ⭐ Star History

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/88lin/computer-repair-skill/star-history/assets/my-star-history/star-history-dark.svg">
  <img alt="Star History" src="https://raw.githubusercontent.com/88lin/computer-repair-skill/star-history/assets/my-star-history/star-history-light.svg">
</picture>

## 📄 来源与许可证

项目按 [GNU AGPL-3.0](LICENSE) 分发。来源、归属和第三方许可证信息见 [NOTICE](NOTICE)；安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

欢迎提交经过验证的 Playbook、平台工具映射和维修案例改进。
