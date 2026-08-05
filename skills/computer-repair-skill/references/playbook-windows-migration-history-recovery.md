---
name: windows-migration-history-recovery
description: Audit Windows Junction migration history, detect ghost links, and restore data with conflict-safe rollback
platform: windows
last_reviewed: 2026-08-05
author: computer-repair-skill-maintainers
source: local
---

# Windows Migration History and Recovery

## When to activate
Use when a migrated application or folder no longer opens, a Junction may be broken, migration history needs auditing/export, or the user wants to restore data to its original path.

## Quick check
Locate the migration manifest, make a read-only backup, and record active operations. Treat history as untrusted metadata until the original path, link target, owner, and target contents are checked on disk. Acquire one restore lock for the entire operation; do not run concurrent restores.

## Standard diagnostic path

### 1. Audit every active record
Use `win_json_atomic_write` only for the final update; read the manifest with `shell_run` or `win_read_file`. For each record use `win_junction_inspect` and `win_path_metadata` to classify:

- `healthy`: original path is a Junction and its target exists;
- `target_missing`: the link is valid but the target no longer exists;
- `junction_broken`: original path exists but is an ordinary directory or points elsewhere;
- `original_missing`: the original path and link are gone, with no recoverable target;
- `unknown`: permissions, path changes, or filesystem errors prevent a conclusion.

Show the record ID, original/target paths, link type, target existence, byte total, last verification time, and proposed action. Do not trust a cached UI status.

### 2. Preview ghost-link cleanup
For `target_missing`, remove only a confirmed orphaned Junction and mark the record `ghost_cleaned`; never delete a target path that still contains data. For `original_missing`, mark the record only when the target is absent or provably empty. For `junction_broken`, refuse automatic deletion: an ordinary directory may contain newer user data and must be compared or reviewed first.

Export the before-state and a per-record preview. An import must validate JSON schema, deduplicate IDs, normalize paths, and remain inactive until each path is verified on the current machine.

### 3. Restore one record
After explicit confirmation, stop the owning application normally and acquire the restore lock. Verify the record is active, the target exists and is non-empty, the original path is a Reparse Point, and the destination volume has at least `1.1 × recorded_bytes` free using `win_disk_usage`.

Remove only the original Junction with `win_junction_remove`; never use recursive deletion on a link. Move the target directory back to the original path with `win_move_file`, then compare byte totals and selected/full hashes. Update the manifest atomically to `restored` only after the data and original workflow are verified.

If the move or verification fails, stop and recreate the Junction to the still-intact target when possible. If both paths contain data, do not merge automatically; preserve both and request a file-level comparison or backup restore.

### 4. Reconcile interrupted operations
A sibling backup, temporary target, or `.tmp` manifest is evidence of an interrupted operation, not a cleanup target. Compare paths, sizes, timestamps, and hashes; keep the newest verified copy only after an explicit user decision. Record the outcome and any retained artifacts in the operation log.

## Verification
Re-scan the restored path, confirm it is an ordinary directory with the expected bytes, launch the application or open the folder workflow, and verify the history status and backup/export file. Report all records left in `unknown`, `target_missing`, or `junction_broken` state.

## Caveats
- Windows Junctions may not be reported as ordinary symbolic links by every API; inspect the Reparse Point attribute and target explicitly.
- A missing original directory after an external uninstall is not a reason to create an empty directory. Mark the record as no recoverable data only when the target is absent or empty.
- History JSON is not a backup of the migrated data. Keep independent backups and do not expose paths containing credentials or personal data in reports.

## Escalation
Escalate filesystem errors, conflicting ordinary directories, encrypted or synchronized data, missing manifests, target data that changed after migration, or any restore that would overwrite newer files.

## Tools referenced
- `win_path_metadata`
- `win_junction_inspect`
- `win_junction_remove`
- `win_disk_usage`
- `win_process_list`
- `win_move_file`
- `win_directory_size`
- `win_file_hash`
- `win_json_atomic_write`
- `win_operation_log`
- `ui_spa`
- `shell_run`
