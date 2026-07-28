---
name: windows-data-recovery-triage
description: Triage deleted or inaccessible Windows data with image-first read-only recovery to a separate target
platform: windows
category: windows-data-recovery
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Data Recovery Triage

## When to activate

Use for accidental deletion, an inaccessible volume, a damaged filesystem, or a request to recover files from a Windows disk or image.

## Quick check

Stop writes to the affected volume. Record the volume state, BitLocker status, filesystem errors, backup availability and a separate destination with enough space. Do not install a recovery tool, mount the source read-write or save recovered files back to the source.

## Standard diagnostic path

### 0. Freeze the evidence

Capture the exact symptom, affected volume, recent writes or repairs, encryption state, backup availability and source/destination identifiers before launching a scanner. Do not use a successful mount, preview or scan as permission to repair the source.

### 1. Preserve the source

Prefer a hardware write blocker or a verified sector image/clone. Record source and destination identifiers without exposing unnecessary serial numbers. If the disk is failing, minimize reads and involve a recovery provider.

### 2. Scan, report, recover later

Use `win_recovery_image_scan` or an approved forensic tool against the image/device in read-only mode. Follow a scan-first workflow: generate a report (DFXML or the tool's equivalent), log the tool/version and hash the image/report with `win_file_hash`, then choose files from the report. Do not mix scanning, destructive repair and recovery in one unreviewed command.

### 3. Write to an isolated target

Recover selected files to a separate verified volume. Preserve original relative paths, timestamps and hashes when the tool supports them. Quarantine suspicious executables and scan them before opening. If the request is legal, employment or incident-related, preserve the report and chain-of-custody notes.

### 4. Validate the result

Compare recovered file counts, sizes and hashes to the report, then let the user confirm the destination before any source cleanup. A successful scan is not proof that every file is recoverable or intact.

## Verification

Verify that the source volume was not written, the report and image hashes are stable, recovered files open in a safe viewer, and the original backup/restore path remains available.

## Caveats

- SSD TRIM, encryption, overwritten sectors and filesystem corruption can make recovery incomplete.
- Mounting a recovered report as a filesystem is for browsing; do not treat it as a writable repair target.
- Never run `chkdsk /f`, format, repartition or “repair” the source before imaging when recovery matters.

## Escalation

Escalate failing hardware, BitLocker recovery-key gaps, ransomware or malware evidence, encrypted enterprise volumes, legal holds, or a destination that cannot be verified.

## Tools referenced

- `win_recovery_image_scan`
- `win_file_hash`
- `win_disk_usage`
- `win_read_log`
- `ui_spa`
