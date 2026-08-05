---
name: windows-large-folder-management
description: Discover, lazily size, and safely offload selected Windows system or application folders
platform: windows
last_reviewed: 2026-08-05
author: computer-repair-skill-maintainers
source: local
---

# Windows Large Folder Management

## When to activate
Use when the user wants to find large Windows folders, inspect known application-data locations, or move a selected folder to another local volume.

## Quick check
Read [windows-storage-inventory](playbook-windows-storage-inventory.md) for the initial storage map. Record the volume, exact path, owner, synchronization/backup state, reparse-point state, and whether the user wants inventory only, a move, or deletion. Keep these goals separate.

## Standard diagnostic path

### 1. Start with a cheap inventory
Use `win_path_inventory` to list approved system folders (Desktop, Documents, Downloads, Pictures, Videos), known application-data templates, and user-added custom folders. Return metadata first: path, type, last-write time, item count estimate, and a size state of `pending` rather than recursively blocking the whole interface.

Never add the whole user profile, `AppData`, `ProgramData`, `Windows`, a drive root, a browser profile, a VM disk, or a chat database as a generic folder. Known application templates must point to a specific child directory and include an owner and redlines.

### 2. Lazy-size expensive paths
After the initial list is visible, run bounded asynchronous size scans with `win_directory_size` and report progress, errors, permission skips, and reparse points separately. Load application-data templates only when the user requests them; this avoids an unbounded HDD scan and prevents a stale scan from overwriting a refreshed result.

For each folder classify it as `system-managed`, `application-state`, `regenerable-cache`, `synchronized-user-data`, `backup/VM`, or `unknown`. A large result remains report-only until the owner and desired action are clear.

### 3. Plan a move or cleanup
For an offload, activate [windows-application-migration](playbook-windows-application-migration.md). Show exact source/target paths, bytes, filesystem, free-space reserve, process locks, backup status, link type, and rollback. For a cache cleanup, activate [windows-application-cleanup](playbook-windows-application-cleanup.md) instead of deleting by extension or size.

For synchronized folders, databases, mail stores, game libraries, VM disks, credentials, and chat data, require an owner-specific backup and application shutdown plan. Do not treat a template match as proof that a directory is safe to remove.

### 4. Maintain templates and reports
Store custom-folder and application-template definitions as versioned, atomically written data. A template must include the literal path rule, owner, category, exclusions, last review date, and whether it is eligible for migration, cleanup, or inventory only. Keep reports privacy-preserving: paths may be redacted and file contents are never needed for sizing.

## Verification
Re-run the same path inventory and size scan after an approved move. Verify the Junction target, byte totals, original workflow, synchronization state, and manifest. Report inaccessible entries, locked files, stale templates, and folders whose size changed during scanning.

## Caveats
- Lazy sizing improves responsiveness but can be stale; record scan start/end times and do not use an old size for a destructive plan.
- Windows Shell known folders can be redirected through supported settings; a Junction is not always compatible with OneDrive or enterprise policy.
- Application caches and profiles often share a parent. Keep cache-only and user-state paths as separate template entries.

## Escalation
Escalate unknown folders under system roots, reparse-point chains, active databases, cloud-provider placeholders, VM images, filesystem errors, or any scan that requires broad administrator access.

## Tools referenced
- `win_path_inventory`
- `win_directory_size`
- `win_path_metadata`
- `win_junction_inspect`
- `win_json_atomic_write`
- `ui_spa`
- `shell_run`
