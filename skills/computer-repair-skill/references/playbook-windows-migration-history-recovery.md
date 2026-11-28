---
name: windows-migration-history-recovery
description: Audit Windows Junction migration history, detect ghost links, and restore data with conflict-safe rollback
platform: windows
last_reviewed: 2026-11-29
author: computer-repair-skill-maintainers
source: local
---

# Windows Migration History and Recovery

## When to activate
Use when a migrated application or folder no longer opens, a Junction may be broken, migration history needs auditing/export, or the user wants to restore data to its original path.

### 相邻流程：存储与迁移集群

「C 盘满了」会同时命中下面六个流程。先确认用户的真实诉求，命中错了就改路由，不要在本流程里硬做别的流程的事：

- 只想知道空间被谁占了（只读盘点） → [windows-storage-inventory](playbook-windows-storage-inventory.md)
- 确认是缓存或重复文件 → [windows-application-cleanup](playbook-windows-application-cleanup.md)
- 要把应用或数据挪到别的盘 → [windows-application-migration](playbook-windows-application-migration.md)
- 迁移后出现幽灵链接或要回滚 → [windows-migration-history-recovery](playbook-windows-migration-history-recovery.md) ← **本流程**
- 只想安全释放系统盘，不动应用 → [windows-disk-space-recovery](playbook-windows-disk-space-recovery.md)
- 空间确实不够，要动分区（风险最高） → [windows-partition-resize-audit](playbook-windows-partition-resize-audit.md)

完整分流表见 [playbook-index.md](playbook-index.md)。

## Quick check
Locate and read the migration manifest and note active or pending operations. Treat history as untrusted metadata until the original path, link target, owner, volume identity, and target contents are checked on disk. Export the relevant record before approved changes and use the same exclusive lock as migration.

## Standard diagnostic path

### 1. Audit every active record
Read the manifest with `shell_run` or `win_read_file`. Use `win_junction_inspect`, `win_path_metadata`, and `win_volume_inventory` to classify each record:

- `healthy`: the original Junction points to the approved directory, which exists on the expected volume;
- `target_unavailable`: the expected volume is offline, locked, or its identity cannot be confirmed;
- `target_missing`: the original Junction points to the recorded path, and that path is verified absent on the correct online volume;
- `junction_broken`: original path exists but is an ordinary directory or points elsewhere;
- `original_missing`: the original path and link are gone. Record the target and sibling backup separately as possible recovery sources;
- `unknown`: permissions, path changes, or filesystem errors prevent a conclusion.

Show the record ID, original/target paths, link type, target existence, byte total, last verification time, and proposed action. Do not trust a cached UI status.

### 2. Preview ghost-link cleanup
Only a confirmed `target_missing` Junction qualifies for a cleanup preview. Recheck the volume and exact Junction target after approval, remove only the link, then mark the record `ghost_cleaned`. Preserve records with unavailable drives or unknown volume identity, and check sibling backups before declaring data lost. An ordinary directory or Junction pointing elsewhere needs a separate review.

Export the before-state and a per-record preview. An import must validate JSON schema, deduplicate IDs, normalize paths, and remain inactive until each path is verified on the current machine.

### 3. Restore one record
After explicit confirmation, acquire the shared lock and stop the owning application normally. Verify the original path is a Junction pointing to the exact recorded target on the expected volume. Use `win_directory_size` to measure the current target and confirm at least `1.1 × current logical bytes` is free for the staged copy on the original volume using `win_disk_usage`. An incomplete measurement cannot authorize cutover.

Use `win_copy_verify` to copy the target into a unique sibling staging directory while the original Junction remains intact. Compare relative paths, byte totals, and selected/full hashes with `win_file_hash`. Leave the Junction and target intact if copying or verification fails.

Save an atomic `restore_pending` record outside the affected trees with all three paths, both volume identities, and the verification evidence. Right before unlinking, recheck the Junction, target, volumes, and application locks. Remove only the verified Junction with `win_junction_remove`, then rename the staging directory into the vacant original path on the same volume. If the rename fails, recreate the verified Junction only if the original path is still free. Otherwise preserve the conflicting data, target, staging directory, and record for review.

Mark the record `restored` only after the data and original workflow are verified. Retain the migration target for a separate cleanup decision.

### 4. Reconcile interrupted operations
Reconcile `cutover_pending` and `restore_pending` records against live paths, volume identities, and verification evidence before retrying. Preserve sibling backups, partial copies, and pending records until rollback or restore is verified. If history is missing, inspect Junctions only within a user-selected original-side directory without traversing them. Treat any recovered history as a candidate and verify its exact target and ownership before asking to import it.

## Verification
Re-scan the restored path, confirm it is an ordinary directory with the expected bytes, launch the application or open the folder workflow, and verify the history status and backup/export file. Report all records left in `unknown`, `target_missing`, or `junction_broken` state.

## Caveats
- Windows Junctions may not be reported as ordinary symbolic links by every API; inspect the Reparse Point attribute and target explicitly.
- A missing original directory after an external uninstall is not a reason to create an empty directory. Mark the record as no recoverable data only when the target is absent or empty.
- History JSON is not a backup of the migrated data. Keep independent backups and do not expose paths containing credentials or personal data in reports.

## Escalation
Escalate filesystem errors, conflicting ordinary directories, encrypted or synchronized data, missing history without a verified recovery candidate, or any restore that would overwrite newer files.

## Tools referenced
- `win_path_metadata`
- `win_junction_inspect`
- `win_junction_create`
- `win_junction_remove`
- `win_disk_usage`
- `win_volume_inventory`
- `win_process_list`
- `win_path_lock_check`
- `win_read_file`
- `win_copy_verify`
- `win_move_file`
- `win_directory_size`
- `win_file_hash`
- `win_json_atomic_write`
- `win_operation_log`
- `ui_spa`
- `shell_run`
