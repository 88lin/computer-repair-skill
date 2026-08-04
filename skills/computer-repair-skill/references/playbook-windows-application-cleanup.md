---
name: windows-application-cleanup
description: Audit and clean regenerable Windows app caches or duplicates while preserving profiles, chat data, and credentials
platform: windows
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Application Cleanup

## When to activate
Use for a named application's cache growth, WeChat received-file duplication, browser cache growth, package caches, or a request to reclaim application storage safely.

## Quick check
Identify the application, version, profile/account, exact data root, current processes, synchronization state, and backup status. Use `win_app_data_ls` and `win_process_list`; do not assume a path from a README or another machine.

Before proposing any deletion, read [cleanup-protocol.md](cleanup-protocol.md) and, for a Winapp2-style or community rule file, [rule-source-contract.md](rule-source-contract.md). Treat the rule as data to review, not as execution authorization.

## Standard diagnostic path

### 1. Establish the data boundary
Separate `cache`, `logs`, `thumbnails`, `shader/download cache` and other regenerable scopes from profile databases, chat history, favorites, cookies, credentials, account keys and user-created media. For WeChat, keep chat databases, favorites, Moments data, `CustomEmotion` and any unverified account directory out of automatic cleanup.

If the application is not running, still check for helper processes and background sync. Never force-kill a process as an implicit cleanup step.

### 2. Detect duplicate files conservatively
When the request is duplicate cleanup, group candidates by size, then compare a bounded prefix hash, then a full SHA-256 hash with `win_file_hash`. Only equal size and full hash make a duplicate candidate. Show every path, timestamp, owner and hash; never choose “shortest path” or “oldest file” as an irreversible rule without user approval.

### 3. Use explicit scopes
Prefer the owning application's documented cleanup or a reviewed, version-specific scope. Do not recursively match `*.tmp`, `*.cache`, `node_modules`, or an entire application root. A scope must state its positive targets and redlines, and must be safe when a directory is absent or a junction is present.

For each reviewed rule, run a read-only preview first. Show the concrete files, registry values, exclusions, warnings, total bytes and locked/skipped items. If a rule cannot distinguish cache from profile state, keep it report-only.

### 4. Stage a reversible action
After the user approves the exact list, close the application through its normal UI or let the user do so. Move files to the Windows Recycle Bin or an isolated quarantine directory with `win_recycle_path`; do not use permanent deletion. Write an undo manifest containing original path, size, SHA-256, timestamp and destination. Use a backup first when the boundary touches account or chat data.

Re-check each path and hash immediately before moving it. Stop the item if it changed, escaped the approved root or the backup could not be read. Never turn this playbook into a silent scheduled delete; unattended runs may produce inventory or preview reports only.

## Verification
Re-scan the same scopes, compare byte counts and duplicate groups, and launch the application or its relevant workflow. Verify that the undo manifest and Recycle Bin/quarantine entries exist. Report skipped locked files instead of retrying with force.

## Caveats
- Browser `Login Data`, `Cookies`, `Web Data`, profile preferences and extension stores are not caches.
- Package-manager caches should be cleaned through the package manager when available.
- Recycle Bin recovery is not a backup; retain a verified backup for chat, mail and synchronized data.
- Unknown application directories remain in `windows-storage-inventory` until the owner and redlines are known.

## Escalation
Escalate when the app has no documented data boundary, the target is synchronized or encrypted, hashes change during scanning, or a cleanup would require administrator access to a protected system directory.

## Tools referenced
- `win_app_data_ls`
- `win_process_list`
- `win_file_hash`
- `win_recycle_path`
- `win_clear_app_cache`
- `ui_spa`
