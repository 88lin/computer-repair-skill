---
name: windows-performance-forensics
description: Diagnose Windows slowness, CPU saturation, memory pressure, disk bottlenecks, startup load, and application hangs
platform: windows
category: health-performance-storage-backup
last_reviewed: 2026-07-26
author: computer-repair-skill-maintainers
source: local
---

# Windows Performance Forensics

## When to activate

User reports a slow Windows machine, high CPU, low memory, heavy disk use, fan noise, freezes, delayed startup, or an unresponsive application.

## Quick check

Run `win_system_info`, `win_process_list`, and `win_disk_usage`. Record uptime, total and available memory, free disk space, top CPU processes, top working-set processes, and the time of the complaint.

Take at least two short samples before naming a transient process as the cause.

## Standard diagnostic path

### 1. Establish system pressure

Query:

```powershell
Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'"
Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk -Filter "Name='_Total'"
```

Capture processor utilization, available MB, committed bytes, pages per second, disk time, queue length, and transfer rate. Interpret samples together; one high value is not a root cause.

### 2. Identify responsible processes

Use `Win32_PerfFormattedData_PerfProc_Process` for current CPU and IO rates, and `Get-Process` for working set, handles, threads, start time, and executable path.

- High CPU: verify the same PID remains high across samples.
- High memory: distinguish working set from committed memory and check system-wide available memory.
- High IO: identify read/write rate and which volume is saturated.
- Many instances: aggregate by executable before concluding one process dominates.

### 3. Check disk and paging

Use `win_disk_usage` and confirm the system volume has operational headroom. Check paging data from `Win32_PageFileUsage` and memory performance data.

Low free space can amplify update, paging, browser, and application problems. Do not start cleanup until `windows-disk-space-recovery` identifies safe targets.

### 4. Check startup and background services

Run `win_startup_programs` and inspect scheduled tasks or services only when startup or persistent background load matches the symptom.

Do not disable security, backup, management, accessibility, or synchronization software based only on resource size. Establish ownership and purpose first.

### 5. Correlate with events

Query System and Application events around the complaint time for disk, storage, display driver, application hang, resource exhaustion, WHEA, and unexpected shutdown events.

Use the exact timestamp and provider. Avoid treating unrelated historical errors as current causes.

### 6. Apply the narrow repair

Show a plan and obtain approval.

- Runaway user application: save work, attempt graceful close, then terminate the confirmed PID if needed.
- Broken background service: restart only the identified service and verify dependencies.
- Startup overload: disable one confirmed non-essential startup entry with a recorded rollback.
- Low disk: activate `windows-disk-space-recovery`.
- Driver or update regression: collect current version and install date before proposing rollback or update.

Avoid generic registry cleaners, broad cache wipes, blanket service disabling, and memory optimizer utilities.

## Verification

Repeat the same performance samples and the user's original workflow. Compare CPU, available memory, disk queue, process identity, startup time, or application response before and after.

## Caveats

- `Get-Process CPU` is cumulative CPU time, not instantaneous percent.
- Antimalware, indexing, updates, and synchronization can be temporarily busy for legitimate reasons.
- Virtual machines, WSL, Docker, and browsers distribute work across many processes.
- Thermal throttling requires hardware or vendor telemetry beyond process CPU.

## Key signals

- High CPU from one stable PID -> application or service path.
- Low available memory plus paging -> memory pressure.
- High disk queue with modest throughput -> latency, failing storage, or small random IO.
- Slow only after boot -> startup tasks, updates, or profile initialization.
- Hangs with display-driver events -> graphics driver or GPU path.

## Tools referenced

- `win_system_info`
- `win_process_list`
- `win_disk_usage`
- `win_startup_programs`
- `win_service_list`
- `win_read_log`
- `win_kill_process`
- `shell_run`

## Escalation

Escalate with timestamped samples, affected PID and executable path, event providers/IDs, disk health evidence, driver versions, and a reproducible workflow. Hardware errors or repeated WHEA/storage events require vendor diagnostics and backup review.
