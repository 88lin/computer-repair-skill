# 贡献指南

感谢改进 Computer Repair Skill。提交 Issue 或 Pull Request 前，请先确认变更属于电脑诊断、修复、安全工作流、平台工具映射或 Playbook 维护范围。

## 开发原则

- 保持 `SKILL.md` 精简，把具体平台和专项流程放在 `references/` 中按需加载。
- 保持只读优先。任何安装、删除、权限、服务、启动项、凭据或安全控制变更，都必须先说明影响、回滚和验证方式，并等待用户确认。
- 不假设宿主存在 Playbook 中的语义工具名；通过 `tool-contract.md` 映射到宿主能力或平台原生命令。
- 不提交密码、令牌、私钥、Cookie、真实设备标识或未经脱敏的日志。
- 不在网页读取失败后根据标题或 URL 补造内容。

## 维护 Skill 入口元数据

- 按 [Agent Skills 规范](https://agentskills.io/specification)维护 `SKILL.md` frontmatter。本项目只使用各支持端均可识别的必填字段 `name` 和 `description`；不要添加没有实际用途的可选字段。
- 按[触发描述优化指南](https://agentskills.io/skill-creation/optimizing-descriptions)让 `description` 以 `Use this skill when ...` 表达用户意图，覆盖常见自然语言症状，并写明容易误触的相邻场景。本项目将描述限制为 600 个字符、80 个空格分词，严于规范的 1024 字符上限。
- 宿主能力、权限、网络和交互要求写在 `SKILL.md` 正文的能力检查中，避免可选 frontmatter 字段造成客户端兼容差异。
- 保持 `SKILL.md` 在 500 行以内。具体平台、工具和专项流程放在 `references/`，并在核心工作流中明确说明何时加载，避免一次读取全部资料。

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
- emoji 的来源约定：`source: bundled` 的 Playbook 保留上游已有图标，用于在支持图标的 Skill 浏览器中快速识别；`source: local` 的新 Playbook 默认省略，只有确实有分类价值时才按需添加。emoji 只服务于展示，不参与路由或执行逻辑；校验器会要求它是单个 emoji。
- 数量统计只包含可执行 Playbook；`playbook-authoring.md` 和 `playbook-index.md` 是参考文档，不计入 62 个 Playbook。
- 给出激活条件、快速只读检查、标准诊断路径、修复前确认、验证、限制和升级信息。
- 对平台命令提供明确失败处理，不使用宽泛删除或不可审计的命令拼接。
- 需要凭据时使用宿主安全输入能力，不在上下文或命令历史中回显秘密。

## 本地验证

仓库只要求 Python 3，无第三方包：

```bash
python tools/extract_data.py --check
python tests/validate_skill.py
```

官网的 `docs/assets/js/playbooks.js` 是生成文件。修改 Playbook 的 frontmatter、
路由索引或 `tools/site_catalog.json` 后，先运行 `python tools/extract_data.py` 更新
它，再运行上面的 `--check`；不要直接手工编辑压缩后的 JavaScript。

还应在对应平台测试安装器：

```powershell
.\scripts\install.ps1 -Target custom -Destination "$env:TEMP\computer-repair-skills-test"
```

```bash
./scripts/install.sh --target custom --destination "$(mktemp -d)/skills"
```

提交前检查 `git diff`，确保没有打包文件、缓存、凭据或无关改动。安全漏洞不要创建公开 Issue，请按 [SECURITY.md](SECURITY.md) 报告。
