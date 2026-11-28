---
name: windows-application-migration
description: Migrate a Windows application or selected data folder to another local NTFS volume with junction rollback
platform: windows
last_reviewed: 2026-11-29
author: computer-repair-skill-maintainers
source: local
---

# Windows Application Migration

## When to activate
Use when the user wants to move an installed application, a selected application-data directory, or a custom large folder to another local disk while preserving the original path.

### 相邻流程：存储与迁移集群

「C 盘满了」会同时命中下面六个流程。先确认用户的真实诉求，命中错了就改路由，不要在本流程里硬做别的流程的事：

- 只想知道空间被谁占了（只读盘点） → [windows-storage-inventory](playbook-windows-storage-inventory.md)
- 确认是缓存或重复文件 → [windows-application-cleanup](playbook-windows-application-cleanup.md)
- 要把应用或数据挪到别的盘 → [windows-application-migration](playbook-windows-application-migration.md) ← **本流程**
- 迁移后出现幽灵链接或要回滚 → [windows-migration-history-recovery](playbook-windows-migration-history-recovery.md)
- 只想安全释放系统盘，不动应用 → [windows-disk-space-recovery](playbook-windows-disk-space-recovery.md)
- 空间确实不够，要动分区（风险最高） → [windows-partition-resize-audit](playbook-windows-partition-resize-audit.md)

完整分流表见 [playbook-index.md](playbook-index.md)。

## Quick check
Record the exact source and target paths, owner, volume, filesystem, reparse-point state, size, file count, backup status, and the application or service that owns the data. A path being large is not permission to move it.

Read [safety-policy.md](safety-policy.md). For cache-only requests also read [cleanup-protocol.md](cleanup-protocol.md). Do not migrate an entire profile, `AppData`, `Program Files`, `Windows`, or a drive root.

## Standard diagnostic path

### 1. Validate the source and risk class
Use literal paths with `win_path_metadata` and `win_path_inventory`; do not follow junctions or scan outside the approved root. Confirm the source is a real directory, not already a reparse point, and that the target path does not exist or is an explicitly empty staging directory.

Resolve source and target aliases and record both volume identities. For an absent target, resolve its nearest existing parent. Apply the path restrictions to the resolved locations and reject identical or nested roots. If the inventory finds cloud placeholders or unsupported reparse points, pause and resolve their data dependencies before copying.

Block migration of Windows, `System32`, `SysWOW64`, `WinSxS`, `WindowsApps`, the `C:\Users` root, `WPSystem`, Edge/Chrome/WebView2 installation directories, Office Click-to-Run, GPU driver directories, `.NET` runtime directories, security drivers, and system-managed components. Warn and require an explicit item-level confirmation for `ProgramData`, database directories, VMware/VirtualBox/Hyper-V data, development toolchains, WeChat/Tencent data, Steam libraries, security software, services, and folders with hard-coded paths.

Check `win_process_list` and `win_path_lock_check`. Ask the user to close the application normally; never force-kill a process as an implicit migration step. If lock evidence is unavailable, report the uncertainty and stop before cutover.

### 2. Check the target volume
Use `win_disk_usage` and `win_volume_inventory` to verify that both paths are on fixed local volumes, the target filesystem is NTFS, and the target has at least `1.2 × source_bytes + 100 MB` free. Do not use network shares, removable media, exFAT, FAT32, or a path that resolves through another junction.

Show the source size, target free bytes, estimated copy time if available, required elevation, restart impact, and the exact rollback path in `ui_spa`. Do not continue to a state change until the user confirms this single migration.

### 3. Copy to an isolated target and verify
Hold an exclusive lock shared by migration and restore. Create a unique target directory on the approved volume. Use `win_copy_verify` with reparse-point exclusion and preservation of file data, timestamps, and directory structure. Record the copy result, file count, byte total, skipped/locked files, and exit code.

Compare source and target byte totals and file counts. For critical application data, sample or fully compare SHA-256 values with `win_file_hash`; a size-only match is not proof of integrity. If any source file changes during the copy, is skipped, or cannot be verified, keep the original untouched and report the incomplete target.

### 4. Switch the original path
Before the first rename, atomically write a `cutover_pending` record outside the source, target and backup trees. Record the operation ID, original/target paths and volume identities, planned sibling backup, and copy verification evidence. Stop at the verified copy if the record cannot be saved.

Recheck the source and verified target, then rename the source to the recorded sibling backup on the same volume. Confirm the original path is free, create the Junction with `win_junction_create`, and verify its exact target with `win_junction_inspect`.

Retain the sibling backup until the application is verified and the user separately approves cleanup. If cutover fails, remove only a verified Junction created by this operation and restore the backup only when the original path is free. Keep both copies and the pending record if rollback cannot be verified.

### 5. Record the migration
Use `win_json_atomic_write` to mark the record `active` after verifying the Junction and its target, or `failed` after verifying rollback. Also record the application/folder name, byte total, verification method, timestamp, link type, and warnings. If saving fails, retain the pending record and report the live state for reconciliation.

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
- `win_junction_remove`
- `win_json_atomic_write`
- `ui_spa`
- `shell_run`
