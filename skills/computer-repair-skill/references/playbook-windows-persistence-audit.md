---
name: windows-persistence-audit
description: Audit Windows startup, services, scheduled tasks, shell integrations, file associations, and extensions before removal
platform: windows
last_reviewed: 2026-09-09
author: computer-repair-skill-maintainers
source: local
---

# Windows Persistence Audit

## When to activate
Use for pop-ups, unknown background activity, slow boot, unexplained context-menu items, browser add-ons, file-association hijacks, or a request to remove residual software.

## Quick check
Record Windows build, current user, complaint time, and whether the device is managed by MDM, Group Policy, security software or an enterprise account. Start read-only and preserve a report outside the suspected application directory.

Read [cleanup-protocol.md](cleanup-protocol.md) and [rule-source-contract.md](rule-source-contract.md) before classifying a vendor or proposing removal. A name or path substring is not sufficient identity evidence.

## Standard diagnostic path

### 1. Enumerate persistence locations
Collect structured results from:

- `Win32_StartupCommand` and HKCU/HKLM `Run` keys;
- `Win32_Service` including state, start mode, account and executable path;
- `Get-ScheduledTask` including task path, triggers and actions;
- Explorer/context-menu and file-association registry entries;
- browser extension manifests and managed policy entries.

For suspicious executables record the literal path, publisher, Authenticode status and SHA-256 with `win_file_hash`. Do not execute a file merely to identify it.

Cover both the classic registrations and the newer ones: `shell` verbs, `ContextMenuHandlers`, drag-and-drop handlers, `CommandStore`, `ShellNew`/`SendTo`/`OpenWith`, the per-scope file/folder/drive/desktop entries, and Windows 11 package-declared context menus. When one location denies access or disappears, log the gap and keep enumerating — a single protected key must not abort the whole audit.

### 2. Tier the findings before naming anything
Split inventory from risk. A normal, fully present third-party integration (archiver, diff tool, editor) belongs in the inventory view for show/hide and provenance only; it is not a finding. Report-only tiers: an entry whose component path could not be resolved is `unknown`, not "missing file" — claim residue only when the path is known and that path really does not exist. Core shell verbs and Windows' own commands are report-only in every case, because deleting them breaks the context menu as a whole.

Behavior labels such as pop-up, ad or watchdog describe symptoms and are not vendor identity; they raise review priority but never substitute for identity evidence or appear as a vendor name.

### 3. Evaluate evidence
Use install date, publisher, signature, parent application, path ownership and observed behavior. “Unknown” is not the same as “malware”. Keep original registry values, task XML or service configuration as evidence. If malware is suspected, activate `endpoint-security-check` and preserve evidence before removal.

Require at least two independent identity signals. Mark weak, unknown or conflicting matches as report-only; do not bulk-select them. Show the user the human-visible entry, technical location, evidence summary, impact and proposed action.

### 4. Plan a single-item change
Default application associations, signed enterprise extensions and security software are review-only. For an unwanted application, prefer its verified uninstaller. If disabling a user-owned startup item or task is appropriate, export the exact registry key/task XML or record the original service start mode first. Do not batch-delete by vendor name, wildcard or pattern.

Keep the action at the level of the entry: remove one startup entry, disable one service, disable one task, disable one shell extension. Sharing a vendor with an unwanted component is not a reason to escalate to uninstalling the product. When there is process evidence but no persistence entry, report it — do not force-kill, because a watchdog will restart it and the target may be the application the user is using.

The plan must contain fixed finding IDs, exact targets, backup location, required elevation, rollback and post-change re-scan. Launching an uninstaller only opens the vendor UI; the user must confirm there, and the Agent must not silently pass uninstall arguments. Before opening it, re-read the same uninstall registry entry and confirm the display name, publisher and uninstall command all still match the scan; if any of the three changed, refuse and re-scan.

### 5. Apply and re-scan
After explicit approval, change only the listed item. Do not alter UAC, certificate trust, Defender, SmartScreen, Windows Update or protected services. Never use PsExec to bypass access checks. Run the audit with normal privileges and elevate only the individual approved action that needs HKLM, a service, a system task or an all-users entry; after elevation, re-verify and re-confirm rather than replaying the earlier selection automatically.

Re-check the item against the preview immediately before the change. Back up first, verify the backup is readable, apply one action, then verify the new state. Keep failed or recreated entries in the report and preserve a restore batch.

## Verification
Re-enumerate the same location, verify the backup/export is readable, and repeat the original boot, context-menu or browser workflow. Check that no dependent service, file association or enterprise policy regressed.

## Caveats
- MDM/Group Policy can recreate an entry; report the policy source instead of fighting it locally.
- A signed binary can still be unwanted, and an unsigned binary is not proof of malware.
- Registry backup is the gate, not a formality: if the export cannot be written and read back, cancel that item rather than deleting first and hoping to reconstruct it.
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
