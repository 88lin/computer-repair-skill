#!/usr/bin/env bash
# 只读采集一台 Linux / macOS 机器的健康证据，输出结构化 JSON 或 Markdown。
#
# 安全边界（与 skills/computer-repair-skill/references/safety-policy.md 一致）：
#   * 只执行查询类命令：不安装、不删除、不重启服务、不改配置、不写注册表或系统目录。
#   * 不发起任何网络请求；需要联网刷新元数据的检查会被显式标记为 skipped。
#   * 输出前逐行过滤，凡含 password / token / secret 等关键字的行整行替换为占位符。
#   * 除 --output 指定的文件外不写入任何路径。
#
# 这个脚本是可选的辅助工具。Skill 的核心仍然是 Markdown Playbook：
# 采集到的证据只是给 Agent 和维修工程师看的输入，任何变更动作仍由 Playbook 驱动。
set -uo pipefail

collector_name="collect-health.sh"
schema=1

format="json"
output=""
selected_sections=""
probe_timeout=20
include_identity=1
list_only=0

usage() {
  cat <<'EOF'
用法: ./scripts/collect-health.sh [选项]

选项:
      --format <json|markdown>  输出格式，默认 json
      --output <path>           写入指定文件；缺省写标准输出
      --sections <a,b,c>        只采集指定小节，逗号分隔；缺省采集全部
      --list-sections           列出可用小节后退出
      --timeout <秒>            单条命令超时，默认 20（需要 timeout/gtimeout）
      --no-identity             报告头部不记录主机名与用户名
                                （注意：uname -a 等探针的原始输出里仍可能出现主机名）
  -h, --help                    显示帮助

示例:
  ./scripts/collect-health.sh --format markdown
  ./scripts/collect-health.sh --sections overview,storage,network --output health.json
EOF
}

fail() {
  printf '错误：%s\n' "$1" >&2
  exit 1
}

while (($# > 0)); do
  case "$1" in
    --format)
      (($# >= 2)) || fail "--format 缺少参数。"
      format="$2"
      shift 2
      ;;
    --output)
      (($# >= 2)) || fail "--output 缺少参数。"
      output="$2"
      shift 2
      ;;
    --sections)
      (($# >= 2)) || fail "--sections 缺少参数。"
      selected_sections="$2"
      shift 2
      ;;
    --timeout)
      (($# >= 2)) || fail "--timeout 缺少参数。"
      probe_timeout="$2"
      shift 2
      ;;
    --no-identity)
      include_identity=0
      shift
      ;;
    --list-sections)
      list_only=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      fail "未知参数：$1。用 --help 查看用法。"
      ;;
  esac
done

case "$format" in
  json | markdown) ;;
  *) fail "不支持的 --format：${format}（可选 json 或 markdown）" ;;
esac

case "$probe_timeout" in
  '' | *[!0-9]*) fail "--timeout 必须是正整数秒数。" ;;
  *) ((probe_timeout > 0)) || fail "--timeout 必须大于 0。" ;;
esac

# 小节定义：id|标题
section_catalog="overview|系统与启动概览
hardware|硬件与固件
storage|存储与文件系统
memory|内存与交换
process|进程占用排行
network|网络配置与监听
services|服务与计划任务
updates|系统更新状态（只读本地缓存）
security|安全基线开关
logs|近期错误日志与崩溃报告
power|电源、电池与温度"

section_ids() {
  printf '%s\n' "$section_catalog" | awk -F '|' '{ print $1 }'
}

section_title() {
  printf '%s\n' "$section_catalog" | awk -F '|' -v id="$1" '$1 == id { print $2 }'
}

if ((list_only == 1)); then
  printf '%s\n' "可用小节（--sections 用逗号连接多个 id）："
  printf '%s\n' "$section_catalog" | awk -F '|' '{ printf "  %-10s %s\n", $1, $2 }'
  exit 0
fi

if [[ -n "$selected_sections" ]]; then
  wanted="$(printf '%s' "$selected_sections" | tr ',' '\n' | awk 'NF')"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    if ! section_ids | grep -Fxq -- "$candidate"; then
      fail "未知小节：${candidate}。用 --list-sections 查看全部。"
    fi
  done <<EOF
$wanted
EOF
else
  wanted="$(section_ids)"
fi

# --- 平台与执行工具 ---------------------------------------------------------

uname_s="$(uname -s 2>/dev/null || printf 'unknown')"
case "$uname_s" in
  Linux) platform="linux" ;;
  Darwin) platform="macos" ;;
  *) fail "本脚本只覆盖 Linux 与 macOS；当前系统是 ${uname_s}。Windows 请改用 scripts/collect-health.ps1。" ;;
esac

timeout_bin=""
if command -v timeout >/dev/null 2>&1; then
  timeout_bin="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  timeout_bin="gtimeout"
fi

# --- 输出工具 ---------------------------------------------------------------

# 整行丢弃可能含凭据的输出。宁可少给一行证据，也不要把秘密写进报告。
redact() {
  awk '
    {
      lowered = tolower($0)
      if (lowered ~ /password|passwd|secret|token|api[_-]?key|apikey|access[_-]?key|bearer|credential|private key|psk/) {
        print "[已按只读采集策略移除可能含凭据的一行]"
      } else {
        print
      }
    }'
}

# 先用 tr 去掉控制字符（保留制表与换行），再交给 awk 做 JSON 转义。
json_escape() {
  tr -d '\000-\010\013\014\016-\037' | awk '
    BEGIN { ORS = "" }
    {
      line = $0
      gsub(/\\/, "\\\\", line)
      gsub(/"/, "\\\"", line)
      gsub(/\t/, "\\t", line)
      printf "%s%s", (NR > 1 ? "\\n" : ""), line
    }'
}

json_inline() {
  printf '%s' "$1" | json_escape
}

# 缓冲区里存的是真实换行，最后用 printf '%s' 原样输出。
# 不能用 printf '%b' + 字面 \n：那样探针输出里的反斜杠（例如 \\wsl$ 或 C:\Users）
# 会被二次解释，JSON 转义结果直接被破坏。
nl=$'\n'
buffer=""
append() {
  buffer="$buffer$1"
}

# --- 探针 -------------------------------------------------------------------

probe_index=0
probe_count=0
probe_failures=0
skipped_count=0

# probe <说明> <命令>：执行只读命令并记录退出码与输出。
probe() {
  probe_label="$1"
  probe_command="$2"

  if [[ -n "$timeout_bin" ]]; then
    probe_output="$("$timeout_bin" "$probe_timeout" sh -c "$probe_command" 2>&1)"
    probe_status=$?
  else
    probe_output="$(sh -c "$probe_command" 2>&1)"
    probe_status=$?
  fi

  probe_output="$(printf '%s\n' "$probe_output" | redact)"
  probe_count=$((probe_count + 1))
  ((probe_status == 0)) || probe_failures=$((probe_failures + 1))

  if [[ "$format" == "json" ]]; then
    if ((probe_index > 0)); then
      append $',\n'
    fi
    append $'      {\n'
    append "        \"label\": \"$(json_inline "$probe_label")\",$nl"
    append "        \"command\": \"$(json_inline "$probe_command")\",$nl"
    append "        \"exit_code\": $probe_status,$nl"
    append "        \"output\": \"$(printf '%s' "$probe_output" | json_escape)\"$nl"
    append '      }'
  else
    append "### $probe_label$nl$nl"
    append $'```text\n'
    append "\$ $probe_command$nl"
    append "$probe_output$nl"
    append $'```\n\n'
    append "退出码：$probe_status$nl$nl"
  fi
  probe_index=$((probe_index + 1))
}

# skip <说明> <原因>：记录一条被主动跳过的检查，说明为什么不做。
skip() {
  skipped_count=$((skipped_count + 1))
  probe_count=$((probe_count + 1))
  if [[ "$format" == "json" ]]; then
    if ((probe_index > 0)); then
      append $',\n'
    fi
    append $'      {\n'
    append "        \"label\": \"$(json_inline "$1")\",$nl"
    append $'        "command": null,\n'
    append $'        "exit_code": null,\n'
    append "        \"output\": \"$(json_inline "已跳过：$2")\"$nl"
    append '      }'
  else
    append "### $1$nl$nl"
    append "已跳过：$2$nl$nl"
  fi
  probe_index=$((probe_index + 1))
}

# 只有命令存在时才执行，否则记录为跳过，避免把 "command not found" 当成故障。
probe_if() {
  if command -v "$1" >/dev/null 2>&1; then
    probe "$2" "$3"
  else
    skip "$2" "本机没有 $1，无法采集这一项。"
  fi
}

collect_linux_section() {
  case "$1" in
    overview)
      probe "内核与架构" "uname -a"
      probe "发行版信息" "cat /etc/os-release"
      probe "运行时长与负载" "uptime"
      probe "当前时间与时区" "date -u; date"
      probe_if timedatectl "时间同步状态" "timedatectl status"
      ;;
    hardware)
      probe_if lscpu "CPU 概览" "lscpu"
      probe "CPU 型号" "grep -m 1 'model name' /proc/cpuinfo"
      probe "内存总量" "grep -E 'MemTotal|SwapTotal' /proc/meminfo"
      probe "主板与机型" "cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name /sys/class/dmi/id/bios_version"
      ;;
    storage)
      probe "文件系统占用" "df -hT"
      probe_if lsblk "块设备拓扑" "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT"
      probe "inode 占用" "df -i"
      probe_if findmnt "只读挂载检查" "findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS"
      ;;
    memory)
      probe "内存与交换用量" "free -m"
      probe_if swapon "交换设备" "swapon --show"
      probe "内存压力（PSI）" "cat /proc/pressure/memory"
      probe "OOM 记录" "grep -i -c 'out of memory' /var/log/syslog /var/log/messages 2>/dev/null || echo '无法读取系统日志（通常需要权限）'"
      ;;
    process)
      probe "CPU 占用前 15" "ps -eo pid,ppid,pcpu,pmem,etime,comm --sort=-pcpu | head -n 16"
      probe "内存占用前 15" "ps -eo pid,ppid,pcpu,pmem,rss,comm --sort=-pmem | head -n 16"
      probe "进程总数" "ps -e --no-headers | wc -l"
      ;;
    network)
      probe_if ip "接口地址" "ip -brief address"
      probe_if ip "路由表" "ip route"
      probe "DNS 配置" "cat /etc/resolv.conf"
      probe_if resolvectl "解析器状态" "resolvectl status | head -n 40"
      probe_if ss "监听端口" "ss -tuln"
      ;;
    services)
      probe_if systemctl "失败的单元" "systemctl --failed --no-pager --no-legend"
      probe_if systemctl "最近的计划任务" "systemctl list-timers --all --no-pager | head -n 15"
      probe "用户 crontab 是否存在" "crontab -l >/dev/null 2>&1 && echo '存在用户 crontab' || echo '没有用户 crontab 或无权读取'"
      ;;
    updates)
      if command -v apt >/dev/null 2>&1; then
        probe "可升级软件包（读本地 apt 缓存，不联网）" "apt list --upgradable 2>/dev/null | head -n 40"
        probe "apt 缓存最后更新时间" "ls -l --time-style=long-iso /var/lib/apt/periodic 2>/dev/null || stat -c '%y %n' /var/lib/apt/lists 2>/dev/null"
      elif command -v pacman >/dev/null 2>&1; then
        probe "可升级软件包（只查本地数据库）" "pacman -Qu | head -n 40"
      elif command -v dnf >/dev/null 2>&1; then
        probe "可升级软件包（--cacheonly，不联网）" "dnf --cacheonly check-update | head -n 40"
      else
        skip "系统更新状态" "未识别到 apt / pacman / dnf，且本脚本不会联网刷新元数据。"
      fi
      ;;
    security)
      probe_if systemctl "防火墙服务状态" "systemctl is-active ufw firewalld nftables 2>&1"
      probe_if nft "nftables 规则条数" "nft list ruleset 2>&1 | wc -l"
      probe "SELinux 状态" "command -v getenforce >/dev/null 2>&1 && getenforce || echo '本机没有 getenforce'"
      probe "已启用的 LSM" "cat /sys/kernel/security/lsm"
      probe "待重启标记" "test -e /var/run/reboot-required && echo '需要重启' || echo '无重启标记'"
      ;;
    logs)
      probe_if journalctl "本次启动的 error 级日志（末 30 行）" "journalctl -p 3 -b --no-pager 2>&1 | tail -n 30"
      probe_if journalctl "上次启动的 error 级日志（末 20 行）" "journalctl -p 3 -b -1 --no-pager 2>&1 | tail -n 20"
      probe "内核错误与告警" "dmesg --level=err,warn 2>&1 | tail -n 20"
      ;;
    power)
      probe "电池状态" "grep -H . /sys/class/power_supply/*/capacity /sys/class/power_supply/*/status 2>/dev/null || echo '未发现电池（可能是台式机）'"
      probe "CPU 温度" "grep -H . /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo '无法读取温度传感器'"
      probe_if sensors "传感器读数" "sensors 2>&1 | head -n 30"
      ;;
    *)
      skip "$1" "该小节在 Linux 上没有定义探针。"
      ;;
  esac
}

collect_macos_section() {
  case "$1" in
    overview)
      probe "系统版本" "sw_vers"
      probe "内核与架构" "uname -a"
      probe "运行时长与负载" "uptime"
      probe "上次启动时间" "sysctl -n kern.boottime"
      probe "当前时间与时区" "date -u; date; systemsetup -gettimezone 2>/dev/null || true"
      ;;
    hardware)
      probe "CPU 型号" "sysctl -n machdep.cpu.brand_string"
      probe "内存总量（字节）" "sysctl -n hw.memsize"
      probe "机型与序列信息" "system_profiler SPHardwareDataType 2>&1 | head -n 25"
      ;;
    storage)
      probe "文件系统占用" "df -h"
      probe "磁盘与分区" "diskutil list"
      probe "APFS 容器信息" "diskutil apfs list 2>&1 | head -n 40"
      ;;
    memory)
      probe "虚拟内存统计" "vm_stat"
      probe "交换用量" "sysctl -n vm.swapusage"
      probe "内存压力" "memory_pressure -Q 2>&1 | head -n 20"
      ;;
    process)
      probe "CPU 占用前 15" "ps -Ao pid,ppid,pcpu,pmem,etime,comm -r | head -n 16"
      probe "内存占用前 15" "ps -Ao pid,ppid,pcpu,pmem,rss,comm -m | head -n 16"
      probe "进程总数" "ps -A | wc -l"
      ;;
    network)
      probe "接口地址" "ifconfig -a"
      probe "路由表" "netstat -rn | head -n 25"
      probe "DNS 解析器配置" "scutil --dns | head -n 40"
      probe "网络硬件端口" "networksetup -listallhardwareports"
      probe "监听端口" "netstat -an -p tcp | head -n 30"
      ;;
    services)
      probe "当前用户的 launchd 任务" "launchctl list | head -n 30"
      probe "系统级 launchd 任务数" "launchctl print system 2>/dev/null | head -n 20 || echo '需要更高权限，已跳过详细输出'"
      ;;
    updates)
      skip "系统更新状态" "softwareupdate --list 必须联网，本脚本不发起网络请求；请在 Playbook 里由工程师确认后手动执行。"
      probe "最近一次成功检查更新的时间（读本地偏好）" "defaults read /Library/Preferences/com.apple.SoftwareUpdate LastFullSuccessfulDate 2>&1"
      ;;
    security)
      probe "系统完整性保护" "csrutil status"
      probe "Gatekeeper 状态" "spctl --status 2>&1"
      probe "FileVault 状态" "fdesetup isactive 2>&1"
      probe "应用防火墙状态" "/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>&1"
      ;;
    logs)
      probe "最近的崩溃报告" "ls -lt ~/Library/Logs/DiagnosticReports 2>/dev/null | head -n 15 || echo '没有用户级崩溃报告'"
      probe "系统级崩溃报告" "ls -lt /Library/Logs/DiagnosticReports 2>/dev/null | head -n 15 || echo '没有系统级崩溃报告或无权读取'"
      probe "近期内核消息" "syslog -k Level Nem 2>/dev/null | tail -n 20 || echo '无法读取内核消息'"
      ;;
    power)
      probe "电池与电源" "pmset -g batt"
      probe "阻止睡眠的断言" "pmset -g assertions 2>&1 | head -n 25"
      probe "电源与循环次数" "system_profiler SPPowerDataType 2>&1 | head -n 40"
      ;;
    *)
      skip "$1" "该小节在 macOS 上没有定义探针。"
      ;;
  esac
}

# --- 组装输出 ---------------------------------------------------------------

generated_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
host_name="$(hostname 2>/dev/null || printf 'unknown')"
user_name="$(id -un 2>/dev/null || printf 'unknown')"

if [[ "$format" == "json" ]]; then
  append $'{\n'
  append "  \"schema\": $schema,$nl"
  append "  \"collector\": \"$(json_inline "$collector_name")\",$nl"
  append "  \"generated_at\": \"$generated_at\",$nl"
  append "  \"platform\": \"$platform\",$nl"
  append $'  "read_only": true,\n'
  append $'  "network_access": false,\n'
  if ((include_identity == 1)); then
    append "  \"identity\": { \"hostname\": \"$(json_inline "$host_name")\", \"user\": \"$(json_inline "$user_name")\" },$nl"
  else
    append $'  "identity": null,\n'
  fi
  append $'  "sections": [\n'
else
  append "# 计算机健康证据采集（只读）$nl$nl"
  append "- 采集脚本：$collector_name$nl"
  append "- 采集时间（UTC）：$generated_at$nl"
  append "- 平台：$platform$nl"
  if ((include_identity == 1)); then
    append "- 主机：${host_name}（用户 ${user_name}）$nl"
  fi
  append "- 全部命令均为只读查询，未发起网络请求。$nl$nl"
fi

section_index=0
while IFS= read -r section_id; do
  [[ -n "$section_id" ]] || continue
  title="$(section_title "$section_id")"

  if [[ "$format" == "json" ]]; then
    if ((section_index > 0)); then
      append $',\n'
    fi
    append $'    {\n'
    append "      \"id\": \"$(json_inline "$section_id")\",$nl"
    append "      \"title\": \"$(json_inline "$title")\",$nl"
    append $'      "probes": [\n'
  else
    append "## ${title}（${section_id}）$nl$nl"
  fi

  probe_index=0
  if [[ "$platform" == "linux" ]]; then
    collect_linux_section "$section_id"
  else
    collect_macos_section "$section_id"
  fi

  if [[ "$format" == "json" ]]; then
    append $'\n      ]\n'
    append '    }'
  fi
  section_index=$((section_index + 1))
done <<EOF
$wanted
EOF

if [[ "$format" == "json" ]]; then
  append $'\n  ]\n'
  append $'}\n'
else
  append "---$nl$nl"
  append "共 $section_index 个小节、$probe_count 项检查，其中 $skipped_count 项主动跳过、$probe_failures 项命令返回非零。$nl"
fi

if [[ -n "$output" ]]; then
  output_tmp="$output.tmp.$$"
  printf '%s' "$buffer" >"$output_tmp" || fail "无法写入 $output_tmp"
  mv -- "$output_tmp" "$output" || fail "无法写入 $output"
  printf '已写入 %s（%s 个小节，%s 项检查，%s 项跳过，%s 项返回非零）\n' \
    "$output" "$section_index" "$probe_count" "$skipped_count" "$probe_failures" >&2
else
  printf '%s' "$buffer"
fi

exit 0
