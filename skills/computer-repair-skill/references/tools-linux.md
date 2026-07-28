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

## 硬件、存储健康与温度

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_hardware_inventory` | `lscpu`、`lsblk`、`lspci`、`lsusb`、`/sys/class/dmi/id/*` | 只读 |
| `linux_storage_health` | `smartctl -H -A '<DEVICE>'`、`nvme smart-log '<DEVICE>'`、`/sys/block/<DEV>/queue/rotational` | 只读，通常需要 root |
| `linux_memory_report` | `/proc/meminfo`、`dmidecode -t memory`、`journalctl -k` 里的 EDAC/MCE 记录、`ras-mc-ctl --summary` | 只读，部分命令需要 root |
| `linux_thermal_status` | `sensors`、`/sys/class/thermal/thermal_zone*/{type,temp}`、`upower -i`、`/sys/class/power_supply/BAT*/` | 只读 |

```bash
lscpu
lsblk -o NAME,TRAN,ROTA,SIZE,MODEL,SERIAL,MOUNTPOINTS
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name /sys/class/dmi/id/bios_version

sudo smartctl -H -A '<DEVICE>'
sudo nvme smart-log '<DEVICE>'

for zone in /sys/class/thermal/thermal_zone*; do
  printf '%s type=%s milli_c=%s\n' "$zone" "$(cat "$zone/type")" "$(cat "$zone/temp")"
done

upower -i "$(upower -e | grep -m1 BAT)"
```

`smartctl -t short`、`smartctl -t long` 和 `nvme format` 会改变设备状态，不属于本别名；健康检查只读取已有计数器。USB 桥接盒经常不透传 SMART，必要时补 `-d sat` 并说明结果可能缺失。`/sys/class/thermal` 的温度单位是千分之一摄氏度。

## 启动与崩溃证据

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_boot_status` | `systemd-analyze blame`、`systemctl --failed`、`journalctl --list-boots`、`bootctl status`、`efibootmgr -v`、`mokutil --sb-state` | 只读，部分命令需要 root |
| `linux_crash_report_list` | `coredumpctl list`、`/var/crash` 元数据、`journalctl -k -b -1 -p err` | 只读 |

```bash
journalctl --list-boots
journalctl -b -1 -p err --no-pager
systemctl --failed
systemd-analyze blame | head -n 20

ls -l /sys/firmware/efi >/dev/null 2>&1 && echo 'firmware=UEFI' || echo 'firmware=BIOS/CSM'
coredumpctl list --no-pager | tail -n 20
```

`bootctl install`、`grub-install`、`update-grub`、`grub2-mkconfig` 和 `update-initramfs -u` 都会改写启动链，不属于只读分诊。文件系统检查只用只读模式（`fsck -n`、`xfs_repair -n`、`btrfs check --readonly`），`btrfs check --repair` 有数据损坏风险。

## 持久化与软件清单

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_startup_items` | `systemctl list-unit-files --state=enabled`、`systemctl --user list-unit-files --state=enabled`、`/etc/xdg/autostart`、`~/.config/autostart`、Shell 启动文件 | 只读 |
| `linux_service_list` | `systemctl list-units --type=service --all`；非 systemd 用 `service --status-all` 或 `rc-status` | 只读 |
| `linux_scheduled_task_list` | `systemctl list-timers --all`、`crontab -l`、`/etc/crontab`、`/etc/cron.*`、`at -l` | 只读 |
| `linux_package_inventory` | `dpkg-query -W -f`、`rpm -qa`、`pacman -Q`；归属查询用 `dpkg -S`、`rpm -qf`、`pacman -Qo` | 只读 |
| `linux_file_hash` | `sha256sum '<PATH>'` | 只读 |

```bash
systemctl list-unit-files --state=enabled --no-pager
systemctl list-timers --all --no-pager
systemd-delta --type=overridden

dpkg -S '<PATH>' 2>/dev/null || rpm -qf '<PATH>' 2>/dev/null || pacman -Qo '<PATH>' 2>/dev/null
sha256sum '<PATH>'
```

`systemd-delta` 能暴露被本地单元覆盖的发行版单元，是排查"改了配置却没生效"的首选证据。包完整性核对用 `rpm -Va`、`debsums -c` 或 `pacman -Qkk`；这些命令只读，但输出量大，先限定到可疑路径。

## 显示与蓝牙外设

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `linux_display_info` | `xrandr --listmonitors`（X11）、`wayland-info` 或 `swaymsg -t get_outputs`（Wayland）、`/sys/class/drm/*/status`、`lspci -k` 的 VGA 段 | 只读 |
| `linux_bluetooth_status` | `bluetoothctl show`、`bluetoothctl devices`、`rfkill list`、`systemctl status bluetooth` | 只读 |

```bash
echo "session=${XDG_SESSION_TYPE:-unknown}"
for port in /sys/class/drm/card*-*; do
  printf '%s %s\n' "${port##*/}" "$(cat "$port/status" 2>/dev/null)"
done
lspci -k | grep -A 3 -iE 'vga|3d|display'

rfkill list
bluetoothctl show
```

Wayland 会话里 `xrandr` 只能看到 XWayland 的视图，不能代表真实输出状态；先读 `XDG_SESSION_TYPE` 再选工具。`bluetoothctl power off`、`connect`、`remove` 都会改变配对与连接状态，需要单独确认。

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
