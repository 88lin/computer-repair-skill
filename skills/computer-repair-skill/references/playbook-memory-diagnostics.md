---
name: memory-diagnostics
description: Separate real RAM faults from memory pressure and driver bugs across Windows, macOS and Linux before replacing modules
platform: all
category: hardware-crash-diagnostics
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Memory Diagnostics

## When to activate

User reports random crashes with different error messages each time, corrupted files or archives that fail checksums, applications that die without a pattern, freezes during memory-heavy work, a machine that became unstable after a memory upgrade, or asks whether the RAM is faulty.

Also activate when a crash triage flow points at memory as a candidate subsystem.

## Quick check

Run `win_hardware_inventory` on Windows, `mac_hardware_inventory` on macOS, and `linux_hardware_inventory` with `linux_memory_report` on Linux.

Record installed capacity, module count and per-slot placement, part numbers, rated versus configured speed, whether the memory is ECC, and whether the platform even allows module changes. Then ask what changed: a memory upgrade, a firmware update, an XMP/EXPO profile, a new dock, a move to a different desk, or nothing.

## Standard diagnostic path

### 1. Rule out memory pressure first

Most "out of memory" and "the RAM is bad" reports are capacity and paging behaviour, not defective hardware. A defective module corrupts data; insufficient memory makes things slow.

Distinguish them:

- Symptoms scale with workload size and disappear when the workload shrinks: pressure, not a fault.
- Symptoms are random, hit different applications, and produce different error signatures: possible fault.
- Files or archives are corrupted after being written: strong fault signal.
- A single application leaks steadily and recovers on restart: application bug.

Use `win_process_list` on Windows, and the platform performance flow when pressure is confirmed — `windows-performance-forensics` on Windows, `performance-forensics` on macOS, `linux-performance-forensics` on Linux.

### 2. Collect the platform's existing error records

Machines already log memory errors; read them before running any test.

- Windows: `win_memory_report` for WHEA-Logger records and any previously stored Windows Memory Diagnostic result events, plus memory counters for available bytes, committed bytes and page-file usage.
- macOS: `mac_hardware_inventory` for the memory profile, plus memory pressure and swap statistics. Apple silicon reports unified memory without slot detail.
- Linux: `linux_memory_report` for `/proc/meminfo`, DIMM inventory, and kernel EDAC or MCE records. On systems running the RAS daemon, the error summary is the best available evidence.

Any corrected-error counter that is climbing identifies the failing module by rank and channel on ECC systems, which is far more precise than any user-space test. Uncorrected memory errors are a replace signal on their own; no further testing is required to justify service.

Use `linux_read_log` for the kernel ring buffer and journal excerpts, and `shell_run` only for the specific read-only commands mapped in the platform tool reference.

### 3. Check configuration before hardware

A stable module can misbehave in an unstable configuration.

- Rated versus running speed: memory running above its rated JEDEC speed via XMP/EXPO is overclocked. Returning to stock is a diagnostic step, not a downgrade.
- Mixed kits: different part numbers, capacities, ranks or timings in one system are a common instability cause even when each module is individually fine.
- Slot population: check the board's documented channel order. A wrong slot pair can halve bandwidth or prevent boot.
- Firmware: a BIOS or UEFI version predating a memory compatibility fix can destabilise a supported kit.
- Voltage and thermals: an undervolted or hot system fails in memory-shaped ways.

### 4. Test with the right tool for the platform

Testing is not free: a full pass takes hours, and userspace testers can only cover memory they are allowed to allocate.

- Windows: the built-in Windows Memory Diagnostic reboots the machine into a pre-boot test. That is a state change requiring a reboot and user consent; schedule it deliberately, not casually, and read the result event afterwards.
- macOS: Apple Diagnostics runs from firmware using the vendor-documented startup key sequence for that model. There is no supported in-session hardware RAM test.
- Linux: a bootable memory tester covers physical memory properly. A userspace tester can only exercise allocatable memory and cannot test what the kernel occupies, so a clean userspace pass does not clear the module.

Any test that reports errors is conclusive. A test that reports no errors is not — intermittent faults commonly need multiple passes or heat to appear.

### 5. Isolate by subtraction

When the platform allows it and multiple modules are installed, isolation beats testing.

1. Record the current configuration, including which module is in which slot.
2. Run with a single module in the primary documented slot.
3. Reproduce the user's workload for a defined period.
4. Rotate modules and slots one variable at a time, keeping notes.

This separates a bad module from a bad slot or a bad memory controller. Follow the hardware-safety flow for the physical work; on Windows laptops route to `windows-hardware-maintenance-safety` before opening the chassis.

### 6. Report a decision, not a suspicion

Close with one of these positions and the evidence for it:

- **Confirmed fault**: uncorrected errors, reproducible test failures, or errors that follow one module across slots. Replace, matching the documented specification.
- **Confirmed configuration problem**: instability that disappears at stock JEDEC settings or in the documented slot layout.
- **Capacity limit**: the workload legitimately exceeds installed memory. Quantify how much is needed rather than saying "add more RAM".
- **Not memory**: evidence points elsewhere. Name the next subsystem and route to it.
- **Not user serviceable**: soldered or on-package memory. The remedy is vendor service or a different machine, and no amount of testing changes that.

## Verification

After a module change or configuration change, confirm the system reports the expected total capacity, per-slot layout, and speed. Re-run the user's original failing workload plus one memory-heavy task, and confirm no new WHEA, EDAC, MCE or kernel memory errors appear. Re-check any file that was previously corrupted by regenerating and comparing it. State the observation window used.

## Caveats

- ECC systems correct single-bit errors silently; a clean user experience can coexist with a failing module. Only the counters reveal it.
- Non-ECC systems have no error reporting at all, so an absence of logged errors proves nothing.
- A single-bit error event after a power event or cosmic-ray-class one-off does not justify replacement; growth over time does.
- Reported memory speed frequently differs from the module's label because the platform runs a JEDEC profile by default.
- Firmware often reserves memory, so total usable capacity is legitimately lower than installed capacity, especially with integrated graphics.
- Apple silicon, many thin laptops and most tablets have non-replaceable memory; do not propose an upgrade path that does not exist for that model.
- Memory testers stress the same components that a failing power supply also stresses; unstable power can produce test failures with healthy modules.

## Escalation

Escalate to hardware service with: platform model and firmware version, installed module inventory including part numbers and slot placement, ECC status, exact error records with timestamps and growth over at least two samples, test tool and number of passes, isolation results per module and per slot, and the workload used for verification. Escalate to the vendor rather than swapping parts when memory is soldered, when errors persist with a single known-good module, or when the memory controller or CPU is implicated.

## Tools referenced

- `win_hardware_inventory`
- `win_memory_report`
- `win_process_list`
- `mac_hardware_inventory`
- `linux_hardware_inventory`
- `linux_memory_report`
- `linux_read_log`
- `shell_run`
