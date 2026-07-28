# 贡献指南

感谢改进 Computer Repair Skill。提交 Issue 或 Pull Request 前，请先确认变更属于电脑诊断、修复、安全工作流、平台工具映射或 Playbook 维护范围。

## 开发原则

- 保持 `SKILL.md` 精简，把具体平台和专项流程放在 `references/` 中按需加载。
- 保持只读优先。任何安装、删除、权限、服务、启动项、凭据或安全控制变更，都必须先说明影响、回滚和验证方式，并等待用户确认。
- 不假设宿主存在 Playbook 中的语义工具名；通过 `tool-contract.md` 映射到宿主能力或平台原生命令。
- 不提交密码、令牌、私钥、Cookie、真实设备标识或未经脱敏的日志。
- 不在网页读取失败后根据标题或 URL 补造内容。

## 维护 Skill 入口元数据

- 按 [Agent Skills 规范](https://agentskills.io/specification)维护 `SKILL.md` frontmatter。本项目只使用必填字段 `name`、`description` 和可选字段 `license`（固定为 `AGPL-3.0`，与 `LICENSE` 保持一致）；不要添加没有实际用途的其他可选字段，校验器会拒绝未登记字段。
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
category: windows-repair-boot-hardware
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---
```

字段约束由 `tests/validate_skill.py` 强制执行：`name` 必须与文件名 `playbook-<name>.md` 对应且全库唯一；`platform` 取 `all`/`windows`/`macos`/`linux`，且 `name` 以平台名开头时必须匹配；`category` 必须是 `tests/playbook_registry.py` 中 `CATEGORIES` 已登记的 slug；`last_reviewed` 是不晚于今天、且距今不超过 365 天的 `YYYY-MM-DD`；`source: local` 时 `author` 必须是 `computer-repair-skill-maintainers`。除 `emoji` 外不接受其他字段。

新 Playbook 还需要：

- 使用 `playbook-<slug>.md` 文件名，并登记到 `references/playbook-index.md`。
- `## Tools referenced` 至少声明一个语义工具别名，且必须已在 `tool-contract.md` 或平台工具表中登记；正文里用反引号提到的已登记别名也必须一并声明（校验器双向比对）。
- 让 frontmatter 的 `description` 不超过 120 个字符且只描述一个明确入口；不要把多个能力堆在同一行。
- `emoji` 是可选字段；需要使用时只填一个合适的 emoji，没有合适图标就省略。
- emoji 的来源约定：`source: bundled` 的 Playbook 保留上游已有图标，用于在支持图标的 Skill 浏览器中快速识别；`source: local` 的新 Playbook 默认省略，只有确实有分类价值时才按需添加。emoji 只服务于展示，不参与路由或执行逻辑；校验器会要求它是单个 emoji。
- 数量统计只包含可执行 Playbook；`playbook-authoring.md` 和 `playbook-index.md` 是参考文档，不计入 Playbook 总数。总数与分类计数由 `tests/playbook_registry.py` 从 frontmatter 派生，不要手工改 README 里的数字。
- 给出激活条件、快速只读检查、标准诊断路径、修复前确认、验证、限制和升级信息。
- 对平台命令提供明确失败处理，不使用宽泛删除或不可审计的命令拼接。
- 需要凭据时使用宿主安全输入能力，不在上下文或命令历史中回显秘密。

## 新增分类

分类是派生数据的真源，顺序如下：

1. 在 `tests/playbook_registry.py` 的 `CATEGORIES` 中登记新条目（slug、索引标题、README 标签）。slug 只用小写字母和连字符。
2. 给 Playbook 的 frontmatter 填上新 slug。
3. 在 `references/playbook-index.md` 手工添加对应的 `## <索引标题>` 章节和表格行；索引章节和表格行不是自动生成的。
4. 在 `README.md` 的能力范围里手工添加 `### <标签>（N）` 小节；括号里的数字之后由生成器回写。
5. 运行 `python tests/playbook_registry.py --write` 刷新 README 分类表、各小节计数和 Playbook 总数，再运行 `--check` 确认一致。

生成器会保留分类表"主要内容"列里已有的人工文案，只在新分类没有文案时填占位描述，请手工替换成真实内容。

## 本地验证

核心校验只需要 Python 3，无第三方包：

```bash
# 结构、元数据、链接、工具契约、格式与安全规则。CI 使用 --strict，warning 也会失败
python tests/validate_skill.py --strict

# 分类登记、分类计数与 Playbook 总数是否与 frontmatter 一致
python tests/playbook_registry.py --check

# 把派生数字回写到 README（幂等，重复执行不会产生新改动）
python tests/playbook_registry.py --write
```

校验器自身有回归测试，需要 pytest：

```bash
python -m pytest tests/ -q
```

CI 还会跑五套 lint。装好对应工具后可以在本地复现：

```bash
markdownlint-cli2                                            # Markdown，配置见 .markdownlint-cli2.jsonc
ruff check . && ruff format --check .                        # Python，配置见 ruff.toml
shellcheck --severity=style --external-sources scripts/*.sh  # Shell 脚本
actionlint                                                   # GitHub Actions 工作流
```

```powershell
Invoke-ScriptAnalyzer -Path ./scripts -Recurse -Severity Error, Warning
```

还应在对应平台测试安装器和只读采集脚本：

```powershell
.\scripts\install.ps1 -Target custom -Destination "$env:TEMP\computer-repair-skills-test"
.\scripts\install.ps1 -Target custom -Destination "$env:TEMP\computer-repair-skills-test" -Verify
.\scripts\collect-health.ps1 -Output "$env:TEMP\health.md"
```

```bash
./scripts/install.sh --target custom --destination "$(mktemp -d)/skills"
./scripts/install.sh --target custom --destination "$(mktemp -d)/skills" --dry-run
./scripts/collect-health.sh --output "$(mktemp -d)/health.md"
```

提交前检查 `git diff`，确保没有打包文件、缓存、凭据或无关改动。安全漏洞不要创建公开 Issue，请按 [SECURITY.md](SECURITY.md) 报告。
