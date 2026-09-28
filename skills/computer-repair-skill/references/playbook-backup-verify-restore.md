---
name: backup-verify-restore
description: Verify backup integrity by checking status, timestamps, and testing a real file restore
platform: all
last_reviewed: 2026-09-28
author: upstream-maintainers
source: bundled
emoji: 💾
---

# Backup Verify & Restore Test

Verifies that the device's backup system is working correctly by checking the backup tool status, confirming the last backup timestamp, and performing a test restore of a known file. This proves backups are not just running but actually recoverable.

## When to activate
Periodic backup verification, after setting up a new backup, compliance audit, or when the admin wants to confirm RPO/RTO for a device.

## Standard check path

### 1. Identify the backup tool
Detect which backup system is in use:
- **macOS**: Check Time Machine status via `tmutil status` and `tmutil latestbackup`.
- **Windows**: `fhmanagew.exe` has no status switch (its only documented switch is `-cleanup <days>`), so query the scheduled task and the config file instead:
  ```powershell
  Get-ScheduledTask -TaskPath '\Microsoft\Windows\FileHistory\' | Get-ScheduledTaskInfo
  Test-Path "$env:LOCALAPPDATA\Microsoft\Windows\FileHistory\Configuration\Config.xml"
  ```
  A `Config.xml` that exists means File History was configured; `LastRunTime`/`LastTaskResult` from the task tell you whether it is still running. Also check Settings → Windows Backup.
- **Linux**: Check for Timeshift (`timeshift --list`), Borg (`borg list`), Restic (`restic snapshots`), or Deja Dup.

If no backup tool is detected, report this immediately and recommend setting one up.

### 2. Check last backup timestamp
For the detected backup tool:
- **Time Machine**: Parse the date from `tmutil latestbackup` output.
- **File History**: Read `LastRunTime` from `Get-ScheduledTaskInfo` above, or take the newest timestamp under the target drive's `FileHistory\<user>\<host>\Data` folder.
- **Timeshift**: Parse the most recent snapshot date from `timeshift --list`.
- **Borg/Restic**: Parse the most recent archive/snapshot timestamp.

Calculate hours since last backup. Report:
- < 24h: Good — backup is recent.
- 24h-7d: Warning — backup may be stale.
- > 7d: Critical — backup is significantly out of date.

### 3. Check backup destination health
Verify the backup destination is accessible:
- **Time Machine**: Check if the backup volume is mounted (`tmutil destinationinfo`).
- **Windows File History**: Verify the backup drive is connected.
- **Network backups**: Test connectivity to the backup server/NAS.
- **Cloud backups**: Test connectivity to the cloud endpoint.

Report: destination type (local drive, network, cloud), available space, and connectivity status.

### 4. Test restore of a known file
Obtain approval for the restore write and select a known file from a completed backup.
If creating a new probe, use a unique name in an approved backed-up location without
overwriting an existing file, and wait for confirmed backup completion.
- Allocate a unique, private, empty restore directory on a verified destination with
  enough space; on macOS/Linux use `mktemp -d`, on Windows a GUID directory with a
  current-user-only ACL. Reject links and never reuse a fixed `/tmp/restore-test/`.
- **Time Machine**: `tmutil restore <backup_path> <unique_destination>`.
- **Borg 1.x**: change to that empty destination, then use
  `borg extract <repo>::<archive> <relative_path_in_archive>`. Confirm the installed
  major version's help first; archive syntax differs across versions. Borg extracts
  into the current directory, and has no generic `--path` extraction option.
- **Restic**: `restic restore <snapshot> --target <unique_destination> --include <file>`.
- Verify hashes against the selected backup version or a recorded baseline. A current
  source file may have changed since that snapshot; a mismatch is not automatically corruption.

Report: restore succeeded/failed, time taken, file integrity check result.

### 5. Document RPO/RTO
Based on the findings, calculate and report:
- **RPO (Recovery Point Objective)** is the agreed acceptable data-loss window. Report
  the age of the last verified backup as observed exposure and compare it to that target.
- **RTO (Recovery Time Objective)** is the agreed recovery-time target. Report measured
  sample restore time separately; one file test does not establish full-system recovery time.
- **Backup frequency**: How often backups run (continuous, hourly, daily).
- **Retention**: How far back can you restore (if detectable).

Present this as a summary the admin can use for compliance documentation.

### 6. Clean up
Remove any test files created during the verification:
- Revalidate the recorded paths and remove only this run's probe and restore directory
  after approval. Preserve restored evidence if the user requests it; do not sweep a shared temp root.

## Caveats
- **Restore tests write potentially sensitive data** — use a private isolated destination and verify it cannot overwrite live files.
- **Time Machine restore requires the backup disk to be connected.** If it's a network backup, ensure the network is available.
- **Full system restore cannot be tested this way.** This only verifies file-level restore. Full bare-metal recovery requires booting from recovery media.
- **Encrypted backups** may require a password to restore. If the password is unknown, the backup is effectively unusable — flag this to the admin.

> Most commonly missed: verifying the backup destination has enough free space for continued backups.

## Key signals
- **"When was the last backup?"** → run steps 1-2 only. Quick check.
- **"Can we actually restore from this backup?"** → run steps 1-4. Full verification.
- **"Compliance audit needs backup documentation"** → run all steps, focus on step 5 (RPO/RTO documentation).
- **"Setting up a new backup, want to verify it works"** → run all steps after the first backup completes.

## Escalation
If verification reveals:
- No backup tool installed → recommend setting one up immediately. Use the `setup-backup` playbook.
- Backup destination is full or inaccessible → the admin needs to provision more storage or fix the network path.
- Restore test fails → the backup may be corrupted. Check backup logs, try restoring from an older snapshot, or reconfigure the backup.
- Backup is encrypted and password is unknown → this is a critical issue. The backup is unrecoverable. Document and escalate to the admin.

## Tools referenced
- Shell commands — backup tool queries, file creation, restore commands
- Disk usage tools — checking backup destination space
