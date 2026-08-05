# Playbook 工具兼容契约

Playbook 中的工具名是能力别名。宿主 Agent 无需提供同名工具，但执行语义、输入范围、审批和验证必须一致。

## 通用工具

| Playbook 名称 | 宿主行为 |
|---|---|
| `shell_run` | 使用宿主终端工具运行当前平台命令。先确定 Shell，设置合理超时，保留退出码。状态变更前取得确认。 |
| `ui_spa` | 在消息中展示诊断、计划、影响、回滚和下一动作。`RUN_STEP` 表示等待用户批准后由 Agent 执行；`WAIT_FOR_USER` 表示用户完成 GUI、手机或交互式步骤。 |
| `ui_user_question` | 使用宿主提问能力。选项、普通文本和秘密输入三种模式保持互斥。 |
| `ui_done` | 仅在验证成功后给出完成摘要和前后数据。 |
| `ui_info` | 给出事实性说明、剩余阻点或需要人工处理的部分。 |
| `secure_input` | 使用宿主的遮罩输入或秘密管理功能。缺少此能力时，让用户在本机设置变量或文件，不接收秘密正文。 |
| `write_secret` | 让用户或受信任的本机命令从环境变量/秘密存储以安全文件权限写入目标文件；验证文件和键存在，但不读取或打印值。 |
| `activate_playbook` | 从 `playbook-index.md` 找到对应 `references/playbook-*.md` 并读取。 |
| `knowledge_search` | 规范名称。使用 `rg`、宿主搜索或结构化文件搜索定位本地知识。别名 `search_knowledge` 语义完全相同，仅为兼容早期 Playbook 保留；新写的 Playbook 一律使用 `knowledge_search`。 |
| `knowledge_read` | 使用宿主文件读取工具读取已选知识文件。 |
| `write_knowledge` | 经用户确认后写入指定 Markdown 知识目录。 |
| `web_fetch` | 使用宿主联网工具读取明确 URL，记录最终 URL、状态和获取日期。 |

## 平台工具

按实际操作系统加载一份平台映射：

- Windows：`tools-windows.md`
- macOS：`tools-macos.md`
- Linux：`tools-linux.md`

优先调用宿主已有的专用工具。例如宿主直接提供进程、服务或网络查询时，使用该工具并保持 Playbook 所需字段。否则执行映射中的平台原生命令。

Windows 专项 Playbook 使用的 `win_path_inventory`、`win_file_hash`、`win_registry_snapshot`、`win_recycle_path`、`win_policy_list`、`win_recovery_image_scan`、`win_package_inventory`、`win_package_metadata`、`win_package_install`、`win_package_uninstall` 和 `win_persistence_snapshot` 也只是能力别名。迁移与恢复流程新增的 `win_path_metadata`、`win_path_lock_check`、`win_directory_size`、`win_copy_verify`、`win_junction_create`、`win_junction_inspect`、`win_junction_remove`、`win_json_atomic_write`、`win_registry_query` 和 `win_operation_log` 同样按平台映射执行。宿主没有同名工具时，读取 `tools-windows.md` 的推荐实现；任何回收、注册表导出、链接创建/删除、文件复制、包安装/卸载或管理员操作仍遵守安全策略并单独确认。

## 结果契约

每次诊断至少保留：

- 动作或命令名称。
- 目标主机、路径、进程、服务或 URL。
- 退出码或结构化成功状态。
- 与判断相关的关键输出。
- 执行时间或采样时间。

每次状态变更额外保留：

- 用户已批准的计划。
- 变更前状态。
- 实际改动。
- 回滚方式。
- 变更后验证。

## 失败处理

- 命令不存在：查找当前平台等价命令，不直接跳过检查。
- 权限不足：说明需要的权限和具体动作，等待用户确认后再提升权限。
- 命令超时：终止当前调用，检查是否留下后台进程，再选择更窄的查询。
- 输出格式变化：读取原始输出并使用结构化解析，不依赖固定列宽。
- 目标不存在：确认路径、服务名或进程 ID 是否已变化，再更新结论。

## `write_secret` 的安全写入

`write_secret` 必须在写入秘密字节之前建立目标文件的限制权限，不能先按默认权限创建
或追加秘密、再用 `chmod`/ACL 收紧。具体要求：

- POSIX：新文件以 `0600` 创建（实现可使用 `umask 077` 或等价的原子创建）；已有文件在追加前先收紧到 `0600`。
- Windows：写入前先应用只允许当前用户 SID 和 LocalSystem well-known SID `S-1-5-18` 的 ACL；使用 `icacls` 时给 SID 加 `*` 前缀，避免本地化账户名。
- 宿主无法保证上述写入前权限时必须拒绝写入，而不是留下短暂的默认权限文件。

写入后的 `chmod 600` 或 ACL 命令只能作为复核/修复步骤，不能替代写入前保护。
