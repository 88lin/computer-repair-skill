# Windows 开发目录与持久数据检查

当存储候选包含 Git 仓库、编译产物、数据库、服务数据、模型或虚拟磁盘时按需读取。只做元数据审计；本文件不授权删除，也不要求读取源码、数据库记录或秘密配置内容。

## Git 仓库：远端有代码不等于本机有完整备份

发现 `.git` 目录或指向外部元数据的 `.git` 文件后，检查实际仓库根、Git 元数据位置和 common dir。不要因为 HEAD 已推送、工作区显示 clean、目录很旧或文件被 gitignore 忽略就判定可删。

### 可选只读脚本

宿主已具备 Python 3.10+ 和 Git 时，可使用随 Skill 分发的 [git_storage_audit.py](../scripts/git_storage_audit.py)。把下面两条绝对路径替换为实际 Skill 安装位置和已确认的仓库位置：

```powershell
python 'D:\AgentSkills\computer-repair-skill\scripts\git_storage_audit.py' 'D:\Projects\example' --timeout 20 --samples 20
```

脚本仅输出本地 JSON，不联网、不 fetch、不清理、不修改仓库，也不自行保存持久报告。命令输出先暂存到系统临时文件并自动关闭，单项最多读取 1 MiB 到内存；超量、失败、超时会让 `complete=false`。`--timeout` 是全部 Git 查询共用的时间预算（大于 0、至多 300 秒），`--samples` 仅限制展示数量（0～100），不会裁剪正常范围内的计数。退出码 0 表示本地检查完成，2 表示输入/依赖无效或检查不完整；命令行参数格式错误也返回 2，需要同时核对是否产生 JSON。

`complete=true` **不是可删除结论**；`remote_verified` 始终为 false，所有远端覆盖信息只来自本地缓存。未跟踪/忽略目录可能被 Git 折叠，计数单位是 Git 条目，不是后代文件数。子模块只识别索引中的 gitlink，不递归读取其工作树，需对每个实际目录另行审计；关联工作树和外部 Git 元数据也须分别检查。

脚本隔离系统/全局 Git 配置和继承的 `GIT_*` 环境变量，禁用 fsmonitor 及仓库配置的 clean/process/smudge filters，防止状态检查调用这些外部程序。这可能改变内容转换后的状态判断，报告会保留配置范围和过滤器提示；不要把此模式等同于用户日常 Git 环境。错误原文可能含路径或凭据配置，脚本仅报告退出码与状态，需要时在本机定向排查。Git 不存在、所有权检查失败或目录没有提交时保留未知状态，不安装依赖或放宽 `safe.directory`。

### 原生命令回退

在已确认的仓库上用结构化参数执行以下本地检查。`$repoPath` 必须替换为用户指定的字面绝对路径；不把输出中的路径、分支名或文字拼接成命令。命令逐条记录退出码，失败记为 unknown，不按空结果处理。

以下回退命令适用于已审查 Git 配置的仓库：仅关闭 fsmonitor 不会禁用 clean/process filters，`status` 仍可能执行这些外部程序。配置不明时先使用上面的隔离脚本，或仅检查引用等不需要比较工作区内容的元数据。不要为使用脚本自动安装 Python。

```powershell
$repoPath = 'D:\Projects\example'
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath rev-parse --show-toplevel --absolute-git-dir --git-common-dir
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath status --porcelain=v1 --untracked-files=normal --ignored=matching --ignore-submodules=none
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath for-each-ref '--format=%(refname) %(objectname) %(upstream:short) %(upstream:track)' refs/heads refs/tags
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath stash list '--format=%gd'
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath worktree list --porcelain
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath submodule status --recursive
git --no-optional-locks --no-pager -c core.fsmonitor=false -C $repoPath rev-list --count --branches --tags HEAD --not --remotes
```

关闭 optional locks 防止只读盘点刷新索引，关闭 fsmonitor 防止状态查询调用仓库配置的监控程序。限制命令耗时和返回样例；状态输出里的折叠目录只说明含有未跟踪/忽略内容，不代表其中的文件计数。发现候选目录后才定向展开，不对整个仓库读取文件正文。Git 不可用、可疑所有权、安全目录拒绝访问时只报告，不修改全局 `safe.directory` 绕过检查。

检查结论按证据保存：

| 证据 | 决策 |
|---|---|
| 修改、暂存、冲突、未跟踪或忽略文件 | 存在本地状态；忽略项可能是 `.env`、训练结果、数据库或手工资源，需要逐项区分 |
| stash、本地分支/标签、detached HEAD | HEAD 同步不能覆盖这些状态；stash 通常没有被普通 push 备份 |
| worktree、子模块、外部 Git common dir | 私有工作树状态和共享元数据要分别核对；不递归删除 `.git` 或共享仓库目录 |
| 本地 remote-tracking refs、ahead/behind、`rev-list` 结果 | 仅是缓存对照；0 个本地独有提交不证明远端现在可达或仍有这些对象 |
| 无 remote、无提交、命令失败、无法解释的引用 | 结论为 unknown，保留数据并提出下一步检查 |

需要声称“远端已覆盖”时，先说明联网和更新 remote-tracking refs 的影响，再在已获授权的范围内核验实际 remote。核对所有相关分支、标签和 detached HEAD，记录访问时间与失败；不自动推送、不清理引用，也不输出带凭据的 remote URL。即使远端核验成功，Git 配置、hooks、reflog、LFS 对象、子模块和工作树外部数据仍需独立备份证据，不能宣称整个文件夹可从远端完整恢复。

只清理构建目录时，确认具体产物的生成命令、依赖清单/锁文件、可取得的依赖与重建成本；`.gitignore`、`node_modules`、`target`、`dist` 等名字只是线索。保留本地修改的依赖、离线包、唯一生成物和无法重建的产物。禁止把 `git clean`、重置工作区或删除仓库当成缓存清理的替代动作。

## 服务、数据库、模型与虚拟磁盘

| 候选对象 | 先取得的证据 | 默认结论 |
|---|---|---|
| PostgreSQL、搜索服务、容器 volume 等持久数据 | 所有者、实际配置指向、服务/任务/容器状态、依赖、最近活动、可恢复备份 | `application-state`；服务当前停止不代表弃用 |
| Hyper-V、WSL、Docker、其他 VM 的 VHDX/镜像 | 所属实例、挂载/运行状态、快照或差分盘依赖、备份和应用内导出路径 | `backup/VM`；不按镜像文件名或时间猜测用途 |
| Hugging Face、Ollama 等模型目录 | 使用者、模型版本、下载来源是否仍可访问、本地微调/适配器/训练输出、离线需求 | 未核实前为 `unknown`；模型既可能是可重下权重，也可能是唯一产物 |

只提取确认归属所需的配置路径和状态字段，避免显示连接字符串或密钥。大体积、旧时间戳和“当前没运行”均不能单独证明无用；没有已运行的服务，也要考虑定时启动和按需加载。

这些对象先保留在盘点报告中。确实需要处理时，逐项说明影响，使用所属应用的备份/导出、卸载或存储管理流程，并验证恢复路径。范围包含唯一数据且用途不明时先问清；不能只给一个“严重风险”标签就把它加入批量清理。占用或权限失败时保留该项，不强制结束进程、停止服务或换删除工具重试。

## 来源

行为参考：[std-microblock/windows-disk-cleaner-skill](https://github.com/std-microblock/windows-disk-cleaner-skill/tree/ea986d425d50a7aacfc6ea6a3bdb0248ac045095)，2026-09-29 复核。吸收 Git 本地独有状态核查和持久数据用途确认，使用本项目的宿主工具、确认和恢复流程；未复制其实现。
