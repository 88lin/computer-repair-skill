---
name: health-baseline-check
description: Comprehensive device health check — disk, memory, uptime, updates, firewall, backup, and network
platform: all
last_reviewed: 2026-07-28
author: upstream-maintainers
source: bundled
emoji: 🩺
---

# Health Baseline Check

Runs a comprehensive health check across the device and produces a baseline summary. Covers disk, memory, uptime, OS updates, firewall, backup status, and network connectivity. Useful for onboarding, periodic audits, or establishing a reference point before changes.

## When to activate
New device setup, periodic health audit, pre-migration baseline, user reports general slowness, or "just check everything is OK."

## Standard check path

> **Platform routing.** Every step below has a command for all three platforms.
> Detect the actual OS first (see SKILL.md "执行前检查") and run only that
> platform's branch. Never hand a macOS-only command to a Windows or Linux user.

### 1. Check disk space
Check overall disk stats with `win_disk_usage` / `mac_disk_usage` / `linux_disk_usage`.
- **Green**: <80% used.
- **Yellow**: 80-90% used. Mention the platform-matched cleanup playbook:
  `windows-disk-space-recovery` (Windows), `disk-space-recovery` (macOS),
  `linux-disk-space-recovery` (Linux).
- **Red**: >90% used. SSDs degrade above 90%. Flag for immediate cleanup.

### 2. Check memory usage
Check RAM usage using system memory info.
- Report total RAM, used, and available.
- **Windows**: `Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory`; commit charge via `Get-Counter '\Memory\% Committed Bytes In Use'`.
- **macOS**: `vm_stat` plus memory pressure — `memory_pressure -Q` if available.
- **Linux**: `free -h` and `cat /proc/pressure/memory` (PSI, kernel 4.20+).
- **Green**: >20% available.
- **Yellow**: 10-20% available. Check what's consuming memory.
- **Red**: <10% available or heavy swap usage. Identify top consumers.

### 3. Check system uptime
- **Windows**: `(Get-CimInstance Win32_OperatingSystem).LastBootUpTime` — there is no `uptime` command in PowerShell. Also check for fast startup masking a "restart": `powercfg /a`.
- **macOS / Linux**: `uptime`.
- **Green**: <14 days.
- **Yellow**: 14-30 days. Suggest a restart — many updates and fixes require a reboot.
- **Red**: >30 days. Strongly recommend a restart.

### 4. Check OS version and update status
Report the current OS version, then check for pending updates read-only.

- **Windows**:
  - Version: `Get-ComputerInfo | Select-Object OsName, OsVersion, OsBuildNumber`.
  - Last patches: `Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5`.
  - Pending updates (read-only search, no install):
    `(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0 AND IsHidden=0").Updates | Select-Object Title, IsMandatory`
- **macOS**: `sw_vers` for version, `softwareupdate --list` for pending updates.
- **Linux**:
  - Version: `cat /etc/os-release`, `uname -r`.
  - Debian/Ubuntu: `apt list --upgradable` (reflects the last metadata refresh — say so); Ubuntu security count: `/usr/lib/update-notifier/apt-check --human-readable`.
  - Fedora/RHEL: `dnf check-update` (exit code 100 means updates are available — not a failure).
  - Arch: `checkupdates` from `pacman-contrib`.

- **Green**: up to date.
- **Yellow**: non-security updates pending.
- **Red**: security updates pending.

### 5. Check firewall status
- **Windows**: `Get-NetFirewallProfile | Select-Object Name, Enabled` — all three profiles (Domain/Private/Public) should be `True`.
- **macOS**: `defaults read /Library/Preferences/com.apple.alf globalstate` — 1 or 2 means enabled, 0 means disabled.
- **Linux**: whichever front end is actually in use — `ufw status`, `firewall-cmd --state`, `nft list ruleset`, or `iptables -S` (most need root). Confirm which one is active first with `systemctl is-active ufw firewalld nftables`.
- **Green**: firewall enabled.
- **Red**: firewall disabled. Recommend enabling it.
- Report the finding; **do not disable a firewall** and do not silently enable one — enabling can break LAN printing, file shares, or remote access. Confirm with the user first.

### 6. Check backup status
- **Windows**: there is no single canonical backup mechanism — check several and report what exists:
  - Restore points: `Get-ComputerRestorePoint`.
  - File History service: `Get-Service -Name fhsvc`.
  - OneDrive folder backup: `$env:OneDrive` and `Get-Process OneDrive -ErrorAction SilentlyContinue`.
  - Image backup (admin, not present on all editions): `wbadmin get versions`.
- **macOS**: `tmutil status` and `tmutil latestbackup`.
- **Linux**: also no canonical mechanism — check `systemctl list-timers` for backup timers, `timeshift --list` (root), and scheduled jobs via `crontab -l` and `ls /etc/cron.*`.
- Report when the last backup completed.
- **Green**: backup within the last 24 hours.
- **Yellow**: backup is 1-7 days old.
- **Red**: no backup configured, or last backup is older than 7 days.

### 7. Check network connectivity
Run the quick connectivity checks from the platform-matched networking playbook —
`windows-network-diagnostics` (Windows), `network-diagnostics` (macOS), or
`linux-network-diagnostics` (Linux):
- Ping `8.8.8.8` — basic internet.
- DNS check for `google.com` — DNS working.
- HTTP check for `https://www.google.com` — full connectivity.
- **Green**: all pass.
- **Yellow**: partial (e.g., ping works but DNS fails).
- **Red**: no connectivity.

### 8. Summarize health baseline
Present a summary with a status for each category:

| Check | Status | Detail |
|-------|--------|--------|
| Disk | Green/Yellow/Red | X% used, Y GB free |
| Memory | Green/Yellow/Red | X GB available of Y GB |
| Uptime | Green/Yellow/Red | X days |
| OS Updates | Green/Yellow/Red | Up to date / N updates pending |
| Firewall | Green/Red | Enabled / Disabled |
| Backup | Green/Yellow/Red | Last backup: date |
| Network | Green/Yellow/Red | All checks pass / Issues |

Give an overall assessment: healthy, needs attention, or needs immediate action. List specific recommendations in priority order.

## Caveats
- This is a point-in-time snapshot. Conditions change — memory usage fluctuates, network can be intermittent.
- **"Purgeable" disk space** on macOS is technically available. Don't flag disk as critical if most of the used space is purgeable.
- **High memory usage isn't always bad.** macOS aggressively caches files in RAM. "Memory pressure" is a better indicator than raw usage. Check for swap usage as the real signal.
- **No Time Machine** isn't necessarily a problem if the user uses another backup solution (Backblaze, CrashPlan, iCloud). Ask before flagging. The same applies to Windows and Linux, where there is no single expected backup tool at all.
- **Windows update search needs the Windows Update service running.** If `wuauserv` is stopped or a WSUS/MDM policy redirects it, the read-only search returns nothing — that is not the same as "up to date". Check `Get-Service wuauserv` before concluding.
- **`apt list --upgradable` reads cached metadata.** Without a recent `apt update` (which needs root and network) the list can be stale. Report the cache age instead of implying a live check.
- **Uptime on Windows is not reboot count.** Fast startup and hibernate can keep `LastBootUpTime` old even though the user "shut down" daily; a Shift-restart or `shutdown /r /t 0` is the real reboot.

> The full baseline covers ~90% of common device health issues. Most frequent finding: pending OS updates and stale backups.

## Key signals
- **"My computer feels slow"** → focus on steps 2 (memory) and 3 (uptime). A reboot often helps.
- **"Just got a new laptop"** → run all steps to establish a clean baseline.
- **"Preparing for a big project"** → ensure disk space is healthy and backups are current.
- **"Something feels off"** → run all steps — the summary table makes issues obvious.

## Escalation
If multiple categories are red:
- Prioritize disk space (>90%) and missing backups — these risk data loss.
- If OS updates have been pending for weeks, check for MDM or policy blocks preventing updates.
- If the device is consistently unhealthy, it may need a fresh OS install or hardware evaluation.

## Tools referenced
- `win_disk_usage` / `mac_disk_usage` / `linux_disk_usage` — disk space stats
- `win_system_info` / `mac_system_info` / `linux_system_info` — OS version, RAM, uptime
- `shell_run` — uptime, firewall state, update search, backup state (read-only)
- `win_service_list` — Windows Update and File History service state
- `win_dns_check` / `mac_dns_check` / `linux_dns_check` — DNS connectivity
- `win_http_check` / `mac_http_check` / `linux_http_check` — HTTP connectivity
- `win_ping` / `mac_ping` / `linux_ping` — basic network check
- `ui_done` — final baseline summary after all checks complete
