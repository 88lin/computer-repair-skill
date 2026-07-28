---
name: linux-boot-failure-triage
description: Triage Linux boot failures stage by stage, from firmware and bootloader to initramfs, root mount and failed units
platform: linux
category: macos-linux-repair
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Linux Boot Failure Triage

## When to activate

A Linux host does not reach a usable state: firmware shows no boot device, the bootloader menu never appears, the kernel panics, boot stops at an initramfs or emergency shell, the root filesystem cannot be mounted, the graphical session never starts, boot became very slow after an update, or the host boots but with failed units. Also activate after a kernel or firmware update changed boot behaviour, or after a disk was cloned, resized or moved to different hardware.

## Quick check

Establish the failure stage before touching anything, because each stage has a different fix and the wrong one wastes a maintenance window.

Ask what the last screen shown is, and place it in one of six stages:

1. **Firmware** — vendor logo only, "no bootable device", or the disk is missing from the firmware boot menu.
2. **Bootloader** — firmware hands over but GRUB or systemd-boot does not appear, or it appears and cannot load the kernel.
3. **Kernel** — kernel messages start and then stop with a panic or a hang.
4. **initramfs** — a `(initramfs)` or `dracut` prompt, or a timeout waiting for a root or swap device.
5. **Early userspace** — systemd starts, units run, and boot stalls or drops to an emergency or rescue shell.
6. **Session** — multi-user target is reached, but the display manager or graphical session fails.

Also record what changed immediately before the failure: a kernel or firmware update, a disk change, an `/etc/fstab` edit, an encryption change, a graphics driver install, or nothing at all. A boot failure that starts right after a package upgrade is usually a rollback question, not a repair question.

## Standard diagnostic path

### 1. Collect the surviving evidence

If the host still reaches a shell, even a rescue or emergency shell, run `linux_system_summary` and `linux_boot_status` and record: distribution and version, running kernel and all installed kernels, firmware mode (UEFI or legacy BIOS), Secure Boot state, init system, whether the root filesystem is encrypted, and which units failed.

If the host does not reach a shell at all, boot the matching distribution live or installer medium and work from there. Do not chroot yet; read first.

### 2. Read the previous boot from the journal

Use `linux_read_log` against the previous boot rather than the current one — that is where the failure is recorded. List the available boots, then read the failed boot at error priority, and separately read the kernel ring buffer for that boot.

What to look for, in order: the last kernel message before the stop, storage or filesystem errors, a device timeout naming a UUID, `Failed to start` lines with the unit name, ordering-cycle warnings, out-of-memory kills during early boot, and firmware or hardware errors (MCE, PCIe, thermal).

If the journal is not persistent, the previous boot will be missing. Enabling persistent storage is a state change; treat it as a follow-up action for recurring failures, not part of this read-only pass.

### 3. Firmware and bootloader stage

For stage 1 and 2 failures, confirm from the firmware setup screen that the disk is detected and that the expected boot entry exists. Then verify the boot chain from the running or live system:

- the EFI system partition exists, is mounted at the expected mount point, has a FAT filesystem and enough free space, and contains the distribution's loader directory;
- the firmware boot entries point at loaders that still exist on disk;
- Secure Boot state matches how the kernel and any out-of-tree modules were signed — a host that stops booting only after a graphics or virtualisation module was built locally is usually a signing problem, not a disk problem;
- the boot order was not reset to network or removable media by a firmware update.

Common outcomes: a missing or wrong-order firmware entry, an EFI partition full of old kernels, an entry that survived a disk clone but points at the old disk's identifiers, or a bootloader that was never reinstalled after the ESP was reformatted.

### 4. initramfs and root device stage

For stage 4, the question is almost always identity: the initramfs is looking for a device that does not exist under that name.

- Compare the root and swap identifiers in the bootloader entry and in `/etc/fstab` against the identifiers actually present on the disks. Prefer UUID over kernel device names, which reorder freely.
- Check whether the initramfs contains the modules for this storage controller, RAID or encryption stack. A host that boots an older kernel but not the newest usually has an incomplete initramfs for the new kernel.
- For encrypted roots, confirm the mapping name and key source resolve; a passphrase prompt that never appears is different from one that is rejected.
- After hardware changes, expect missing controller modules; after cloning, expect duplicate filesystem UUIDs, which is a genuine ambiguity the kernel cannot resolve for you.

Regenerating the initramfs or reinstalling the bootloader fixes many of these, but both rewrite the boot chain. Confirm the diagnosis first, keep the known-good kernel entry available, and record exactly what you ran.

### 5. Filesystem and space stage

A full or read-only filesystem produces failures that look like anything but a space problem. Run `linux_disk_usage` and check free space and free inodes on the root, `/var`, `/boot` and the EFI partition separately.

A full `/boot` is a classic cause of "the new kernel does not boot": the image was written incompletely. A full root leaves systemd unable to write runtime state, and services fail with unrelated-looking errors. Exhausted inodes with plenty of free bytes look identical to users and different to tools. For the cleanup itself, follow `linux-disk-space-recovery` rather than deleting by hand.

If the filesystem was mounted read-only after an error, read the reason from the journal before remounting. Check filesystems in read-only mode only; a repair pass that rewrites metadata is a data-risk operation and belongs in step 7 with explicit consent and a backup.

### 6. Userspace and session stage

For stage 5 and 6, work from the failed units. For each failed unit, read its effective definition and its journal entries, and separate three cases: a unit waiting on a device or network that will never arrive, a unit failing on its own configuration, and a unit failing because a dependency failed earlier.

Boot that is merely slow is a different question: read the per-unit boot timing and look for the one long-running job — commonly a network-wait unit on a host with no cable, a mount for an absent remote filesystem, or a service blocking on a name resolution timeout.

For graphical failures, check the display manager's unit and log, whether the graphics driver module loaded, and whether the failure followed a driver or kernel change. A host that boots to a text console with working SSH is fully diagnosable remotely; keep it in that state rather than rebooting repeatedly.

Use `linux_crash_report_list` to check for core dumps and kernel crash reports that match the failure window. Record the timestamps and the crashing executable; treat dump contents as sensitive and do not copy them off the host or upload them to third-party analysis sites.

### 7. Decide and act, one change at a time

Rank candidate actions by reversibility, and take the least invasive one that addresses the evidence:

1. Boot a previously working kernel from the bootloader menu. Reversible, and it immediately separates "kernel or module regression" from everything else.
2. Fix identifiers in the bootloader entry or `/etc/fstab` to match reality.
3. Regenerate the initramfs for the affected kernel.
4. Reinstall the bootloader to the correct ESP and restore the firmware boot entry.
5. Roll back the specific package or kernel that correlates with the failure.
6. Repair the filesystem in write mode, only after a block-level backup and explicit consent.

Copy any configuration file to a dated backup before editing it. If several candidates look plausible, apply one, reboot, and re-read the journal; batching changes destroys the signal you need. Never disable SELinux, AppArmor, Secure Boot, auditing or unattended security updates as a shortcut to a successful boot — if one of them is genuinely implicated, say so explicitly and propose a scoped fix.

If the evidence points at an unexpected unit, service or timer rather than the boot chain itself, continue with `linux-persistence-audit` instead of editing units here.

## Verification

Reboot cleanly at least twice, including one cold boot, and confirm the host reaches its normal target both times without manual intervention. Then confirm: no failed units, the expected kernel is running, the root and all `/etc/fstab` entries mounted as intended, boot time back in its normal range, the graphical session or display manager reachable if in scope, and remote access working before you leave. Re-read the current boot's journal at error priority and confirm the original messages are gone rather than merely later. Verify the previous known-good kernel is still installed and selectable, so the host retains a fallback.

## Caveats

- A boot that succeeds once may be luck; a timing-dependent device wait can pass on a warm boot and fail on a cold one.
- Regenerating the initramfs or reinstalling the bootloader on the wrong disk or wrong ESP can make a working operating system unbootable — confirm the target device explicitly on multi-disk and dual-boot hosts.
- Filesystem repair in write mode can lose data, especially on Btrfs, where `--repair` is a last resort and can worsen damage.
- Duplicate filesystem UUIDs after cloning cause non-deterministic mounts; the fix is to change one UUID, not to retry the boot.
- Without persistent journal storage there is no record of the failed boot; the first recurrence may be the only chance to capture it live.
- Some errors printed during boot are benign and permanent on that hardware; correlate with the failure window instead of treating every red line as the cause.
- Firmware updates can reset boot order and Secure Boot settings silently, so re-check them after any firmware change.
- Container, WSL and cloud instances do not have a local boot chain in this sense; there the equivalent question belongs to the host or the image build.

## Escalation

Escalate to the hardware vendor when the firmware cannot see the disk, when SMART or controller errors accompany the failure, or when the same failure follows the disk to another machine. Escalate to the platform or host owner for managed, production and shared systems, and for cloud or virtualised guests where the boot chain is built by an image pipeline. Escalate to security if boot artefacts changed without a corresponding package or administrator action, if Secure Boot was disabled by someone unknown, or if the bootloader or initramfs no longer matches what the package manager installed. Hand over: distribution and kernel versions, firmware mode and Secure Boot state, the identified failure stage, journal excerpts from the failed boot with timestamps, the storage and identifier layout, disk and inode usage, the list of failed units, every change made with its backup location, and whether a known-good kernel still boots.

## Tools referenced

- `linux_boot_status`
- `linux_crash_report_list`
- `linux_read_log`
- `linux_system_summary`
- `linux_disk_usage`
- `shell_run`
