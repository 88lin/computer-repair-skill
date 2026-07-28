# 安全策略

## 支持范围

当前只维护 `main` 分支的最新版本。旧提交和第三方修改版本可能不会获得安全修复。

## 私下报告漏洞

请使用 GitHub 的 [Private vulnerability reporting](https://github.com/88lin/computer-repair-skill/security/advisories/new) 提交安全报告，不要在公开 Issue、Discussion 或 Pull Request 中披露漏洞、凭据或可复现的敏感设备信息。

报告尽量包含：

- 受影响文件、提交或版本。
- 可复现步骤和实际影响。
- 宿主 Agent、操作系统和权限条件。
- 已做的脱敏处理；不要附带真实令牌、私钥或用户数据。
- 建议修复或缓解方式（如有）。

维护者会先确认收到报告，再根据影响和可复现性协调修复与披露时间。

## 信任边界

Computer Repair Skill 是提供给 Agent 的指令与参考资料，不是权限隔离器。宿主 Agent 的审批、沙箱、操作系统权限和用户确认始终是最终安全边界。

本项目不会要求关闭安全软件、绕过审批或回显秘密。Playbook 中出现的系统命令必须先按当前设备事实复核；安装、删除、提权、重启及其他状态变更必须由用户明确确认。

## `scripts/` 的威胁模型

仓库里的脚本是可选的便利工具，Skill 的核心内容仍然是 Markdown。运行前请先审阅源码；两类脚本的边界不同：

**安装器（`scripts/install.ps1`、`scripts/install.sh`）会写盘。** 它只写三处：目标 Agent 的 Skills 目录（或 `--destination` 指定的路径）、同级的备份目录 `.computer-repair-skill-backups`、以及记录本次安装文件清单的 `.computer-repair-skill-install.json`。安装清单只用于 `--verify` 校验和 `--uninstall` 精确回收，不会记录设备标识或凭据。`--dry-run` 打印计划而不落盘；`--uninstall` 只删除清单里登记过的文件，不做通配删除。安装器不会修改系统设置、服务、注册表运行项或安全软件配置。

**采集脚本（`scripts/collect-health.ps1`、`scripts/collect-health.sh`）是严格只读的。** 它只运行查询类命令，不改变系统状态、不联网、不下载任何内容，除 `--output` 指定的报告文件外不写入任何路径。输出会逐行过滤疑似凭据（令牌、密钥、密码形态的字符串），`--no-identity` 可进一步去掉主机名、用户名和序列号等标识字段。即便如此，生成的报告仍属于设备事实，附到 Issue 或发给他人之前请自行复核内容。

脚本不是权限边界：它们以调用者的权限运行，也无法阻止宿主 Agent 执行其他命令。请只运行你审阅过的版本，不要从未经核对的来源下载并直接执行。
