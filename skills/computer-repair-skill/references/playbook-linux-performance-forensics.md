---
name: linux-performance-forensics
description: Diagnose Linux load, CPU, memory pressure, swapping, IO waits, disk bottlenecks, cgroup limits, and process hangs
platform: linux
last_reviewed: 2026-07-26
author: computer-repair-skill-maintainers
source: local
---

# Linux Performance Forensics

## When to activate
User reports a slow Linux host, high load, CPU saturation, memory pressure, swapping, IO waits, container throttling, service latency, or process hangs.

## Quick check
Run `linux_system_info`, `linux_process_list`, and `linux_disk_usage`. Record CPU count, load average, available memory, swap, filesystem and inode headroom, and top processes.

Identify whether the workload runs on bare metal, a VM, a container, WSL, or a cgroup-limited service.

## Standard diagnostic path

### 1. Interpret load and CPU
Run:
```
uptime
nproc
vmstat 1 5
```

Compare load average with available CPUs. Use `vmstat` to separate runnable CPU work (`r`), blocked tasks (`b`), idle CPU, IO wait, and steal time.

- High user/system CPU: identify processes and threads.
- High IO wait: continue to storage and blocked-task analysis.
- High steal: suspect hypervisor contention.
- High load with low CPU: inspect uninterruptible tasks or cgroup throttling.

### 2. Identify responsible processes
Run `linux_process_list` twice and inspect stable offenders. Use per-thread views only for the selected PID.

When available, use `pidstat 1 5` for CPU, memory faults, and IO rates. Record full executable path and service/container ownership before proposing changes.

### 3. Check memory pressure
Run:
```
free -h
cat /proc/meminfo
cat /proc/pressure/memory
```

Use `MemAvailable`, swap activity from `vmstat`, and PSI together. Linux page cache is reclaimable; low `MemFree` alone does not prove pressure.

Check recent OOM events with `journalctl -k` or `dmesg` access. Do not raise limits before identifying the growth source.

### 4. Check storage and filesystems
Run `df -hT`, `df -i`, and inspect `/proc/pressure/io`. When available, use `iostat -xz 1 5` for device latency, utilization, and queue data.

Low free space or inodes routes to `linux-disk-space-recovery`. Repeated device errors, resets, or filesystem warnings route to backup and hardware escalation.

### 5. Check cgroups and containers
Read `/proc/self/cgroup`, systemd unit properties, or container limits for CPU quota, memory max, current usage, throttling, and OOM count.

Compare host pressure with the affected cgroup. A healthy host can still throttle one container or service.

### 6. Correlate with logs and time
Query the affected service and kernel logs around the complaint time. Check scheduled jobs, package updates, backup, indexing, log rotation, and container restarts.

### 7. Apply the narrow repair
Show a plan and obtain approval.
- Runaway process: request graceful service/application shutdown before a signal.
- Service leak: restart the confirmed unit and preserve relevant logs.
- Mis-sized cgroup: change one limit with its previous value recorded.
- Low disk/inodes: activate `linux-disk-space-recovery`.
- Scheduled contention: adjust only the identified job after confirming ownership.

Avoid dropping caches, disabling swap, broad `killall`, and random sysctl tuning as generic speed fixes.

## Verification
Repeat the same load, `vmstat`, PSI, process, memory, and IO samples. Re-run the user's workload and compare latency or throughput using the same conditions.

## Caveats
- Load includes runnable and uninterruptible tasks, not only CPU use.
- `buff/cache` is not automatically wasted memory.
- Container-visible CPU and memory may differ from host totals.
- `/proc/pressure` and some performance tools may be unavailable on older kernels or minimal images.

## Key signals
- High `r`, low idle -> CPU saturation.
- High `b` or IO PSI -> blocked storage path.
- Swap in/out plus memory PSI -> real memory pressure.
- High steal -> virtualization contention.
- OOM records in one cgroup -> local limit or workload growth.

## Tools referenced
- `linux_system_info`
- `linux_process_list`
- `linux_disk_usage`
- `linux_read_log`
- `linux_kill_process`
- `shell_run`

## Escalation
Escalate with kernel/distribution, environment type, timestamped samples, cgroup limits, affected PID/service, PSI, IO latency, OOM or device errors, and a reproducible workload.
