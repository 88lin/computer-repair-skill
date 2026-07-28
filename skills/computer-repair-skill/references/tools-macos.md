# macOS 工具映射

默认使用 `/bin/zsh` 语义，但通过宿主终端直接传递参数时优先避免额外 Shell 层。占位符 `<HOST>`、`<DOMAIN>`、`<URL>`、`<PID>`、`<APP>`、`<PRINTER>` 和 `<PATH>` 必须替换成已验证的字面值。

## 网络与 Wi-Fi

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `mac_network_info` / `mac_check_network` | `networksetup`、`route`、`ifconfig`、`scutil --dns` | 只读 |
| `mac_ping` | `/sbin/ping -c <COUNT> <HOST>` | 只读 |
| `mac_dns_check` | `dig +time=3 +tries=1 <DOMAIN>`，缺少 `dig` 时用 `dscacheutil -q host -a name` | 只读 |
| `mac_http_check` | `curl --head --location --silent --show-error --max-time 15` | 只读联网 |
| `mac_flush_dns` | `sudo dscacheutil -flushcache` 后向 `mDNSResponder` 发送 HUP | 可逆变更，先确认 |
| `wifi_scan` | `system_profiler SPAirPortDataType`；旧系统可使用受支持的 Wi-Fi 诊断命令 | 只读，可能较慢 |

```bash
networksetup -listallhardwareports
route -n get default
scutil --dns
ifconfig

curl --head --location --silent --show-error \
  --max-time 15 --write-out '\nstatus=%{http_code} total=%{time_total}s final=%{url_effective}\n' \
  '<URL>'
```

刷新 DNS：

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

执行前说明短暂解析中断，并在执行后重新测试原域名。

## 打印机

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `mac_printer_list` | `lpstat -p -d` | 只读 |
| `mac_print_queue` | `lpstat -o` 或 `lpstat -o '<PRINTER>'` | 只读 |
| `mac_cancel_print_jobs` | `cancel <JOB_ID>`，逐项处理 | 高影响，先列出并确认 |
| `mac_restart_cups` | 使用受支持的 `launchctl kickstart` 重启 `org.cups.cupsd` | 会中断打印，先确认 |

```bash
lpstat -p -d
lpstat -o
```

只取消用户确认的作业 ID。重启 CUPS 后再次检查默认打印机和队列。

## 性能与存储

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `mac_system_info` | `sw_vers`、`sysctl`、`uptime` | 只读 |
| `mac_process_list` | `ps`，需要瞬时采样时补充 `top -l 1` | 只读 |
| `mac_disk_usage` | `df -h` | 只读 |
| `mac_performance_diagnose` | 组合 CPU、内存压力、交换、磁盘和高负载进程检查 | 只读 |
| `disk_audit` | 对明确卷或目录使用 `du`，逐级缩小 | 只读但可能较慢 |
| `mac_kill_process` | `kill <PID>`，必要时再考虑更强信号 | 高影响，先确认 PID 和用途 |
| `mac_clear_caches` | 先测量并枚举具体缓存，再清理明确条目 | 高影响，读取安全策略 |

```bash
sw_vers
sysctl -n machdep.cpu.brand_string
sysctl -n hw.memsize
uptime

ps -axo pid,ppid,user,%cpu,%mem,rss,etime,comm |
  sort -k4 -nr |
  head -n 20

memory_pressure
vm_stat
df -h
```

目录审计先从目标卷的一级目录开始，例如：

```bash
du -x -d 1 -h '<PATH>' 2>/dev/null | sort -h
```

`du` 可能耗时且触发隐私权限提示。先限定路径，设置超时，并说明未授权目录会影响总量。

## 应用与日志

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `mac_app_list` | 枚举 `/Applications`、`~/Applications`，需要时读取 bundle 元数据 | 只读 |
| `mac_app_logs` | `log show` 按进程、时间和级别筛选 | 只读，可能较慢 |
| `mac_app_support_ls` | 查看具体应用在 `~/Library/Application Support`、Containers、Logs 中的目录 | 只读 |
| `mac_clear_app_cache` | 关闭应用、检查具体 Cache/Logs 子目录后处理 | 高影响，读取安全策略 |
| `mac_move_file` | `mv` 或宿主文件移动工具，检查目标冲突 | 状态变更，先确认 |
| `crash_log_reader` | 读取 `~/Library/Logs/DiagnosticReports` 中匹配应用的最新报告 | 只读 |

```bash
find /Applications "$HOME/Applications" -maxdepth 2 -name '*.app' -print 2>/dev/null

log show --last 1h --style compact \
  --predicate 'process == "<APP>"' \
  --info --debug

find "$HOME/Library/Logs/DiagnosticReports" -type f \
  -name '<APP>*' -print 2>/dev/null
```

读取崩溃报告时优先提取时间、进程、异常类型、终止原因、崩溃线程和二进制映像，不需要把完整报告全部带入上下文。

## 系统诊断

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `mac_system_summary` | 组合 `sw_vers`、`hostname`、`uptime`、`sysctl`、`df` 和网络摘要 | 只读 |
| `mac_read_file` | 先 `stat`，再对允许的文本范围使用 `sed`、`head` 或宿主读取工具 | 只读 |
| `mac_read_log` | `log show`、`tail` 或应用专用日志查询 | 只读 |
| `shell_run` | 使用宿主终端执行当前 macOS 命令 | 按具体输入分类 |

```bash
stat -f 'type=%HT size=%z modified=%Sm path=%N' '<PATH>'
sed -n '1,200p' '<PATH>'
```

密钥链、Messages、Mail、Safari、照片库、云盘和其他隐私目录需要更窄的目标与明确理由。优先读取元数据，不读取秘密正文。

## 管理员权限

- 先用普通权限完成检查。
- 需要 `sudo` 时展示单条命令、原因、影响和回滚，再由宿主或用户触发系统认证。
- 不缓存或传递管理员密码。
- 终止系统进程、重启服务、修改网络或清理 `~/Library` 前读取安全策略。
