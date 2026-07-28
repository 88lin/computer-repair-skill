---
name: windows-crash-dump-triage
description: Triage Windows blue screens, unexpected restarts and app crashes from dump metadata and event evidence
platform: windows
category: hardware-crash-diagnostics
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Crash And Dump Triage

## When to activate

User reports a blue or green screen, a stop code, spontaneous restarts or shutdowns, a black screen followed by reboot, "Windows did not shut down properly", freezes that require a hard power cycle, or a single application that crashes repeatedly.

## Quick check

Run `win_system_summary` and record the Windows edition and build, uptime, last boot time, recent update history, whether the machine is a laptop on battery, and whether the crash is reproducible.

Then establish the single most important distinction before anything else:

- **Kernel-level crash** (stop code shown, `Minidump` written, BugCheck event) — driver, firmware or hardware.
- **Unexpected power loss** (no stop code, no dump, Kernel-Power 41 with no bug check data) — power, thermal, PSU, battery or a hard shutdown by the user.
- **User-mode application crash** (only that app dies, Application Error events) — the application, its plugins or a corrupted profile.

These three have almost no diagnostic steps in common. Mixing them wastes the visit.

## Standard diagnostic path

### 1. Confirm crash capture is even enabled

Run `win_crash_dump_list` and read `Win32_OSRecoveryConfiguration` first. If the dump type is set to none, or the page file is too small or disabled on the system drive, no dump exists and none will be written next time.

Report this as a finding: without a dump, kernel triage is limited to event evidence. Changing the dump setting is a configuration change; propose it explicitly with the current value recorded, and note that a kernel dump needs page-file space on the system volume.

### 2. Build the crash timeline from events

Query the System log with `win_read_log` for the providers that actually carry crash evidence:

- `BugCheck` (event 1001) — the stop code and parameters as recorded after reboot.
- `Microsoft-Windows-WER-SystemErrorReporting` (event 1001) — the same bug check via error reporting.
- `Microsoft-Windows-Kernel-Power` (event 41) — the machine restarted without a clean shutdown.
- `EventLog` (event 6008) — previous shutdown was unexpected.
- `Microsoft-Windows-WHEA-Logger` — a hardware error the platform reported; treat as hardware until disproved.
- `Microsoft-Windows-Kernel-Boot` and `Microsoft-Windows-Kernel-PnP` — boot mode and device start failures around the event.

For application crashes use `win_app_logs` and read `Application Error` (event 1000), `Application Hang` (1002), `.NET Runtime` (1026) and the Windows Error Reporting entries. Record the faulting module name and version, not just the application name — the faulting module is usually the actual culprit.

Write the timeline down: crash time, stop code, faulting module, what the user was doing, and what changed on the machine in the preceding days.

### 3. Read the stop code before touching the dump

The stop code plus the first parameter narrows the cause more cheaply than dump analysis. Use `knowledge_read` to pull the recorded meaning of the specific bug check before proposing any action, and state the interpretation in terms of a subsystem rather than a single guess.

Useful groupings:

- Memory management, page fault in nonpaged area, bad pool header or bad pool caller: memory, storage or a driver corrupting pool. Route to `memory-diagnostics` and `storage-health-smart`.
- Driver-named stop codes (`DRIVER_IRQL_NOT_LESS_OR_EQUAL`, `SYSTEM_THREAD_EXCEPTION_NOT_HANDLED` with a named module): identify that driver with `win_driver_inventory`.
- Watchdog and clock-interrupt stop codes: firmware, virtualization, overclocking or a stalled device.
- Machine check exception and WHEA uncorrectable error: CPU, memory, bus or power. Hardware first, software last.
- Critical process died, inaccessible boot device, unmountable boot volume: storage path and system files. Route to `windows-winre-system-repair` on Windows, and treat the disk as suspect.

### 4. Correlate with what changed

Check recent Windows updates, driver installs, new peripherals, BIOS or firmware updates, a new memory module, a docking station, and any tuning or "optimizer" utility. A crash that started within days of a driver or firmware change is a rollback candidate before it is a hardware candidate.

For repeated crashes tied to one device, route to `windows-driver-lifecycle-audit` on Windows for the vendor-source and rollback path.

### 5. Handle the dump files safely

List dumps by path, timestamp and size only. Also list `LiveKernelReports`, which records recoverable kernel events such as display watchdog timeouts without a full blue screen.

A kernel memory dump contains the contents of system memory at crash time. It can include passwords in memory, decryption keys, document fragments and network data. Therefore:

- do not read dump contents into the conversation;
- do not copy dumps to shared folders, chat, ticket attachments or cloud storage without explicit owner approval;
- do not upload dumps to third-party "BSOD analyzer" websites;
- if symbolized analysis is needed, have the user run WinDbg locally against the Microsoft symbol server, and share only the resulting module and stop-code summary.

Record the SHA-256 of a suspect driver binary with `win_file_hash` when a module is named, so the exact file version can be identified later without moving the dump.

### 6. Act on the narrowest confirmed cause

Show the plan and get approval. One change at a time, with the previous state recorded.

- Named third-party driver: update from the vendor's own source, or roll back to the previously working version.
- Firmware or BIOS defect: apply the vendor update only on AC power with a charged battery, and only after the user confirms.
- Suspected memory or storage: run the dedicated flows rather than replacing parts speculatively.
- Overclocking, undervolting or XMP/EXPO profiles: return to stock settings as a diagnostic step.
- Application crash in a plugin or add-in: disable that component, not the application.
- Corrupted user profile or configuration: test with a new local profile before any repair install.

Do not enable Driver Verifier as a routine step. It changes kernel behavior, can prevent boot, and belongs to escalation with a recorded rollback path through Safe Mode.

## Verification

Re-run the workload that triggered the crash and keep the machine in service long enough to cover the original crash interval. Confirm no new BugCheck, WER, WHEA or Kernel-Power 41 events appear, that `win_crash_dump_list` shows no new dump files, and that the previously faulting application or device completes the user's task. Record the verification window explicitly — "no crash for two hours" and "no crash for a week" are different claims.

## Caveats

- Kernel-Power 41 without bug check data is not a diagnosis; it only says the shutdown was not clean.
- A stop code names the subsystem that noticed the fault, not necessarily the component that caused it.
- Bad memory can produce many different, unrelated-looking stop codes.
- A single crash after a power interruption or forced shutdown may need no repair at all.
- On managed devices, driver and firmware policy may be controlled centrally; report the policy instead of fighting it.
- Storage-related stop codes can indicate a dying drive; do not run repeated repair passes on a drive with uncorrectable errors before data is safe.

## Escalation

Escalate to hardware service or the device owner with: exact stop code and parameters, timestamps, faulting module and version, dump inventory (paths and sizes only, not contents), WHEA records, recent update and hardware changes, memory and storage health results, and the verification window already attempted. Escalate immediately for WHEA uncorrectable errors, machine check exceptions, repeated crashes across a clean reinstall, or crashes that persist with a single memory module and stock firmware settings.

## Tools referenced

- `win_crash_dump_list`
- `win_system_summary`
- `win_read_log`
- `win_app_logs`
- `win_driver_inventory`
- `win_file_hash`
- `knowledge_read`
