---
name: storage-health-smart
description: Read SMART and NVMe health counters on Windows, macOS, and Linux to judge whether a drive is failing
platform: all
category: hardware-crash-diagnostics
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Storage Health And SMART Review

## When to activate

User reports clicking or grinding noises, files that fail to open, repeated filesystem repairs, stalls that freeze the whole system, slow boot with disk activity, a vendor tool warning, or asks whether a drive should be replaced. Also activate before any partition, imaging, reinstall or data-recovery work, so a dying drive is identified before it is stressed further.

## Quick check

Record device model, serial, bus type, capacity, rotational or solid state, firmware version, and how long the device has been in service. Determine whether the drive is internal, in a USB enclosure, behind a RAID or hardware controller, or a virtual disk.

Ask the user one question first: **is there a current, verified backup?** If not, backup comes before diagnosis. A failing drive can die during the very commands used to inspect it.

## Standard diagnostic path

### 1. Inventory the device

Run `win_storage_health` and `win_volume_inventory` on Windows, `mac_storage_health` on macOS, and `linux_storage_health` with `linux_disk_usage` on Linux.

Map every physical device to its volumes before reading counters, so a later "the disk is failing" statement names a specific device rather than a drive letter or mount point.

### 2. Read the health counters

The overall SMART verdict is a single pass/fail bit and is deliberately conservative. Read the individual counters, not only the verdict.

For SATA and SAS devices the attributes that actually predict failure:

| Attribute | Meaning | Interpretation |
|---|---|---|
| 05 Reallocated_Sector_Ct | Sectors remapped to spares | Any non-zero value that grows over days is a replace signal |
| 197 Current_Pending_Sector | Sectors queued for remap | Non-zero means unreadable data right now |
| 198 Offline_Uncorrectable | Sectors that could not be recovered | Non-zero means confirmed data loss |
| 187 Reported_Uncorrect | Errors the drive could not correct | Correlates strongly with imminent failure |
| 188 Command_Timeout | Commands that timed out | High values often mean cable, power or controller, not the platter |
| 199 UDMA_CRC_Error_Count | Link-level errors | Almost always cable, connector or enclosure |
| 09 Power_On_Hours / 04 Start_Stop_Count | Service life | Context for wear, not a fault by itself |

For NVMe devices read `critical_warning`, `percentage_used`, `available_spare` and `available_spare_threshold`, `media_errors`, `num_err_log_entries`, `unsafe_shutdowns`, and `temperature`.

Interpretation rules:

- `percentage_used` above 100 means the vendor endurance rating is exhausted; the drive may still work but is out of spec.
- `available_spare` falling toward its threshold is a replace signal.
- `media_errors` greater than zero means uncorrectable data errors have already occurred.
- `unsafe_shutdowns` alone usually reflects power loss habits, not drive health.

Vendor-specific and normalized-versus-raw attribute encodings differ per model. Use `knowledge_search` to look up the vendor's published attribute table before interpreting an unfamiliar ID, and say "unknown encoding" instead of guessing.

### 3. Separate the drive from its path

A drive reachable only through a USB bridge, dock, hub or RAID controller frequently reports no SMART data, or reports the bridge's data instead of the disk's. Before concluding "no SMART support":

- reseat or replace the cable and use a rear or direct port;
- test the same device on another host or enclosure when available;
- on Linux, retry with an explicit device type such as SATA-over-USB translation.

High CRC or command-timeout counters with clean reallocation counters point at the cable, connector, dock or power delivery. Replacing a healthy drive because of a bad cable is a common and expensive misdiagnosis.

### 4. Correlate with system evidence

Check the operating system's own view of device errors: Windows system log disk and storage provider events, macOS unified log I/O errors, and Linux kernel messages for resets, medium errors and controller timeouts.

Repeated device resets, `I/O error`, `medium error`, `link reset` or filesystem remounted-read-only events raise the severity even when SMART still says pass. Use `shell_run` only for the specific read-only command mapped in the platform tool reference.

### 5. Decide and act in the right order

Rank the outcome into one of four states and act accordingly.

- **Confirmed failing** (growing reallocations, pending or uncorrectable sectors, NVMe media errors, critical warning): stop routine work. Copy data off, largest-value first, then replace the device. Do not defragment, do not run long self tests, do not write benchmarks.
- **Wear limit reached** (endurance exhausted, spare area low, no data errors yet): plan replacement on a schedule, keep backups current, and record the counters as a baseline.
- **Link or enclosure fault** (CRC and timeouts only): fix the physical path first, then re-read counters.
- **Healthy** (clean counters, symptoms unexplained): the storage device is not the cause; route to the platform performance flow. On Windows use `windows-performance-forensics`, on macOS use `performance-forensics`, on Linux use `linux-performance-forensics`.

When data must be preserved from a failing device, imaging comes before repair attempts. On Windows route to `windows-data-recovery-triage`.

## Verification

Re-read the same counters after the physical path is corrected or the device is replaced, and record the new values next to the old ones. Confirm that the operating system logs no longer show device resets or medium errors during the same workload, that the affected files open, and that a backup verification pass succeeds. For a replaced device, confirm firmware, capacity and bus speed match the expected specification.

## Caveats

- A SMART verdict of pass does not mean the drive is healthy; many drives fail with a passing verdict.
- Self tests (`short`, `long`, `conveyance`) change device state and load a weak drive. They are not part of this read-only flow, and are never appropriate before data is safe.
- Reallocated-sector counts on SSDs and HDDs are not comparable; SSD wear is expressed through spare area and endurance, not platter remapping.
- Apple silicon and T2 Mac internal storage is not user replaceable, and reports through the NVMe profile rather than a removable-device model.
- Virtual disks, hardware RAID members and network volumes usually expose no per-device health data; report the controller or hypervisor as the correct source of truth.
- Temperature spikes can throttle an otherwise healthy drive. Sustained temperature is a cooling problem, not a health verdict.

## Escalation

Escalate to hardware service or the storage owner with: device model, serial, firmware, bus type, full counter dump with timestamps, growth over at least two samples, correlated operating-system error events, backup status, and whether the device is still under warranty. For RAID, SAN or hypervisor storage, escalate to the platform owner rather than pulling a member disk. If the drive holds the only copy of important data and shows uncorrectable errors, escalate to a professional recovery service before further power cycles.

## Tools referenced

- `win_storage_health`
- `win_volume_inventory`
- `mac_storage_health`
- `linux_storage_health`
- `linux_disk_usage`
- `knowledge_search`
- `shell_run`
