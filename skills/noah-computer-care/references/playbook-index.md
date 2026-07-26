# Playbook 路由索引

先按实际平台过滤，再按症状选择最具体的条目。`all` 表示流程可跨平台，但其中命令仍需按当前平台工具映射执行。

同一问题命中多个条目时，优先级依次为：具体产品或组件、具体故障类型、通用健康检查。不要用健康基线替代已存在的专项流程。

本索引登记 43 个可执行 Playbook：37 个来自 Noah for Tinkerers，6 个由本项目补充，用于覆盖 Windows 和 Linux 的网络、性能与磁盘空间诊断。

## 健康、性能、存储与备份

| Playbook | 平台 | 触发症状 | 文件 |
|---|---|---|---|
| `health-baseline-check` | all | 全面体检、设备健康、交接前检查 | [playbook-health-baseline-check.md](playbook-health-baseline-check.md) |
| `performance-forensics` | macOS | 高 CPU、内存压力、卡顿、风扇、无响应 | [playbook-performance-forensics.md](playbook-performance-forensics.md) |
| `windows-performance-forensics` | Windows | 高 CPU、内存压力、磁盘瓶颈、启动慢、应用无响应 | [playbook-windows-performance-forensics.md](playbook-windows-performance-forensics.md) |
| `linux-performance-forensics` | Linux | 高负载、CPU 饱和、内存压力、交换、IO 等待、容器限额 | [playbook-linux-performance-forensics.md](playbook-linux-performance-forensics.md) |
| `mac-tune-up` | macOS | Mac 普遍变慢、安全维护、缓存刷新 | [playbook-mac-tune-up.md](playbook-mac-tune-up.md) |
| `disk-space-recovery` | macOS | 磁盘爆满、释放空间、大文件与缓存审计 | [playbook-disk-space-recovery.md](playbook-disk-space-recovery.md) |
| `windows-disk-space-recovery` | Windows | 系统盘爆满、更新空间不足、安全释放空间 | [playbook-windows-disk-space-recovery.md](playbook-windows-disk-space-recovery.md) |
| `linux-disk-space-recovery` | Linux | 文件系统或 inode 用尽、日志与容器存储增长 | [playbook-linux-disk-space-recovery.md](playbook-linux-disk-space-recovery.md) |
| `local-data-audit` | all | 离职、设备回收、本地敏感数据盘点 | [playbook-local-data-audit.md](playbook-local-data-audit.md) |
| `backup-verify-restore` | all | 验证备份、检查时间戳、抽样恢复文件 | [playbook-backup-verify-restore.md](playbook-backup-verify-restore.md) |
| `setup-backup` | macOS | 配置 Time Machine 或基础备份策略 | [playbook-setup-backup.md](playbook-setup-backup.md) |

## 网络、DNS、VPN、身份与邮件

| Playbook | 平台 | 触发症状 | 文件 |
|---|---|---|---|
| `network-diagnostics` | macOS | 无网络、Wi-Fi 掉线、DNS、网页打不开 | [playbook-network-diagnostics.md](playbook-network-diagnostics.md) |
| `windows-network-diagnostics` | Windows | 网卡、DHCP、路由、DNS、代理、VPN 或 HTTP 异常 | [playbook-windows-network-diagnostics.md](playbook-windows-network-diagnostics.md) |
| `linux-network-diagnostics` | Linux | 链路、地址、路由、DNS、防火墙、命名空间异常 | [playbook-linux-network-diagnostics.md](playbook-linux-network-diagnostics.md) |
| `vpn-troubleshooting` | macOS | VPN 连不上、掉线、分流 DNS 异常 | [playbook-vpn-troubleshooting.md](playbook-vpn-troubleshooting.md) |
| `dns-record-check` | all | MX、SPF、DKIM、DMARC、邮件域名记录 | [playbook-dns-record-check.md](playbook-dns-record-check.md) |
| `email-connectivity-test` | all | SMTP、IMAP、POP3 或邮件服务器连通性 | [playbook-email-connectivity-test.md](playbook-email-connectivity-test.md) |
| `identity-provider-test` | all | Entra ID、Google Workspace、SSO 登录端点 | [playbook-identity-provider-test.md](playbook-identity-provider-test.md) |
| `setup-wifi-profile` | all | 新 Wi-Fi、企业 Wi-Fi、WPA2-Enterprise | [playbook-setup-wifi-profile.md](playbook-setup-wifi-profile.md) |
| `setup-email-account` | macOS | Apple Mail 或 Outlook 添加邮箱 | [playbook-setup-email-account.md](playbook-setup-email-account.md) |

## 应用、系统更新与打印

| Playbook | 平台 | 触发症状 | 文件 |
|---|---|---|---|
| `app-doctor` | macOS | 应用崩溃、打不开、权限或配置损坏 | [playbook-app-doctor.md](playbook-app-doctor.md) |
| `outlook-troubleshooting` | all | Outlook 同步、崩溃、卡信、配置文件 | [playbook-outlook-troubleshooting.md](playbook-outlook-troubleshooting.md) |
| `update-troubleshooting` | macOS | macOS 更新卡住、下载或安装失败 | [playbook-update-troubleshooting.md](playbook-update-troubleshooting.md) |
| `windows-update-troubleshooting` | Windows | Windows Update 卡住、错误码、待重启 | [playbook-windows-update-troubleshooting.md](playbook-windows-update-troubleshooting.md) |
| `printer-repair` | macOS | 打印队列、找不到打印机、CUPS | [playbook-printer-repair.md](playbook-printer-repair.md) |
| `windows-printer-repair` | Windows | 离线打印机、卡住作业、Spooler | [playbook-windows-printer-repair.md](playbook-windows-printer-repair.md) |

## 安全与凭据

| Playbook | 平台 | 触发症状 | 文件 |
|---|---|---|---|
| `endpoint-security-check` | all | 防病毒、防火墙、更新、可疑活动检查 | [playbook-endpoint-security-check.md](playbook-endpoint-security-check.md) |
| `browser-security-audit` | all | 浏览器扩展、密码、版本和安全审计 | [playbook-browser-security-audit.md](playbook-browser-security-audit.md) |
| `credential-cleanup` | all | 离职或事件后的凭据盘点与清理 | [playbook-credential-cleanup.md](playbook-credential-cleanup.md) |

## 开发环境与基础设置

| Playbook | 平台 | 触发症状 | 文件 |
|---|---|---|---|
| `setup-homebrew` | macOS | 安装或配置 Homebrew | [playbook-setup-homebrew.md](playbook-setup-homebrew.md) |
| `setup-cuda` | Linux | Ubuntu/Debian/RHEL/Fedora 安装 CUDA | [playbook-setup-cuda.md](playbook-setup-cuda.md) |
| `setup-ssh-key` | all | SSH Key、GitHub SSH、publickey 错误 | [playbook-setup-ssh-key.md](playbook-setup-ssh-key.md) |

## OpenClaw

先加载主流程，再按选择读取一个子模块。配置字段查询可直接读取配置参考。

| Playbook | 用途 | 文件 |
|---|---|---|
| `setup-openclaw` | 安装、引导、网关、渠道和总体验证 | [playbook-setup-openclaw.md](playbook-setup-openclaw.md) |
| `setup-openclaw/install-node` | 安装 Node.js 22+ | [playbook-setup-openclaw-install-node.md](playbook-setup-openclaw-install-node.md) |
| `setup-openclaw/configure` | 模型、渠道、会话和自动化配置 | [playbook-setup-openclaw-configure.md](playbook-setup-openclaw-configure.md) |
| `setup-openclaw/config-reference` | 查询 OpenClaw 配置字段 | [playbook-setup-openclaw-config-reference.md](playbook-setup-openclaw-config-reference.md) |
| `setup-openclaw/add-feishu` | 飞书内置插件，机器人身份 | [playbook-setup-openclaw-add-feishu.md](playbook-setup-openclaw-add-feishu.md) |
| `setup-openclaw/add-feishu-official` | 飞书官方插件，用户身份与文档能力 | [playbook-setup-openclaw-add-feishu-official.md](playbook-setup-openclaw-add-feishu-official.md) |
| `setup-openclaw/add-telegram` | Telegram 渠道 | [playbook-setup-openclaw-add-telegram.md](playbook-setup-openclaw-add-telegram.md) |
| `setup-openclaw/add-whatsapp` | WhatsApp 登录或重新配置 | [playbook-setup-openclaw-add-whatsapp.md](playbook-setup-openclaw-add-whatsapp.md) |
| `setup-openclaw/china-models` | 火山、Moonshot、DeepSeek、Qwen、GLM | [playbook-setup-openclaw-china-models.md](playbook-setup-openclaw-china-models.md) |
| `setup-openclaw/troubleshooting` | 网关、渠道、模型和日志排错 | [playbook-setup-openclaw-troubleshooting.md](playbook-setup-openclaw-troubleshooting.md) |
| `setup-openclaw/uninstall` | 停止服务并卸载 OpenClaw | [playbook-setup-openclaw-uninstall.md](playbook-setup-openclaw-uninstall.md) |

## 未命中专项流程

没有精确 Playbook 时继续执行 `SKILL.md` 的通用工作流：只读快照、建立候选原因、最小复现、展示计划、确认、修复、验证。完成后用户要求复用时，按 `playbook-authoring.md` 沉淀新流程。
