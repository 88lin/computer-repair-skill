# 项目审计与修复记录

## 2026-11-29：参考项目增量复核

核对 `NOTICE` 所列 18 个仓库的分支头。主上游、RogueCleaner、pinkbin、WxCleaner、ZyperWinOptimize、disk-raccoon 和 windows-disk-cleaner-skill 的复核提交仍是当前分支头。viap 的旧样本没有 Git 元数据，以 2026-08-05 当日公开提交作为时间锚点。

| 参考项目 | 复核证据 | 本轮判断 |
|---|---|---|
| WindowsCleaner | [e953870 → 6e7c133](https://github.com/darkmatter2048/WindowsCleaner/compare/e953870f554665841ef2c94aeddc4742ea320415...6e7c133768a61f2d5facecace1226c1251ed2e5a) | 合并重叠的清理命中，保留各条规则的证据和排除项。 |
| FluentCleaner | [9df539c → 3462547](https://github.com/builtbybel/FluentCleaner/compare/9df539ca504ab0ec38f550fa53b07148bc93ce75...34625475a08445ae8f5e1aecf51db9fdbe7f84bd) | 外部规则缺少或无法识别默认值时保持未勾选。 |
| viap | [68da856 → d0611a7](https://github.com/Chunyu33/viap/compare/68da8564fdcacf167d4883217e454747353cc175...d0611a7fadaca1afaaeb81b46938339556babecf) | 补强迁移中断、目标卷离线、缺失记录和卸载完成判定。 |
| just-the-browser | [ec96b1b → 312caf3](https://github.com/corbindavenport/just-the-browser/compare/ec96b1b4b6d387e32ad23341fb086ee57ccd338c...312caf3e9e248ba81dbc79ae093dcb9fe566ae8d) | 按 [Chrome](https://chromeenterprise.google/policies/autofill-gen-ai-settings/) 和 [Edge](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-browser-policies/edgeautofillmlenabled) 文档补充只读审计。 |
| optimizerDuck | [5aea652 → 4c33b61](https://github.com/itsfatduck/optimizerDuck/compare/5aea6522248e71ef30765a3f8a9693adb8a95224...4c33b61371594ff66740cf1c280414c1390d7c63) | 版本适用性、状态核查和回滚已有独立流程，保留按设备逐项评估。 |
| Winhance | [f23d554 → 60f60cb](https://github.com/memstechtips/Winhance/compare/f23d554eb2d6400b1827bcc46b91294ffa53fbc9...60f60cbf0cce10b10344cc04db96eeba3823d50b) | 配置差异预览已覆盖，安装镜像工作流与本 Skill 的维修范围不同。 |
| Atlas | [1ed9630 → a78dd07](https://github.com/Atlas-OS/Atlas/compare/1ed9630616b29f0c7974e8bd76a94fc06f60388c...a78dd0710cb927043967a0de9ed81b508bb177d7) | 升级保留偏好针对 Atlas 自有预设，现有 Windows 配置流程已有逐项状态记录。 |
| windows-update-disabler | [bd98afc → 440e873](https://github.com/tsgrgo/windows-update-disabler/compare/bd98afcfcbd6ed50480bc70d32e5a5ca8265a34d...440e8735fc2d5b88d5e30f3664ff4571a8fb8816) | 变更只涉及 README 下载说明。 |
| Malware-Patch | [d7018e5 → b390e8b](https://github.com/the1812/Malware-Patch/compare/d7018e5c2d404ccef294ef4f61a5bc6bffa1510e...b390e8b4dbda060fd601c86d98a077346bc2428b) | 更新证书清单，本 Skill 继续按现场签名及独立身份信号判定。 |
| digler | [2f62fc7 → fedd1a9](https://github.com/ostafen/digler/compare/2f62fc7e90f5c4123e0f0fa9a31c0128bfffc32c...fedd1a9496c3daaccf9dd434c32d100fd2a65827) | 修复 macOS 原始设备读取和工具输出参数，当前 Windows 镜像恢复流程不依赖该 CLI。 |
| Sparkle | [cce02cd → d1721a3](https://github.com/thedogecraft/sparkle/compare/cce02cd5517ee0f01e83d41a3c2fb7547e506352...d1721a326e1a1d8622980ee18dd43027474c6ab5) | 新增更新模式预设，现有 Windows Update 流程继续以诊断和保留更新能力为主。 |

大型差异按与 Skill 相关的文件、提交和发布说明抽查。采纳项均为工作流改进，来源记录同步到随包分发的 `NOTICE`。

仓库校验、两项生成检查和 25 项核心测试通过。PowerShell 5.1 与 7 的临时目录实验验证了先复制普通文件和零字节文件、仅移除目录联接、再同卷切换路径的步骤。

## 2026-09-29：Windows 存储流程增量复核

参考 `std-microblock/windows-disk-cleaner-skill` 的提交
`ea986d425d50a7aacfc6ea6a3bdb0248ac045095`，读取 Skill/CLI 文档及扫描、比较、
Git 审计、删除前复核相关源码，核验 Apache-2.0 许可证。只吸收行为设计，未运行或复制上游程序。

本轮改进四个 Windows 存储相关 Playbook，新增两份按需加载的参考：扫描后端与完整度、
快照下钻和空间核算，以及 Git/构建产物/服务数据库/模型/虚拟磁盘的数据边界。
同时纠正普通迁移被导向分区调整、同盘隔离误计释放空间的流程问题，更新路由、网站数据和分发 NOTICE。

后续复核增加可选只读 `git_storage_audit.py`，提供本地 JSON 报告、总时间预算和完整度标记，
隔离继承的 Git 环境与全局配置，禁用仓库外部过滤器；补充分发脚本的安装器测试。
普通文件 offload 进一步与保留原路径的 Junction 迁移分开，避免强制创建链接。

验证：

- 仓库专用校验通过：64 个 Playbook，结构、路由、链接、来源与安全扫描正常。
- 网站数据和页面的两个生成器 `--check` 通过；全量核心回归测试 25 项通过（原有 16 项加新增 9 项）。
- 新增 Git 审计的 9 项行为测试通过，包括未提交/忽略内容、stash、缓存远端、重命名、
  工作树/子模块标记、无提交/裸仓库、超时/输出限制与环境隔离；外部过滤器测试包含实际可执行的正向对照，确认审计期间未调用它。
- 新增参考中的 7 条 Git 命令分别在 PowerShell 7 与 Windows PowerShell 5.1 的临时仓库执行成功，
  检出修改/暂存、未跟踪/忽略目录、stash、本地分支和关联工作树；检查前后夹具文件哈希一致。
- 通用 `skill-creator/quick_validate.py` 不接受项目已有的 `version`、`when_to_use` 字段；
  这两个字段及入口文件本轮未改，继续由仓库专用校验器按 CONTRIBUTING 中的约定验证。

本轮包含 Skill 指令、工具映射和只读 Git 辅助脚本，未测试 NTFS/ReFS 原始扫描速度、真实磁盘删除或远端 Git 覆盖，
也未改动官网交互；不能据此宣称已集成快速扫描引擎、完成浏览器验证或真实空间回收。

## 2026-09-28：仓库级审计

日期：2026-09-28

本轮完成仓库级检查，并直接修复安装、构建、发布、官网交互和维修指令中的可确认问题。现有验证器在修改前已通过，因此新增了覆盖异常路径的行为测试。

## 检查范围

- 64 个 Playbook 的结构、元数据、路由、平台工具契约、链接与高风险命令模式；重点复核清理、凭据、备份恢复、应用修复、性能、CUDA、OpenClaw 卸载和系统更新流程。
- PowerShell 与 Bash 安装器的路径、备份、并发、失败恢复和分发完整性。
- Python 数据生成、英文页面生成、发布说明提取与 GitHub Actions 发布判定。
- 中英文官网的搜索、筛选、键盘焦点、弹窗、安装选项卡、剪贴板回退、卡片滚动、移动端与静态回退。
- 仓库文本中的高置信度凭据模式、许可证与归属一致性。

## 已修复问题

| 优先级 | 问题与影响 | 修复 |
|---|---|---|
| P1 | macOS 清理流程批量永久删除应用缓存、废纸篓、Mail 下载与模拟器数据，恢复边界不清晰 | 改为具体目标盘点、确认、隔离和恢复清单；废纸篓永久清空独立处理 |
| P1 | 应用修复把“应用已损坏”直接归因于隔离标记，并建议绕过安全拦截；重装时可能删除 Application Support 中的用户数据 | 先检查来源、签名和架构；保留应用数据，只处理证据充分的缓存子项 |
| P1 | SIGTERM 被描述为保证保存会话，性能维护默认运行 purge，并建议无人值守清理 | 优先应用正常退出，说明未保存数据风险；依据压力与交换采样诊断，定时任务默认只读 |
| P1 | 浏览器凭据审计复制密码库，清理建议删除整个数据库；主数据库复制还会漏掉 WAL 中的变更 | 默认使用浏览器界面，明确授权后只读聚合计数；禁止直接删除密码库与无边界密钥链输出 |
| P1 | OpenClaw 重复插件直接递归删除；卸载从环境变量重新解析目标，可能偏离已批准范围 | 核对实际 profile、插件身份与物理路径；依据已批准清单隔离，保护真实用户目录和独立配置文件 |
| P1 | 安装器允许源码与目标重叠，强制更新链接目标或并发执行可能破坏安装/备份关系 | 拒绝重叠、文件及链接路径，增加独占锁、完整文件检查、唯一备份和故障恢复验证 |
| P2 | CUDA 工具包被错误描述为自动安装驱动，并建议关闭 Secure Boot 或通配符清除驱动 | 区分工具包与驱动，检查兼容性，保留安全启动，按明确包事务恢复 |
| P2 | 备份测试使用固定目录、错误的 Borg 提取选项，并混淆 RPO/RTO 目标与测量值 | 私有唯一恢复目录、按 Borg 版本选择命令、按备份版本核验；区分目标与实际观测 |
| P2 | Windows 更新卡住后建议按等待时间强制重启 | 先核对更新阶段、日志和活动，按批准的恢复流程处理 |
| P2 | 发布 tag 成功而 Release 失败后无法重试；远端错误被视为版本不存在 | 独立检查 Release/tag，只有 404 表示缺失，tag 已存在时检出该版本验证后补发 |
| P2 | 数据产物缺失时无法重建，重复路由可进入输出，英文纯文本译文可被解释为 HTML | 支持缺失文件重建、拒绝重复条目/ID、区分纯文本转义与显式 HTML |
| P2 | 键盘筛选丢失焦点、连续复制后标签不恢复、卡片焦点仍在时恢复滚动、数据缺失清空静态索引 | 保留焦点、合并复制定时器、剪贴板失败回退、独立暂停状态、保留静态表格 |
| P3 | 缺少证据来源的成功率数字、维护文档与版本字段/构建步骤不一致，凭据扫描未覆盖官网源码 | 清理无依据数字，更新维护说明，扩展 JSON/JS/HTML 扫描并接入行为测试 |

## 验证结果

- `python tests/validate_skill.py`：通过，64 个 Playbook。
- `python tools/extract_data.py --check`、`python tools/build_site.py --check`：通过。
- `python -m unittest discover -s tests -p "test_*.py"`：16 项测试通过；安装器测试包含 PowerShell 7 与 Git Bash 的独立子场景，复查新增失效链接目标和文件/目录锁的互斥检查。
- 额外使用 Windows PowerShell 5.1 执行安装器测试：通过。包括首次安装、覆盖拒绝、备份、切换失败回滚、目录冲突、链接目标、缺少文件和安装锁。
- 发布判定使用本地模拟的 Git/GitHub 响应覆盖已发布、仅有 tag、全新版本、API 403 四种状态，未调用远端发布接口。
- `python tests/browser_site.py --channel chrome --output artifacts/site-audit`：中英文交互、390px 移动端、禁用 JS、数据文件缺失、滚动暂停均通过；没有页面脚本异常。移动端截图已目视检查。
- `node --check docs/assets/js/site.js` 与 `git diff --check`：通过。
- 实现提交 `8137479` 推送后，[GitHub Actions](https://github.com/88lin/computer-repair-skill/actions/runs/36421241444) 的 Ubuntu、Windows 两个作业均通过；[Release 工作流](https://github.com/88lin/computer-repair-skill/actions/runs/36421241418) 正常识别已发布的 `v1.2.0` 并跳过重复发布。

浏览器测试只读取本地页面、屏蔽 HTTP(S)，安装器测试只写临时目录。核心行为测试使用 Python 标准库；浏览器测试单独依赖 Playwright。

## 验证边界与维护注意事项

- 本轮没有在 macOS/Linux 真机执行维修动作，没有执行真实卸载、凭据清理、驱动安装、系统更新或分区操作。Bash 安装器已在 Windows Git Bash 与 GitHub Actions 的原生 Ubuntu 环境验证；macOS 安装器尚未实机验证。
- 未对外部供应商当前下载地址、包版本和所有联网流程逐项复核；执行时仍需依据当前官方文档与实际设备状态确认。
- 本地审计验证没有调用 GitHub Release 发布接口。审计修复已纳入 `1.3.0` 变更记录；提交和发布状态以 Git 与 GitHub Release 记录为准。
- 安装器有意拒绝包含符号链接或 Junction 的安装路径。由其他工具管理的链接安装应由原工具更新；自定义安装请选择实际目录。
- PowerShell 使用原子的 `CreateNew` 锁文件，Bash 使用独占锁目录，两者共享锁路径。强制终止安装进程可能保留锁与暂存/备份。重试前确认没有活跃安装，检查恢复状态，再移除明确的锁文件或锁目录；不要直接批量删除恢复文件。
- 凭据扫描是高置信度模式检查，不等同于发现所有格式的秘密；文档静态检查也不等同于在每种设备上验证每条命令。
