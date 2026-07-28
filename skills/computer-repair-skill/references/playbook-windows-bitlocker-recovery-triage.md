---
name: windows-bitlocker-recovery-triage
description: Audit BitLocker/device encryption before PE, BIOS, hardware, partition, repair, or reinstall operations
platform: windows
category: windows-repair-boot-hardware
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows BitLocker Recovery Triage

## When to activate

Use before entering PE or Linux, changing BIOS/UEFI or TPM, upgrading firmware, opening a laptop, resizing partitions, reinstalling Windows, moving a disk to another computer, or responding to a BitLocker recovery prompt.
Run this triage while the current Windows session or another connected host is still available. If the device is already in an offline PE/WinRE session, do not assume the Skill or AI is reachable; follow the saved manual checklist and return to a usable host for review.

## Quick check

For every affected volume, record `VolumeStatus`, `ProtectionStatus`, `LockStatus`, key-protector type and whether the recovery key is available. Distinguish full BitLocker from Windows device encryption and identify the Microsoft or organization account that may hold the recovery key. Never print or paste the 48-digit key into chat or logs.

## Standard diagnostic path

### 1. Preserve access

Ask the owner to retrieve and privately save the recovery key for each volume. Confirm a second copy and a verified destination before any external boot or disk operation. A key saved only on the disk being modified is not a backup.

### 2. Classify the planned action

- PE, Linux LiveCD, BIOS/UEFI or TPM change, firmware update, and some hardware maintenance may require suspending protection for the next boot.
- Partition movement, offline data manipulation, a clean reinstall or moving the disk to another device generally requires full decryption or a tool that explicitly supports the encrypted layout.
- Suspension is not decryption: data remains encrypted and protection is restored after the planned reboot when the platform supports it.

### 3. Prefer supported controls

Use Windows Settings, Manage BitLocker or the documented BitLocker PowerShell module. Show the exact volume and intended state transition. Do not use undocumented registry edits, delete protectors, clear TPM or disable Secure Boot to avoid a recovery prompt.

### 4. Recheck before proceeding

After a user-approved suspend or decrypt operation, re-read the volume state, confirm AC power for long decryption, and verify the recovery key remains available. If the state is ambiguous, stop rather than guessing.

## Verification

After repair or reboot, confirm the expected volume is unlocked, protection has resumed when intended, recovery keys are still accessible, and the original data or boot workflow works. Record before/after status without recording secrets.

## Caveats

- BIOS updates, TPM changes, boot-order changes and external boot can legitimately trigger recovery.
- Decryption can take hours and reduces protection during the operation; it is not a routine troubleshooting shortcut.
- Enterprise-managed keys and policies may require the organization's recovery workflow.

## Escalation

Escalate missing keys, locked volumes, TPM or Secure Boot changes, enterprise devices, suspected theft or ransomware, and any request to bypass BitLocker.

## Tools referenced

- `win_bitlocker_status`
- `win_file_hash`
- `win_volume_inventory`
- `ui_spa`
- `shell_run`
