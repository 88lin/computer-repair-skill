---
name: thermal-battery-health
description: Diagnose overheating, fan noise, thermal throttling, battery wear and sleep-drain on Windows, macOS and Linux
platform: all
category: hardware-crash-diagnostics
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Thermal And Battery Health

## When to activate

User reports a hot chassis, constant or loud fans, performance that collapses after a few minutes, shutdowns under load, a battery that drains quickly or while asleep, a swollen case or trackpad that no longer clicks, a battery-service warning, or a laptop that only works while plugged in.

## Quick check

Run `win_power_report` on Windows, `mac_power_report` on macOS, and `linux_thermal_status` on Linux.

Record model, age, AC or battery state, current charge, design capacity versus full-charge capacity, cycle count, reported battery condition, current temperatures, fan behaviour, and the ambient conditions. Ask where the machine sits: a bed, sofa, closed drawer, docking station in a cabinet, or a desk.

**Safety gate first.** A swollen battery, a deformed chassis, a trackpad pushed upward, a case that no longer closes, hissing, or a burning smell means stop. Do not charge, do not puncture, do not continue diagnostics. Move to escalation immediately.

## Standard diagnostic path

### 1. Separate the four failure shapes

These look similar to users and have different causes:

- **Heat with high load** — something is running. Software problem until proven otherwise.
- **Heat with no load** — cooling path, firmware, or a stuck sensor/fan controller.
- **Throttling without heat** — power delivery, charger wattage, firmware limit, or battery unable to supply peak current.
- **Battery drain** — wear, background wake activity, or a device blocking sleep.

Identify which one applies before collecting more data.

### 2. Attribute the heat to work

Sample the top consumers twice, a few minutes apart, with `win_process_list` on Windows, `mac_process_list` on macOS, and `linux_process_list` on Linux.

Common legitimate causes that users mistake for faults: search indexing after a large copy, a backup or cloud-sync catch-up pass, an operating-system update installing in the background, antivirus scans, a browser tab running video or crypto-adjacent scripts, and a game or model workload behaving exactly as designed.

If a specific process explains the heat, this is a performance problem, not a hardware fault. Route to the platform performance flow: `windows-performance-forensics` on Windows, `performance-forensics` on macOS, `linux-performance-forensics` on Linux.

### 3. Read temperature and throttling evidence

Read the platform's own sensors rather than a third-party utility where possible.

- Windows: platform temperature exposure is inconsistent and often unavailable without vendor tooling. Report what is available and say what is missing rather than inventing numbers. Processor performance counters show sustained clock reduction, which is throttling evidence independent of temperature.
- macOS: the thermal log records thermal pressure and CPU speed limits. Battery condition and cycle count come from the power profile.
- Linux: thermal zones and hardware monitoring provide per-sensor temperatures in millidegrees; per-core throttle counters and current frequency show whether limits are being hit.

Interpretation rules:

- Brief peaks at high temperature under load are normal design behaviour, not a fault.
- A sustained ceiling with reduced clocks is thermal throttling.
- Clock reduction without a temperature ceiling points at power limits, a weak charger, or battery current limits.
- A single sensor reading far outside the others is more likely a sensor or reporting bug than a real hotspot.

### 4. Inspect the cooling path physically

Verify airflow before proposing service. Check intake and exhaust for dust and lint, whether the machine sits on soft surfaces, whether a case or stand blocks vents, whether fans spin and are audible, and whether the machine is inside a closed cabinet or dock enclosure.

For a laptop that needs opening, follow the safety flow — on Windows machines route to `windows-hardware-maintenance-safety` for discharge, ESD, dust removal and reassembly rules. Thermal paste replacement is a service action with a real risk of damage; it is justified by evidence (sustained throttling on a clean cooling path, machine age), not by habit.

### 5. Assess battery wear honestly

Compute wear from design capacity versus current full-charge capacity, and read cycle count and the platform's own condition verdict. Then interpret:

- High wear plus high cycles: normal ageing. Replacement is a choice, not an emergency.
- Low cycles with high wear: heat exposure, permanent full charge on AC, or a defective cell. Warranty candidate.
- Platform reports "replace" or "service": trust the platform verdict and pass it through.
- Capacity fine, runtime poor: this is drain, not wear. Continue to the next step.
- Reported capacity jumping around: the gauge may need a full charge-discharge cycle to recalibrate before any conclusion.

### 6. Diagnose drain and sleep behaviour

Distinguish drain while in use from drain while asleep.

- Check which sleep states the platform actually supports and which one it uses. Modern standby behaves like a very low-power running state, so background network activity legitimately consumes power.
- List active power assertions or wake-blocking requests: audio streams, open network shares, downloads, a connected display, an application preventing sleep, or a peripheral rearmed for wake.
- Check wake-armed devices: a mouse, keyboard, network adapter or dock can wake the machine repeatedly overnight.
- On battery, check the charge limit setting. Many vendors cap charging at 80 percent by design; a user reading that as a fault needs an explanation, not a repair.

Use `shell_run` only for the specific read-only commands mapped in the platform tool reference.

### 7. Act on the narrowest cause

Show the plan and get approval. One change at a time.

- Runaway process or indexing backlog: address that workload, do not disable the whole service.
- Blocked airflow: clean and reposition. Measure temperatures before and after.
- Wake-blocking device or application: change that single setting and record the original value.
- Charger or dock underpowered: verify the rated wattage against the vendor specification and test with a compliant supply.
- Firmware or vendor power-management updates: apply from the vendor's own source, on AC power, with user confirmation.
- Worn battery: quote wear, cycles and condition, then let the user decide on service.

Do not disable thermal management, remove power limits, or install "fan control" utilities as a fix for a cooling fault. Do not suggest running a laptop with the bottom cover removed.

## Verification

Re-run the workload that produced the complaint and compare the same measurements: sustained temperature, clock behaviour, fan state, and time to throttle. For a battery issue, record charge percentage at the start and end of a defined idle or sleep period and compare with the pre-change measurement. Confirm the platform's own condition verdict and cycle count after any battery replacement, and confirm the reported design capacity matches the replacement part.

## Caveats

- Temperature exposure varies enormously by platform, model and privilege level. Missing sensors are a reporting limitation, not a healthy result.
- Fan noise is not proportional to a fault; some models are simply loud under load.
- Vendor charge limits, adaptive charging and long-term-standby behaviour reduce reported capacity or runtime by design.
- Battery gauges drift; a single reading after a partial cycle can be misleading.
- Ambient temperature, altitude and enclosed spaces materially change results. Record conditions with measurements.
- Third-party monitoring utilities frequently misread sensors or report the wrong die; prefer platform sources and label anything else as unverified.
- Lithium batteries are a fire and injury risk when damaged. There is no safe do-it-yourself remedy for a swollen cell.

## Escalation

Escalate to hardware service immediately for a swollen or deformed battery, a chassis that no longer closes, burning smells, liquid exposure, or shutdowns under load with a clean cooling path. Escalate with: model and firmware version, age, design versus full-charge capacity, cycle count, platform condition verdict, temperature and clock samples with timestamps and ambient conditions, cooling-path inspection notes, the workload used, charger rating, and the wake or assertion evidence for a drain complaint. For a machine under warranty, escalate before opening the chassis.

## Tools referenced

- `win_power_report`
- `win_process_list`
- `mac_power_report`
- `mac_process_list`
- `linux_thermal_status`
- `linux_process_list`
- `shell_run`
