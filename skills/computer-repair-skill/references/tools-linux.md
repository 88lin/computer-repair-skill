# Linux 工具映射

默认按 POSIX 环境处理，并在执行前识别发行版、init 系统、网络管理器和可用 Shell。占位符 `<HOST>`、`<DOMAIN>`、`<URL>`、`<PID>`、`<PATH>` 和 `<SERVICE>` 必须替换成已验证的字面值。

## 网络

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_network_info` | `ip address`、`ip route`、`resolvectl status` | 只读 |
| `linux_ping` | `ping -c <COUNT> <HOST>` | 只读 |
| `linux_dns_check` | `getent ahosts <DOMAIN>`；有 `dig` 时补充 `dig` | 只读 |
| `linux_http_check` | `curl --head --location --max-time 15` | 只读联网 |
| `linux_flush_dns` | 根据实际解析器使用 `resolvectl flush-caches` 或重启对应缓存服务 | 可逆变更，先确认 |

```bash
ip -brief address
ip route show
resolvectl status

getent ahosts '<DOMAIN>'

curl --head --location --silent --show-error \
  --max-time 15 --write-out '\nstatus=%{http_code} total=%{time_total}s final=%{url_effective}\n' \
  '<URL>'
```

`resolvectl` 不存在时先识别 `systemd-resolved`、NetworkManager、dnsmasq 或 nscd，避免重启无关服务。

## 性能与存储

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_system_info` | `/etc/os-release`、`uname`、`uptime`、`free` | 只读 |
| `linux_process_list` | `ps` 按 CPU 和内存排序 | 只读 |
| `linux_disk_usage` | `df -hT`、`df -i`，需要时对明确路径使用 `du` | 只读 |
| `linux_kill_process` | `kill <PID>`，必要时再升级信号 | 高影响，先确认 PID 和用途 |

```bash
cat /etc/os-release
uname -a
uptime
free -h

ps -eo pid,ppid,user,%cpu,%mem,rss,etime,comm --sort=-%cpu | head -n 20
ps -eo pid,ppid,user,%cpu,%mem,rss,etime,comm --sort=-rss | head -n 20

df -hT
df -i
```

容器、cgroup 和虚拟机环境中，主机可见内存与进程限制可能不同。读取 `/proc/self/cgroup` 和相关 cgroup 限制后再解释资源数据。

## 系统诊断

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_system_summary` | 组合发行版、内核、运行时间、内存、磁盘和网络摘要 | 只读 |
| `linux_read_file` | 先 `stat` 和 `file`，再限制行数读取文本 | 只读 |
| `linux_read_log` | 优先 `journalctl`，文本日志使用 `tail` 或 `sed` | 只读 |
| `shell_run` | 使用宿主终端执行当前 Linux 命令 | 按具体输入分类 |

```bash
stat --printf='type=%F size=%s modified=%y path=%n\n' '<PATH>'
file --brief '<PATH>'
sed -n '1,200p' '<PATH>'

journalctl --since '-2 hours' --priority=warning --no-pager
journalctl --unit '<SERVICE>' --since '-2 hours' --no-pager
```

日志查询先限定 unit、时间、priority、boot 或 PID。读取 `/var/log` 中的认证和安全日志时只提取故障所需字段。

## 常见状态变更

Linux Playbook 语义工具集较小，流程常通过 `shell_run` 完成动作。以下全部先展示计划并确认：

- 重启服务：先 `systemctl status '<SERVICE>'`，确认后运行 `sudo systemctl restart '<SERVICE>'`，再检查状态和日志。
- 刷新 DNS：先识别解析器，确认后调用其原生命令，再重新解析原域名。
- 终止进程：先记录 PID、父进程、命令、用户和资源占用，确认后先发送 TERM，等待并验证。
- 清理缓存：先用 `du` 测量和枚举具体可再生成目录，读取安全策略后处理字面目标。
- 安装软件：先识别发行版和包管理器，展示仓库来源、包名、版本、下载量和回滚方式。

## 管理员权限

- 先用普通权限完成诊断。
- 每次只提升已批准的单条命令，不开启长期 root Shell。
- 不采集或记录 sudo 密码；让终端或系统认证组件处理。
- 修改 `/etc`、`/usr`、`/var/lib`、启动项、服务单元、网络配置或安全策略前备份具体文件并记录原权限。
