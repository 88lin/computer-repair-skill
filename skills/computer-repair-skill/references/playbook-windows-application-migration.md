---
name: windows-application-migration
description: Migrate a Windows application or selected data folder to another local NTFS volume with junction rollback
platform: windows
last_reviewed: 2026-08-05
author: computer-repair-skill-maintainers
source: local
---

# Windows Application Migration

## When to activate
Use when the user wants to move an installed application, a selected application-data directory, or a custom large folder to another local disk while preserving the original path.

## Quick check
Record the exact source and target paths, owner, volume, filesystem, reparse-point state, size, file count, backup status, and the application or service that owns the data. A path being large is not permission to move it.

Read [safety-policy.md](safety-policy.md). For cache-only requests also read [cleanup-protocol.md](cleanup-protocol.md). Do not migrate an entire profile, `AppData`, `Program Files`, `Windows`, or a drive root.

## Standard diagnostic path

### 1. Validate the source and risk class
Use literal paths with `win_path_metadata` and `win_path_inventory`; do not follow junctions or scan outside the approved root. Confirm the source is a real directory, not already a reparse point, and that the target path does not exist or is an explicitly empty staging directory.

Block migration of Windows, `System32`, `SysWOW64`, `WinSxS`, `WindowsApps`, the `C:\Users` root, `WPSystem`, Edge/Chrome/WebView2 installation directories, Office Click-to-Run, GPU driver directories, `.NET` runtime directories, security drivers, and system-managed components. Warn and require an explicit item-level confirmation for `ProgramData`, database directories, VMware/VirtualBox/Hyper-V data, development toolchains, WeChat/Tencent data, Steam libraries, security software, services, and folders with hard-coded paths.

Check `win_process_list` and `win_path_lock_check`. Ask the user to close the application normally; never force-kill a process as an implicit migration step. If lock evidence is unavailable, report the uncertainty and stop before cutover.

### 2. Check the target volume
Use `win_disk_usage` and `win_volume_inventory` to verify that both paths are on fixed local volumes, the target filesystem is NTFS, and the target has at least `1.2 × source_bytes + 100 MB` free. Do not use network shares, removable media, exFAT, FAT32, or a path that resolves through another junction.

Show the source size, target free bytes, estimated copy time if available, required elevation, restart impact, and the exact rollback path in `ui_spa`. Do not continue to a state change until the user confirms this single migration.

### 3. Copy to an isolated target and verify
Create a unique target directory on the approved volume. Use `win_copy_verify` with reparse-point exclusion and preservation of file data, timestamps, and directory structure. Record the copy result, file count, byte total, skipped/locked files, and exit code.

Compare source and target byte totals and file counts. For critical application data, sample or fully compare SHA-256 values with `win_file_hash`; a size-only match is not proof of integrity. If any source file changes during the copy, is skipped, or cannot be verified, keep the original untouched and report the incomplete target.

### 4. Cut over atomically
After a successful copy, rename the source directory to a unique sibling backup name on the same volume. Confirm the source path is now free, create an NTFS Junction at the original path pointing to the verified target with `win_junction_create`, then inspect the link with `win_junction_inspect`.

Never delete the sibling backup during the same unattended step. Retain it until the user confirms the application launches and the target remains readable. If link creation or verification fails, remove only the newly created link, restore the sibling backup to the original path, and preserve the target for inspection. Do not recursively delete an unknown target.

### 5. Record the migration
Write an atomic manifest with `win_json_atomic_write` containing a unique ID, application/folder name, original path, target path, source and target volume, byte total, verification method, timestamp, link type, backup path, status (`active`, `restored`, or `failed`), and warnings. Do not store passwords, tokens, cookies, or file contents.

For custom or large folders, reuse this engine rather than inventing a second move procedure. Link the record to `windows-migration-history-recovery` for later health checks and restoration.

## Verification
Re-check that the original path is a Junction whose target is the approved directory, the target byte total still matches the manifest, no source files are changing, and the application or folder workflow works. Report retained backup paths, skipped files, locked processes, and the exact restore command. A successful copy without a verified link and post-launch check is not a completed migration.

## Caveats
- Store, MSIX/UWP, browser installation directories, drivers, security software, self-healing services, and licensed applications may overwrite or reject a Junction; use the vendor-supported data-location setting instead.
- Junctions are local filesystem metadata, not a backup. Keep an independent backup for important data.
- Do not migrate a whole user profile or a complete `AppData` root. Choose a documented child directory and preserve credentials and databases unless the user explicitly includes them.
- Cancellation or power loss may leave a target and a sibling backup. Treat both as recoverable artifacts and reconcile them before another attempt.

## Escalation
Escalate filesystem errors, BitLocker or enterprise management restrictions, unknown ownership, active database writes, missing lock evidence, a target that is not local NTFS, or any request to bypass a blocked path.

## Tools referenced
- `win_path_metadata`
- `win_path_inventory`
- `win_process_list`
- `win_path_lock_check`
- `win_disk_usage`
- `win_volume_inventory`
- `win_copy_verify`
- `win_file_hash`
- `win_junction_create`
- `win_junction_inspect`
- `win_json_atomic_write`
- `ui_spa`
- `shell_run`
