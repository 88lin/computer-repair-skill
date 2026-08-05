---
name: windows-uninstall-residue-cleanup
description: Preview and clean Windows uninstall residue with strict identity matching, registry backup, and recovery
platform: windows
last_reviewed: 2026-08-05
author: computer-repair-skill-maintainers
source: local
---

# Windows Uninstall Residue Cleanup

## When to activate
Use after a Windows application uninstall when the user wants to inspect leftover files, registry keys, services, startup entries, or file associations, or when the vendor uninstaller is broken and a guarded force-removal review is needed.

## Quick check
Read [cleanup-protocol.md](cleanup-protocol.md) and [safety-policy.md](safety-policy.md). Identify the exact display name, publisher, package/registry ID, version, install location, executable or display icon, uninstall command, current processes, and whether the application is shared, synchronized, licensed, security-related, or managed by an organization.

## Standard diagnostic path

### 1. Run the vendor path first
Preview the exact uninstall command with `win_app_list` and `win_package_metadata`. Show the command, arguments, elevation, expected restart, data boundary, and rollback. After approval, use `win_package_uninstall` or the vendor uninstaller interactively; never append silent or force flags without a separate confirmation.

Wait for the uninstaller and verify the exact package/registry entry, install directory executables, services, startup items, scheduled tasks, and file associations. An exit code of zero alone is not proof of removal.

### 2. Build a strict residue preview
Scan only concrete, bounded roots: the application-specific children of `%APPDATA%`, `%LOCALAPPDATA%`, `%ProgramData%`, uninstall registry keys, publisher/application registry paths, and file-association keys. Use `win_path_inventory`, `win_app_data_ls`, and `win_registry_query`; do not scan or delete an entire profile or registry hive.

A candidate is high-confidence only when multiple signals agree: exact app name or folder name, publisher, install location, executable/display icon, uninstall metadata, and registry evidence. Label each item `high`, `medium`, or `unknown` and show path, item type, bytes, evidence, exclusions, and whether it is shared. Unknown, shared runtime, browser profile, credentials, chat database, cloud-sync, security, driver, and enterprise-management data stay report-only.

### 3. Guard force removal
Only when the user explicitly requests force removal and the vendor path is unavailable, preview the exact install-directory children. Refuse Windows/system directories, common parent roots, reparse points, shallow paths (fewer than three path components), and directories without app-name, executable, display-icon, or registry-path evidence. Export the relevant registry keys with `win_registry_snapshot` before any registry change.

Require per-item confirmation. Move files to the Recycle Bin with `win_recycle_path` by default; permanent deletion is a separate, explicit choice and needs a verified backup. Never delete a registry key or file-association entry merely because its name contains the app name.

### 4. Log and clean incrementally
Re-check every path and registry value immediately before the approved action. Stop an item if it changed, is locked, escaped the approved root, or no longer matches the evidence. Record action, result, bytes, backup/export path, recovery method, and failed items with `win_operation_log`.

## Verification
Re-enumerate the exact package, install location, persistence entries, file associations, and reviewed residue scopes. Confirm shared dependencies, security controls, unrelated applications, and user profiles remain intact. Report Recycle Bin/quarantine and registry backups, skipped locks, and any residue that remains report-only.

## Caveats
- Uninstallers may leave auto-updaters, services, scheduled tasks, shell extensions, or shared runtimes; route those to `windows-persistence-audit` and review separately.
- Do not remove Edge, Defender, WebView2, Office runtimes, GPU drivers, Store dependencies, or enterprise agents through this workflow.
- Recycle Bin recovery is not a backup. Preserve a tested backup for mail, chat, credentials, synchronized data, and licensed application state.

## Escalation
Escalate unsigned or unknown uninstallers, protected paths, active services/drivers, organization policy, ambiguous publisher identity, locked files, registry export failure, or a request for unattended/batch force removal.

## Tools referenced
- `win_app_list`
- `win_package_metadata`
- `win_package_uninstall`
- `win_process_list`
- `win_path_inventory`
- `win_app_data_ls`
- `win_registry_query`
- `win_registry_snapshot`
- `win_recycle_path`
- `win_operation_log`
- `ui_spa`
- `shell_run`
