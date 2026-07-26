---
name: linux-disk-space-recovery
description: Reclaim Linux disk space and inodes by measuring filesystems, identifying owners, cleaning through native tools, and verifying services
platform: linux
last_reviewed: 2026-07-26
author: noah-computer-care-maintainers
source: local
---

# Linux Disk Space Recovery

## When to activate
User reports a full filesystem, inode exhaustion, package/update failures, runaway logs, container storage growth, or asks to reclaim Linux disk space safely.

## Quick check
Run `linux_disk_usage` and record `df -hT` plus `df -i`. Identify the exact filesystem, mount point, device, free bytes, free inodes, and whether the environment is a host, container, VM, or WSL.

## Standard diagnostic path

### 1. Distinguish bytes from inodes
- Bytes full: measure directory and file sizes.
- Inodes full: count file-heavy directories and identify the creating workload.
- Filesystem appears full but `du` is smaller: check deleted-open files, snapshots, reserved blocks, mount boundaries, and hidden data beneath mounts.

### 2. Measure within one filesystem
Start at the affected mount and stay on that filesystem:
```
du -x -d 1 -h '<MOUNT>' 2>/dev/null | sort -h
```

Descend only into the largest measured directory. Set a time budget and preserve permission errors in the report. Do not cross into network, pseudo, container, or backup mounts unintentionally.

### 3. Check deleted-open files
When `df` and `du` disagree, run `lsof +L1` if available. A process can hold disk blocks after a file is unlinked.

Restarting or signaling that process is a service-impacting action. Identify the process and owner, preserve logs if needed, and obtain approval.

### 4. Inspect common managed stores
Measure before cleanup:
- systemd journal: `journalctl --disk-usage`
- package manager caches and obsolete packages
- container images, layers, volumes, and build cache
- application logs and crash dumps
- old kernels through the package manager
- language/package caches owned by the user
- VM images, database files, backups, and snapshots

Use the owning tool's dry-run, list, or prune report. Do not remove files directly from package, database, container, or journal internals.

### 5. Propose a tiered cleanup
Show exact targets, owner, last use, regeneration path, expected bytes/inodes, and rollback:
1. Rotated or expired logs through the logging system.
2. Package caches through the active package manager.
3. Confirmed unused container/build artifacts through the container engine.
4. Application caches after stopping or closing the owner.
5. User-selected data copied to verified storage.

Protect home content, credentials, databases, active container volumes, backups, cloud mounts, and unknown state directories.

### 6. Execute with checkpoints
Obtain approval for concrete targets. Follow `safety-policy.md` before deletion: literal paths, prior inspection, no hidden indirection, and post-action verification.

For remote systems, preserve enough free space for logs and package operations before attempting larger repairs. Avoid restarting the service carrying the current session without a recovery path.

## Verification
Re-run `df -hT`, `df -i`, and the original failed workflow. Report exact before/after bytes and inodes. Verify every service whose logs, cache, packages, or process state changed.

## Caveats
- Sparse files, snapshots, reflinks, reserved blocks, and copy-on-write storage complicate apparent sizes.
- Container storage and databases require owner-aware cleanup.
- Deleting a file held open by a process does not release space until the handle closes.
- Log growth may immediately return unless the source failure or retention policy is corrected.

## Key signals
- Inodes 100%, bytes available -> too many files.
- `df` much larger than `du` -> deleted-open files, snapshots, reserved space, or mount effects.
- `/var/log` regrows -> diagnose the emitting service.
- Container store dominates -> inventory images, containers, build cache, and volumes separately.

## Tools referenced
- `linux_disk_usage`
- `linux_process_list`
- `linux_read_log`
- `shell_run`

## Escalation
Escalate filesystem errors, read-only remounts, database growth, storage-device faults, snapshot ambiguity, or recurrent exhaustion with mount details, measurements, service ownership, and current backup status.
