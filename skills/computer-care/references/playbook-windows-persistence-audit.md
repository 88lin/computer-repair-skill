---
name: windows-persistence-audit
description: Audit Windows startup, services, scheduled tasks, shell integrations, file associations, and extensions before removal
platform: windows
last_reviewed: 2026-07-28
author: computer-care-maintainers
source: local
---

# Windows Persistence Audit

## When to activate
Use for pop-ups, unknown background activity, slow boot, unexplained context-menu items, browser add-ons, file-association hijacks, or a request to remove residual software.

## Quick check
Record Windows build, current user, complaint time, and whether the device is managed by MDM, Group Policy, security software or an enterprise account. Start read-only and preserve a report outside the suspected application directory.

## Standard diagnostic path

### 1. Enumerate persistence locations
Collect structured results from:

- `Win32_StartupCommand` and HKCU/HKLM `Run` keys;
- `Win32_Service` including state, start mode, account and executable path;
- `Get-ScheduledTask` including task path, triggers and actions;
- Explorer/context-menu and file-association registry entries;
- browser extension manifests and managed policy entries.

For suspicious executables record the literal path, publisher, Authenticode status and SHA-256 with `win_file_hash`. Do not execute a file merely to identify it.

### 2. Evaluate evidence
Use install date, publisher, signature, parent application, path ownership and observed behavior. “Unknown” is not the same as “malware”. Keep original registry values, task XML or service configuration as evidence. If malware is suspected, activate `endpoint-security-check` and preserve evidence before removal.

### 3. Plan a single-item change
Default application associations, signed enterprise extensions and security software are review-only. For an unwanted application, prefer its verified uninstaller. If disabling a user-owned startup item or task is appropriate, export the exact registry key/task XML or record the original service start mode first. Do not batch-delete by vendor name, wildcard or pattern.

### 4. Apply and re-scan
After explicit approval, change only the listed item. Do not alter UAC, certificate trust, Defender, SmartScreen, Windows Update or protected services. Never use PsExec to bypass access checks.

## Verification
Re-enumerate the same location, verify the backup/export is readable, and repeat the original boot, context-menu or browser workflow. Check that no dependent service, file association or enterprise policy regressed.

## Caveats
- MDM/Group Policy can recreate an entry; report the policy source instead of fighting it locally.
- A signed binary can still be unwanted, and an unsigned binary is not proof of malware.
- Keep browser profile databases, credentials and extension evidence intact until the incident owner approves cleanup.

## Escalation
Escalate protected services, system-wide certificate/UAC changes, unsigned binaries in system paths, repeated recreation, or a corporate device to IT/security. Do not implement a certificate allow/deny list as a substitute for Defender or incident response.

## Tools referenced
- `win_startup_programs`
- `win_service_list`
- `win_scheduled_task_list`
- `win_policy_list`
- `win_file_hash`
- `win_registry_snapshot`
- `ui_spa`
