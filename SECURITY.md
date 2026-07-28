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
