---
name: macos-filevault-recovery-triage
description: Check FileVault, APFS crypto users and recovery-key escrow before service, erase or data recovery on a Mac
platform: macos
category: macos-linux-repair
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# macOS FileVault And Recovery Triage

## When to activate

Run this **before** any of the following on a Mac: hardware service, logic-board or storage replacement, erase and reinstall, Recovery or Migration Assistant work, target-disk or external-boot use, removing the disk, resetting the password, changing the enrolment state, or handing the Mac to a repair shop.

Also activate when the user reports being stuck at a password prompt at startup, a Mac asking for a recovery key, "your disk is locked", an unlock that no longer accepts a known password, or a Mac that no longer starts after an account or MDM change.

## Quick check

Run `mac_system_info` and `mac_filevault_status` and record:

- macOS version and whether the Mac is Apple silicon or Intel with or without a T2 chip;
- FileVault state (on, off, encrypting, decrypting) and progress if in transition;
- which accounts are enabled to unlock the disk;
- whether a personal recovery key exists, whether an institutional key exists, and whether iCloud is allowed to unlock the disk;
- APFS container layout and the crypto users on the system volume;
- System Integrity Protection state and MDM enrolment state.

**Then stop and ask the escrow question with `ui_user_question`, using preset options:** where is the recovery key today — printed or written down, stored in a password manager, escrowed to iCloud, escrowed to MDM or an institutional key, or unknown? "Unknown" is a blocking answer, not a detail.

Never ask the user to type the recovery key or the account password into the conversation, and never print either into a report. When a key must be used, the user enters it at the macOS prompt on the machine itself.

## Standard diagnostic path

### 1. Understand what is actually encrypted

On Apple silicon and T2 Macs the internal storage is always encrypted at rest by the hardware. FileVault adds the requirement that a credential be supplied before the data volume can be unlocked at startup.

Two consequences that change advice:

- With FileVault **off**, data is still encrypted at rest but unlocks automatically. Removing the storage from the machine still does not give a readable disk on Apple silicon or T2 hardware, because the keys are bound to that Mac's Secure Enclave.
- With FileVault **on**, losing every credential and every escrow copy means the data is unrecoverable. No tool, vendor or service can decrypt it. Say this plainly rather than implying a recovery path exists.

On older Intel Macs without a T2 chip, an unencrypted volume is readable from another machine, so physical possession matters more.

### 2. Confirm at least two independent unlock paths before proceeding

Before any state-changing work, the user should have two of:

- a working account password for an unlock-enabled user;
- the personal recovery key, verified to be the current one;
- MDM or institutional escrow the organisation confirms it can retrieve;
- iCloud unlock, where the Apple Account credentials are known and reachable.

If only one path exists, treat the engagement as high risk and say so. If none exists and FileVault is on, the only honest options are: recover the credential, or accept data loss.

### 3. Verify the backup before touching encryption

Run `mac_disk_usage` to confirm there is space for a backup, then confirm a **verified** backup exists — not merely a configured one. Route to `backup-verify-restore` and actually restore one sample file to an independent target.

Also list APFS local snapshots on the system volume: they are useful for rolling back a recent mistake, but they live on the same disk and are not a backup.

Do not start an erase, a decryption, a re-encryption or a storage replacement on the strength of a backup nobody has tested.

### 4. Read the evidence for a stuck unlock

For a Mac that will not accept a known credential, use `mac_read_log` to review the unlock and authentication records around the failure window, and check:

- whether the account is actually unlock-enabled, since a newly created or MDM-created account may not be;
- whether the password was changed elsewhere, such as by a directory service or MDM, so the local volume key still expects the old one;
- whether the keyboard layout at the pre-boot screen differs from the one in the session, which silently breaks correct passwords;
- whether an external keyboard is being used at a pre-boot screen where it is not yet initialised;
- whether the Mac is in a transitional encryption state, which can change unlock behaviour until it completes.

An account that is not unlock-enabled is a configuration problem with a straightforward fix while the Mac is still unlocked, and an unrecoverable problem after it locks.

### 5. Plan the change with rollback

Only after escrow and backup are confirmed, show the plan and get explicit approval. State for each step what changes, what breaks if it fails, and how to get back.

- Adding an unlock-enabled account, or enabling an existing one, is the lowest-risk remedy and should be done while the Mac is unlocked.
- Generating a new personal recovery key invalidates the previous one. Confirm the user records the new key immediately, outside this Mac, before the old one is discarded.
- Turning FileVault off starts a decryption pass that takes time and needs power and free space; it is a deliberate decision, not a diagnostic step.
- Erase-and-reinstall destroys the data. It requires a separate, explicit confirmation naming the volume, and a verified backup restore beforehand.

For a Mac going to service, prepare a written handover note: FileVault state, whether an unlock credential is being provided, and whether the shop is authorised to erase. Do not put the key itself in the note or the ticket.

### 6. Handle Recovery-mode work as a separate phase

Recovery mode is entered by a vendor-documented startup sequence that differs between Apple silicon and Intel. In Recovery there may be no agent, no network and no automation, so produce a printed or separately stored checklist first: the exact steps, the volume identifiers, what to verify at each point, and the stop conditions.

Disk Utility First Aid on the container and volume is a read-and-repair operation on filesystem metadata, not a decryption tool, and it cannot recover a lost key.

## Verification

Confirm FileVault state and the list of unlock-enabled users match the intended configuration. Confirm the recovery key currently on file is the valid one using the supported validation path, entered by the user on the machine and never captured into a report. Reboot and confirm the intended credential unlocks the volume at the pre-boot screen. Confirm MDM or institutional escrow reflects the new key where applicable, that the backup still runs and verifies after the change, and that the user has a recorded copy of the current key stored off this Mac.

## Caveats

- A lost recovery key with no other unlock path means permanent data loss. There is no vendor bypass.
- FileVault off does not mean data at rest is unprotected on Apple silicon or T2 Macs, and FileVault on does not protect a running, unlocked session.
- Storage removed from an Apple silicon or T2 Mac is not readable elsewhere, so component-level data recovery expectations must be reset early.
- A password change made through MDM or a directory service does not always propagate to the pre-boot unlock.
- Escrow to MDM depends on the organisation's configuration and retention; "we have MDM" is not proof the key was captured.
- Encryption or decryption in progress can be interrupted by power loss; keep the Mac on AC power.
- APFS snapshots share the disk they protect and disappear with it.
- Erase All Content and Settings, Recovery re-provisioning and enrolment changes can require network access and the organisation's approval on managed Macs.

## Escalation

Escalate to the organisation's IT or Mac administration owner for any enrolled or organisation-owned Mac, and before any erase where escrow is uncertain. Escalate to Apple or an authorised provider for Secure Enclave, activation-lock or firmware-password issues, and for hardware service on an encrypted Mac. Provide: model and architecture, macOS version, FileVault and enrolment state, unlock-enabled users, escrow answer from the intake question, backup verification result, the exact failure symptom with timestamps, and the planned change with its rollback. Do not include the recovery key or any password in the escalation.

## Tools referenced

- `mac_filevault_status`
- `mac_system_info`
- `mac_disk_usage`
- `mac_read_log`
- `ui_user_question`
- `options`
