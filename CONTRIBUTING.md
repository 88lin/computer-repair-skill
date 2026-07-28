# 贡献指南

感谢改进 Computer Repair Skill。提交 Issue 或 Pull Request 前，请先确认变更属于电脑诊断、修复、安全工作流、平台工具映射或 Playbook 维护范围。

## 开发原则

- 保持 `SKILL.md` 精简，把具体平台和专项流程放在 `references/` 中按需加载。
- 保持只读优先。任何安装、删除、权限、服务、启动项、凭据或安全控制变更，都必须先说明影响、回滚和验证方式，并等待用户确认。
- 不假设宿主存在 Playbook 中的语义工具名；通过 `tool-contract.md` 映射到宿主能力或平台原生命令。
- 不提交密码、令牌、私钥、Cookie、真实设备标识或未经脱敏的日志。
- 不在网页读取失败后根据标题或 URL 补造内容。

## 修改上游 Playbook

`source: bundled` 的文件来自 `NOTICE` 记录的上游基准提交，面向 Agent 的措辞和 author 标记已做中性化适配。项目维护的本地扩展使用 `source: local` 标记；来源和归属以 `NOTICE` 为准。同步上游时保留现有行为与中性命名，并在 Pull Request 中注明上游提交、变更文件和行为差异。

项目新增 Playbook 使用以下元数据：

```yaml
---
name: example-playbook
description: Describe the exact task and trigger
platform: windows
last_reviewed: YYYY-MM-DD
author: computer-repair-skill-maintainers
source: local
---
```

新 Playbook 还需要：

- 使用 `playbook-<slug>.md` 文件名，并登记到 `references/playbook-index.md`。
- 让 frontmatter 的 `description` 不超过 120 个字符且只描述一个明确入口；不要把多个能力堆在同一行。
- `emoji` 是可选字段；需要使用时只填一个合适的 emoji，没有合适图标就省略。
- 给出激活条件、快速只读检查、标准诊断路径、修复前确认、验证、限制和升级信息。
- 对平台命令提供明确失败处理，不使用宽泛删除或不可审计的命令拼接。
- 需要凭据时使用宿主安全输入能力，不在上下文或命令历史中回显秘密。

## 本地验证

仓库只要求 Python 3，无第三方包：

```bash
python tests/validate_skill.py
```

还应在对应平台测试安装器：

```powershell
.\scripts\install.ps1 -Target custom -Destination "$env:TEMP\computer-repair-skills-test"
```

```bash
./scripts/install.sh --target custom --destination "$(mktemp -d)/skills"
```

提交前检查 `git diff`，确保没有打包文件、缓存、凭据或无关改动。安全漏洞不要创建公开 Issue，请按 [SECURITY.md](SECURITY.md) 报告。
