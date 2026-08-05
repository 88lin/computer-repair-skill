---
name: endpoint-security-check
description: Quick security posture check — antivirus, firewall, updates, and suspicious activity
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🛡️
---

# Endpoint Security Check

Runs a quick security posture check on the device. Covers endpoint protection, firewall, OS updates, recently installed programs, and unusual network activity. Designed to run fast and flag anything that needs attention.

## When to activate
Routine security audit, post-incident triage, new device onboarding, or user reports suspicious behavior.

## Standard check path

### 1. Check endpoint protection
Check for running antivirus/endpoint protection processes:
- **macOS**: Look for `XProtect`, `XProtectRemediator*` (the per-family scanners under `/Library/Apple/System/Library/CoreServices/XProtect.app/Contents/MacOS/`), `com.apple.ManagedClient`, CrowdStrike (`falcond`), SentinelOne (`SentinelAgent`), Sophos (`SophosScanD`), or Jamf (`jamf`). Do **not** expect `MRT` — the Malware Removal Tool was superseded by XProtect Remediator in macOS 12.3 and is not installed on current systems, so its absence is normal.
- **Windows**: Check for `MsMpEng.exe` (Defender), `CsFalconService` (CrowdStrike), `SentinelAgent.exe`, or other known AV processes.
- **Linux**: Check for `clamd` (ClamAV), `falcond`, or `SentinelAgent`.

If no endpoint protection is found, flag as a finding. macOS XProtect should always be present — if it's missing, something is wrong.

### 2. Check firewall status
- **macOS**: Use the application firewall CLI. The old `com.apple.alf` plist is gone in macOS 15 and reading it there returns an error, so do not depend on it:
  ```bash
  /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
  ```
  If you cannot get `sudo`, read it without elevation via `system_profiler SPFirewallDataType`.
- **Windows**: Check Windows Firewall status.
- **Linux**: Check `ufw status` or `iptables -L`.

Flag if firewall is disabled.

### 3. Check OS update status
- **macOS**: Run `softwareupdate --list` to check for pending updates.
- **Windows**: Check Windows Update status.
- **Linux**: Check for available package updates.

Flag if security updates are pending. Critical updates pending for more than 7 days are a higher concern.

### 4. Check recently installed programs
Look at programs installed in the last 30 days:
- **macOS**: Check `/Applications/` modification dates and `installer` history via `pkgutil --pkgs` or system_profiler `SPInstallHistoryDataType`.
- **Windows**: Check Programs and Features install dates.
- **Linux**: Check package manager logs.

Flag anything unfamiliar or recently installed that the user doesn't recognize.

### 5. Check for unusual network connections
List active network connections and flag suspicious activity:
- Look for connections to unusual ports (not 80, 443, 53, 993, 587).
- Look for connections to IP addresses (no hostname) on high ports.
- Check for processes with many outbound connections.
- **macOS/Linux**: Use `netstat` or `lsof -i`.
- **Windows**: Use `netstat -b`.

Don't alarm the user — many legitimate apps use unusual ports. Flag for review, not as confirmed threats.

### 6. Report findings
Summarize results in a clear report:
- **Green**: endpoint protection active, firewall on, OS up to date, no suspicious findings.
- **Yellow**: minor issues (non-critical updates pending, unfamiliar but likely safe programs).
- **Red**: no endpoint protection, firewall off, critical updates missing, suspicious network activity.

Present findings with recommended actions for any yellow or red items.

## Caveats
- macOS XProtect runs silently — no visible app. Its presence is normal and expected.
- Some corporate endpoint protection tools may not appear in standard process lists. Check with `launchctl list` on macOS for LaunchDaemons.
- Unusual network connections are not necessarily malicious. Many dev tools, sync services, and VPNs produce unusual-looking traffic.

> Steps 1-6 resolve ~80% of endpoint security concerns. Most common finding: pending OS updates.

## Key signals
- **"My computer is slow and showing pop-ups"** → likely adware or unwanted software. Focus on steps 4 and 5.
- **"IT said we need antivirus"** → check step 1 first — macOS XProtect counts but corporate may require a third-party tool.
- **"I clicked a suspicious link"** → prioritize step 5 (network connections) and step 4 (recent installs).

## Escalation
If suspicious network connections or unrecognized processes are found:
- Do not attempt removal — document findings and recommend the user contact their IT security team.
- If endpoint protection is missing on a corporate device, escalate to IT for MDM enrollment.
- Persistent red findings after remediation suggest a deeper compromise — recommend professional incident response.

## Tools referenced
- Shell commands — check firewall, list processes, network connections
- Process listing tools — find running AV/endpoint protection processes
