---
name: windows-disk-space-recovery
description: Reclaim Windows disk space by measuring volumes, identifying safe targets, preserving user data, and verifying freed space
platform: windows
last_reviewed: 2026-07-26
author: computer-care-maintainers
source: local
---

# Windows Disk Space Recovery

## When to activate
User reports a full Windows drive, low-space warnings, update failures caused by storage, or asks to reclaim space without losing personal data.

## Quick check
Run `win_disk_usage` and record total/free space for each fixed volume. Confirm the target volume and requested free-space goal.

Do not begin deletion from a drive-level percentage alone. Measure categories first.

## Standard diagnostic path

### 1. Establish the baseline
Query `Win32_LogicalDisk` for fixed volumes. Record bytes, not only rounded GB. Check whether the low-space volume contains Windows, user profiles, applications, VMs, containers, or synchronized folders.

### 2. Measure top-level categories
Measure specific directories one level at a time. Start with user-approved roots such as the affected profile, `C:\ProgramData`, application caches, package caches, VM images, and container data.

Use PowerShell enumeration with a narrow literal path. Set a time budget; recursive scans of the full system drive can be slow and permission-limited.

Do not follow reparse points blindly. Treat OneDrive and other synchronized roots as user data.

### 3. Inspect Windows-managed storage
Check Settings storage categories or approved system tools. Analyze the component store before proposing cleanup:
```
DISM.exe /Online /Cleanup-Image /AnalyzeComponentStore
```

Inspect Windows Update download cache, Delivery Optimization, Recycle Bin, crash dumps, temporary files, hibernation, restore points, and old Windows installations as separate categories. Each has different recovery and rollback implications.

### 4. Inspect application and development data
Common large but intentional locations include IDE caches, package managers, Docker/WSL virtual disks, game libraries, browser profiles, Outlook data, VM images, and build artifacts.

Identify owner, last use, regeneration path, and whether the data is synchronized or backed up. A large directory is evidence, not permission to remove it.

### 5. Propose a tiered cleanup
Show exact measured targets and expected recovery:
1. Recycle Bin and confirmed temporary artifacts.
2. Application caches known to regenerate, after closing the application.
3. Package/download caches through their native package manager.
4. Windows-managed cleanup through Settings or supported commands.
5. User-selected archives, VMs, installers, or media moved to verified storage.

Keep user files, mail stores, browser profiles, credentials, cloud roots, and unknown application data out of automatic cleanup.

### 6. Execute with checkpoints
Obtain approval for the listed targets. Before each delete, follow `safety-policy.md`: inspect the literal path, enumerate concrete entries, and record recovery.

For offload requests, copy to the target, compare size/file count or hashes, let the user confirm the copy, then propose local cleanup separately.

## Verification
Re-run `win_disk_usage` and report exact before/after free bytes. Verify Windows Update or the original blocked workflow, plus the applications whose caches were touched.

## Caveats
- Hibernation, restore points, component-store cleanup, and previous Windows installations reduce rollback options.
- WSL and Docker virtual disks may not shrink when files inside are deleted.
- OneDrive Files On-Demand state must be understood before changing local availability.
- Antivirus and indexing can temporarily hold deleted files or increase IO during cleanup.

## Key signals
- Low free space plus update failure -> recover supported system headroom first.
- Large user profile -> measure categories; preserve personal and synchronized data.
- Large WSL/Docker data -> clean through the owning platform, then inspect compaction separately.
- Large `WinSxS` -> trust DISM analysis, not Explorer's apparent size.

## Tools referenced
- `win_disk_usage`
- `win_app_data_ls`
- `win_clear_app_cache`
- `win_move_file`
- `shell_run`

## Escalation
Escalate unknown system growth, filesystem errors, repeated volume exhaustion, or failed storage hardware with exact path measurements, volume health evidence, and a current backup status.
