---
name: windows-partition-resize-audit
description: Audit Windows partition and C-drive expansion requests with backup, BitLocker, adjacency and offline-tool safety checks
platform: windows
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Partition Resize Audit

## When to activate
Use when the user wants to expand C:, shrink or move a data partition, merge free space, change a disk layout or prepare a disk for reinstall.

## Quick check
Build a read-only map of physical disks, partition order, sizes, filesystem, free space, boot/recovery partitions, BitLocker state and mounted volumes. Record which filesystems and user data are on every partition that would move. Do not infer that free space at the end of D: is adjacent to C:.

## Standard diagnostic path

### 1. Establish recoverability
Back up important data from every partition that may move and verify the copy. For high-value or failing disks, make a verified image. Run `windows-bitlocker-recovery-triage` and ensure all relevant volumes have recovery keys; offline partition tools may not support encrypted NTFS layouts.

### 2. Determine whether the request is actually needed
Run `windows-storage-inventory` and `windows-disk-space-recovery` first. Remove only confirmed regenerable data or move verified archives if that solves the capacity problem. A small C: drive is not by itself a reason to repartition.

### 3. Check geometry and tool boundary
Windows Disk Management can extend into immediately adjacent unallocated space, but cannot safely move arbitrary intervening data. Moving a partition requires an offline PE/WinToGo environment and a reviewed tool. Do not resize the running system volume with an unreviewed hot operation.

### 4. Produce a human-executed plan
List the exact disk, partitions, source of free space, expected new sizes, order of any moves, AC-power requirement, estimated downtime, backup location and rollback limitation. When multiple partitions are crossed, the plan must move them from the farthest affected partition toward C: and must stop if any partition is dynamic, encrypted, failing or unknown.

### 5. Keep execution outside automatic repair
The host Agent may collect the map and verify results, but must not invoke `Resize-Partition`, DiskGenius, GParted, format, delete-partition or a PE imaging tool without a separate explicit authorization and technician-controlled session. Never resize a disk whose only backup is on a partition being moved.

## Verification
After the technician reports completion, re-read the partition table, volume sizes, filesystem health, drive letters, BitLocker state and boot entries. Compare file counts or hashes for affected data and run the original low-space workflow. Do not delete the old backup until the user confirms the result.

## Caveats
- Power loss or a crashed partition tool during data movement can make an entire volume inaccessible.
- SSD free space and filesystem free space are different; shrinking a partition does not create a backup.
- Recovery and EFI partitions are not ordinary data volumes and must not be merged or deleted casually.

## Escalation
Escalate missing backups, BitLocker key gaps, dynamic or vendor-managed disks, filesystem errors, SMART warnings, multiple-disk ambiguity, boot/recovery partition changes and any request to erase data.

## Tools referenced
- `win_volume_inventory`
- `win_disk_usage`
- `win_bitlocker_status`
- `win_file_hash`
- `win_recovery_image_scan`
- `ui_spa`
- `shell_run`
