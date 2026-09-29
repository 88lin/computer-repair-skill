---
name: windows-storage-inventory
description: Build a privacy-preserving Windows storage inventory that explains large paths before any cleanup
platform: windows
last_reviewed: 2026-09-29
author: computer-repair-skill-maintainers
source: local
---

# Windows Storage Inventory

## When to activate
Use when a Windows volume is unexpectedly full, an unfamiliar directory is large, or the user wants a map of storage before deciding what to remove.

### 相邻流程：存储与迁移集群

「C 盘满了」会同时命中下面六个流程。先确认用户的真实诉求，命中错了就改路由，不要在本流程里硬做别的流程的事：

- 只想知道空间被谁占了（只读盘点） → [windows-storage-inventory](playbook-windows-storage-inventory.md) ← **本流程**
- 确认是缓存或重复文件 → [windows-application-cleanup](playbook-windows-application-cleanup.md)
- 要把应用或数据挪到别的盘 → [windows-application-migration](playbook-windows-application-migration.md)
- 迁移后出现幽灵链接或要回滚 → [windows-migration-history-recovery](playbook-windows-migration-history-recovery.md)
- 只想安全释放系统盘，不动应用 → [windows-disk-space-recovery](playbook-windows-disk-space-recovery.md)
- 空间确实不够，要动分区（风险最高） → [windows-partition-resize-audit](playbook-windows-partition-resize-audit.md)

完整分流表见 [playbook-index.md](playbook-index.md)。

## Quick check
Record the target volume, exact free/total bytes, Windows build, current user, and whether OneDrive, WSL, Docker, VMs, or backup software is active. Do not infer ownership from size alone.

Read [windows-storage-scan.md](windows-storage-scan.md) for backend selection, scan coverage, bounded drill-down and space accounting. If candidates include Git projects, build outputs, services, databases, models or virtual disks, also read [windows-storage-data-guards.md](windows-storage-data-guards.md).

## Standard diagnostic path

### 1. Measure narrow scopes
Use `win_disk_usage` for fixed volumes, then `win_path_inventory` on the volume root and one level at a time. Use literal paths, a time budget, and a maximum depth. Do not follow junctions or reparse points into another volume or user profile.

Start with ordinary permissions. An already available, reviewed NTFS/ReFS indexer is optional; verify its supported filesystem version and any whole-volume read or elevation before use. Report the actual backend and incomplete coverage when falling back to enumeration. Do not install a scanner or elevate just to produce an initial map.

For each candidate record:

- absolute path, volume, owner and application (if known);
- logical/allocated bytes (unknown when unavailable), file count, file-type distribution, newest/oldest descendant-file write time;
- whether it is synchronized, backed up, regenerable, or unknown;
- the evidence source, scan identity, time window, limits, exclusions, completeness and inaccessible/skipped scopes.

Show the largest entries plus an aggregate of other measured entries; unknown scopes remain separate. Keep a local snapshot when useful and drill into the selected subtree instead of repeating a full scan. Display limits must not masquerade as scan limits or complete totals.

### 2. Classify before explaining
Classify each path as `protected-user-data`, `application-state`, `regenerable-cache`, `system-managed`, or `unknown`. Keep Documents, Downloads, mail, browser profiles, credentials, chat databases, media, cloud roots, VM disks and game libraries in the protected or unknown class until the user identifies them.

Git repositories need local-state and remote-coverage checks, not just a clean HEAD. Ignored files, stopped services and old model/VM directories remain protected or unknown until ownership, regeneration and backup evidence are established.

Cloud-storage clients, backup products and some security tools publish a virtual drive letter or mount point that is not local storage. Report the drive letter, provider and mount evidence read-only; do not include it in a volume free-space calculation, do not scan it for large files, and never target it for cleanup, migration or drive-letter changes. Removing the client's device or letter is the vendor's operation, not a storage fix.

If the user asks for an AI explanation, send only de-identified metadata: path labels, byte totals, counts, extension percentages and at most 20 relative path samples. Never send file contents, secrets, database rows, cookies or private keys.

### 3. Produce a decision report
Present the largest paths with a confidence level, likely owner, regeneration path, last-use evidence and a proposed next check. A large directory is an observation, not a deletion target. Route known applications to `windows-application-cleanup` rather than inventing a glob.

### 4. Plan any cleanup separately
For every proposed target list the exact child paths, expected recovery, application-close requirement, backup/quarantine location and rollback. Read [safety-policy.md](safety-policy.md) before changing anything.

## Verification
Re-run the same inventory and compare exact free bytes and the affected category. Confirm that synchronized folders, applications and the original low-space workflow still work. Inventory-only runs should leave a hashable local report without changing the inspected data.

Compare the same scope, metric and exclusions over the underlying records, not only the displayed Top N. A partial scan cannot prove that missing entries were removed. Report snapshot age and any coverage gaps.

## Escalation
Escalate unexplained growth under Windows, Program Files, System Volume Information, recovery partitions, cloud roots, or a volume showing filesystem errors. Stop when a scan would require broad administrator access or would cross a reparse point.

## Tools referenced
- `win_disk_usage`
- `win_path_inventory`
- `win_file_hash`
- `win_app_data_ls`
- `ui_spa`
- `shell_run`
