---
name: windows-boot-failure-triage
description: Triage Windows startup, No Boot Device, UEFI/boot-entry, and pre-login failures without blindly changing firmware
platform: windows
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Boot Failure Triage

## When to activate
Use for `No Boot Device`, missing Windows Boot Manager, boot loops, a machine that reaches firmware but not Windows, or a blue pre-login screen that may not be a normal BSOD.

## Quick check
Capture the exact message and a photograph if possible. Record whether the system reaches POST/UEFI, whether the internal disk is visible in firmware, the current boot mode and order, BitLocker status, recent disk/BIOS/driver changes, attached USB media, and the last known working boot. Do not change firmware values while the evidence is incomplete.

## Standard diagnostic path

### 1. Separate the failure layer
- No display or no POST: treat as power, memory, display or board hardware.
- Firmware sees no disk: stop and investigate storage connection, drive health or firmware compatibility.
- Firmware sees the disk but no boot entry: check UEFI versus Legacy history and the EFI boot entry; do not convert the partition scheme blindly.
- Windows begins loading then fails: route to `windows-winre-system-repair` and collect stop code or event evidence.

### 2. Rule out removable and transient causes
Disconnect unneeded USB drives, docks and external disks, but preserve the user's recovery media. Check whether a recent firmware update, battery drain, forced shutdown or driver change preceded the failure. A one-off `EARLY EXIT ON FAILURE` screen is not automatically a kernel BSOD; a tested first response is `Ctrl+Alt+Delete`, sign out, and restart if the screen accepts it.

### 3. Review UEFI/boot configuration safely
Read the vendor manual and current firmware screen. A Windows installation created for UEFI normally needs a UEFI boot path; an old Legacy/MBR installation may not boot after an arbitrary switch. Present the exact proposed firmware change and its reversal before the user performs it. Do not automate BIOS changes.

### 4. Protect data before external boot
Before PE, WinRE or another OS accesses the disk, run `windows-bitlocker-recovery-triage`. Back up the recovery key and confirm a separate destination. Do not run repair or partition commands against the source disk while recovery is the goal.

### 5. Choose the smallest recovery path
Use the built-in recovery environment or a verified Microsoft installation/recovery medium. Prefer startup diagnostics and read-only inspection. Repartitioning, `bootrec`, `bcdboot`, formatting, firmware updates and reinstalling Windows require a separate high-impact plan.

## Verification
Confirm the disk is still detected, the intended boot entry and mode are unchanged or explicitly documented, BitLocker remains recoverable, Windows reaches the expected sign-in state, and the original data and applications remain available.

## Caveats
- `No Boot Device` can mean a missing boot entry, a failed disk, a disabled storage controller or a mode mismatch; the text alone is not a diagnosis.
- A blue screen before sign-in may be firmware, OEM recovery or setup UI rather than Windows crash data.
- Repeated boot attempts can write logs or trigger recovery changes; minimize retries when data recovery matters.

## Escalation
Escalate an undetected disk, SMART errors, BitLocker key gaps, suspected filesystem damage, firmware changes, missing recovery media, a managed device, or any request to erase or repartition the disk.

## Tools referenced
- `win_system_info`
- `win_disk_usage`
- `win_volume_inventory`
- `win_read_log`
- `win_file_hash`
- `ui_spa`
- `shell_run`
