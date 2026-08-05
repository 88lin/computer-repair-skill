# Changelog

本文件记录 Computer Repair Skill 的对外可见变更，格式参考
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。

版本号同时写在 `skills/computer-repair-skill/SKILL.md` 的 `version` 字段和
`skills/computer-repair-skill/agents/openai.yaml` 里，`tests/validate_skill.py`
会校验两者一致并要求本文件存在对应条目。1.1.0 之前的变更请查阅 Git 历史。

## [1.1.0] - 2026-08-05

本次发布集中修复第三方审阅报告中确认成立的问题，并补上审阅遗漏的同类缺陷。
所有命令与配置字段均按官方文档核对，不再依赖记忆推断。

### Added

- `SKILL.md` 新增 `when_to_use`，列出常见中文求助说法（C 盘变红、开机很慢、
  把应用迁到 D 盘、蓝屏进不了系统等），提升中文提问的命中率。
- `SKILL.md` 与 `agents/openai.yaml` 新增 `version` 字段，并新增本 CHANGELOG。
- `playbook-index.md` 新增「存储与迁移：先选对入口」决策清单，把六个都会被
  「C 盘满了」命中的流程按真实诉求分流。
- 六个存储/迁移 Playbook 新增统一的「相邻流程」互链区块。
- `playbook-setup-openclaw-config-reference.md` 补齐 `typingIndicator`、
  `resolveSenderNames`、`groups.<group-id>.requireMention`、`gateway.mode`
  四个字段，并写清环境变量解析优先级。
- `playbook-windows-printer-repair.md` 在安装厂商驱动前要求校验 SHA256 与
  Authenticode 签名。
- `playbook-setup-wifi-profile.md` 补上可执行的 Windows WLAN 配置文件分支，
  并要求验证后立即删除含密码的临时 XML。
- `tests/validate_skill.py` 新增三类断言：路由表表头与列数一致、站点数据
  （`docs/assets/js/playbooks.js`）与 frontmatter 同步、版本号在 SKILL.md
  与 `agents/openai.yaml` 之间一致且 CHANGELOG 有对应条目。

### Changed

- `playbook-setup-openclaw-china-models.md` 更新为当前在售的模型 id，并把
  Moonshot 说明改为外部插件安装流程，区分 Moonshot 与 Kimi Coding 两个
  独立 Provider；配置示例的 `api` 值改为 `openai-completions`。
- `playbook-setup-openclaw-uninstall.md` 以官方 `openclaw uninstall` 为主路径，
  补上 Windows 计划任务与桌面端清理，手工删除降级为兜底。
- `playbook-setup-openclaw-add-feishu.md` 的批量导入权限收敛到最小租户权限，
  文档/表格/知识库权限改为显式可选。
- `playbook-windows-boot-failure-triage.md` 改为按实际屏幕文案分流，移除无法
  在真实机器上出现的固件字符串。
- `playbook-setup-ssh-key.md` 默认要求交互式输入口令，配合 ssh-agent 与
  钥匙串；空口令改为需要显式记录的例外。
- `playbook-setup-homebrew.md` 改为探测实际安装前缀与当前 Shell 配置文件，
  不再依赖 `uname -m` 推断。
- `playbook-index.md` 的 OpenClaw 路由表补齐「平台」与「触发症状」列，八张
  路由表统一表头。
- `tool-contract.md` 明确 `knowledge_search` 为规范名称，`search_knowledge`
  仅作兼容别名保留。
- `.github/workflows/star-history.yml` 把第三方 Action 从可变标签 `v1` 固定到
  `v1.3.5` 对应的提交 SHA。

### Fixed

- `playbook-windows-update-troubleshooting.md` 不再把第三方 PSWindowsUpdate
  的 `Get-WindowsUpdate` 当作内置命令，改用 `Get-HotFix` 与内置
  `Microsoft.Update.Session` 搜索器；补齐未标注语言的代码块。
- 停止通过命令行参数传递机密：飞书、飞书官方插件、Telegram、国产模型、
  基础配置和排错共 6 个 Playbook 改为写入 `~/.openclaw/.env` 后用单引号
  引用变量名，避免机密进入进程列表、Shell 历史或明文配置文件。
- 移除 macOS 上已不存在的命令与路径：`com.apple.alf` plist 直读（4 处）、
  `MRT.app`、`security find-generic-password -D "AirPort network password"`。
- `playbook-backup-verify-restore.md` 不再调用无 `-status` 开关的
  `fhmanagew.exe`，改用计划任务与配置文件状态判断文件历史记录。
- `playbook-browser-security-audit.md` 不再用文件大小推测密码条数，改为复制
  数据库后用 `sqlite3` 计数（Chrome 会锁定在用数据库）。
- `playbook-windows-partition-resize-audit.md` 把已停止支持的 Windows To Go
  改为 WinRE/WinPE/厂商启动介质。
- `playbook-windows-network-diagnostics.md` 补上 WinHTTP 与 WinINET 的区别，
  说明两者不一致本身就是结论。
- `playbook-windows-application-lifecycle-audit.md` 区分 Windows 精简工具
  Sparkle 与 macOS 更新框架 Sparkle。
- `playbook-setup-backup.md` 补上 Time Machine 网络目标的钥匙串挂载前置条件
  与 `tmutil setdestination -a` 的追加语义。
- 同步 `docs/assets/js/playbooks.js` 中本次修改文件的 `last_reviewed`。

### Known issues

- `docs/assets/js/playbooks.js` 声明由 `python3 tools/extract_data.py` 生成，
  但该脚本不在仓库内，本次仍需手工同步该文件。已单独开 issue 跟踪。
- 2026-03 引入的上游 Playbook 中，本次未涉及的文件仍待逐个复核。
