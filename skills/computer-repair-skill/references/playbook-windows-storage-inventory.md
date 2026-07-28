---
name: windows-storage-inventory
description: Build a privacy-preserving Windows storage inventory that explains large paths before any cleanup
platform: windows
category: health-performance-storage-backup
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Storage Inventory

## When to activate
Use when a Windows volume is unexpectedly full, an unfamiliar directory is large, or the user wants a map of storage before deciding what to remove.

## Quick check
Record the target volume, exact free/total bytes, Windows build, current user, and whether OneDrive, WSL, Docker, VMs, or backup software is active. Do not infer ownership from size alone.

## Standard diagnostic path

### 1. Measure narrow scopes
Use `win_disk_usage` for fixed volumes, then `win_path_inventory` on the volume root and one level at a time. Use literal paths, a time budget, and a maximum depth. Do not follow junctions or reparse points into another volume or user profile.

For each candidate record:

- absolute path, volume, owner and application (if known);
- bytes, item count, file-type distribution, newest/oldest modification time;
- whether it is synchronized, backed up, regenerable, or unknown;
- the evidence source and timestamp.

### 2. Classify before explaining
Classify each path as `protected-user-data`, `application-state`, `regenerable-cache`, `system-managed`, or `unknown`. Keep Documents, Downloads, mail, browser profiles, credentials, chat databases, media, cloud roots, VM disks and game libraries in the protected or unknown class until the user identifies them.

If the user asks for an AI explanation, send only de-identified metadata: path labels, byte totals, counts, extension percentages and at most 20 relative path samples. Never send file contents, secrets, database rows, cookies or private keys.

### 3. Produce a decision report
Present the largest paths with a confidence level, likely owner, regeneration path, last-use evidence and a proposed next check. A large directory is an observation, not a deletion target. Route known applications to `windows-application-cleanup` rather than inventing a glob.

### 4. Plan any cleanup separately
For every proposed target list the exact child paths, expected recovery, application-close requirement, backup/quarantine location and rollback. Read [safety-policy.md](safety-policy.md) before changing anything.

## Verification
Re-run the same inventory and compare exact free bytes and the affected category. Confirm that synchronized folders, applications and the original low-space workflow still work. Inventory-only runs should leave a hashable report and no state change.

## Escalation
Escalate unexplained growth under Windows, Program Files, System Volume Information, recovery partitions, cloud roots, or a volume showing filesystem errors. Stop when a scan would require broad administrator access or would cross a reparse point.

## Tools referenced
- `win_disk_usage`
- `win_path_inventory`
- `win_file_hash`
- `win_app_data_ls`
- `ui_spa`
- `shell_run`
