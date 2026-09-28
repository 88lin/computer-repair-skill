---
name: performance-forensics
description: Diagnose slowness, high CPU, memory pressure, and hangs
platform: macos
last_reviewed: 2026-09-28
author: upstream-maintainers
source: bundled
emoji: ⚡
---

# Performance Forensics

## When to activate
User reports: computer is slow, fans are loud, spinning beach ball, apps freezing, system lagging, "everything takes forever."

## The iron rule: close the loop, never hand off a chore
Every path below ends with **the host Agent taking the action (with the user's OK) and
then verifying the result** — not with "now you go close some tabs." A user
who asked for help because their Mac is slow should not be handed homework.

- ✅ "I'll quit Safari and Chrome to free that 2 GB — ready?" → do it → re-measure → report freed RAM.
- ❌ "Try closing some Safari tabs and let me know."

If an action genuinely requires the user (e.g. a doc with unsaved changes),
say *specifically* what and why, then **verify after** they confirm — never
leave the session dangling on a `WAIT_FOR_USER` with no follow-up.

## Quick check
Map **`mac_performance_diagnose`** through `tool-contract.md` and `tools-macos.md`.
It is a semantic alias, not a guaranteed installed tool or fixed JSON schema. Gather
CPU samples, memory pressure, swap activity, free space and process ownership using
available host capabilities. Treat any `primary` classification as a hypothesis and
verify the underlying signals; never assume a tool automatically protects system PIDs.

## The diagnoses (try in order)

### D1 — `primary: cpu` — Runaway process (most common single cause)
The diagnose tool's top `top_cpu` entry is pinning the CPU.
- Verify the PID, owner and role. Ask the user to save work and prefer the app's normal
  Quit action; terminating a process requires specific approval and unsaved-work warning.
- **Close the loop:** re-run `mac_performance_diagnose`, confirm CPU dropped,
  report it in a `ui_done`.

### D2 — `primary: memory` — Memory pressure (the dangling-loop trap)
Swap being allocated is not itself proof of current pressure. Check pressure and
swap-in/out over a sampling interval before identifying sustained consumers.
- Prefer normal application Quit after the user saves work. SIGTERM (signal 15) does
  not guarantee a save prompt or preserved tabs/documents; never describe it as safe.
- If normal Quit fails, explain data-loss risk and obtain approval for the exact PID
  before `mac_kill_process`. Do not substitute force-kill for an app the user needs open.
- Re-measure pressure, swap activity and the actual symptom. Do not run `sudo purge`;
  discarding reclaimable cache can increase I/O and reduce performance.
- **Normal, not a problem:** high *Compressed Memory* and *Cached Files* are
  healthy macOS behavior — don't alarm the user about them.

### D3 — `primary: disk` — Disk full
`signals.disk_full` true (boot volume ≥ 90%). A near-full SSD slows everything
— activate `disk-space-recovery` and let it close that loop.

### Restart / thermal — when nothing else stands out
- `uptime_days > 7` → recommend a restart (clears accumulated swap, caches,
  leaked memory — the most underrated fix). The user triggers it; frame it as
  the recommended next step.
- `primary: thermal` (`kernel_task` holding CPU) → the Mac is hot and throttling
  itself. Fix is physical: improve ventilation, don't use on a soft surface.

> **Durable advice (don't skip):** for
> the common case — an 8 GB Mac with many browser tabs — quitting apps is only a
> band-aid; it recurs. Tell the user plainly and give prevention: keep tabs
> modest, restart weekly, and offer the **`mac-tune-up`** sweep. If they want it
> hands-off, offer scheduled read-only reports. Unattended deletion is not a routine
> performance measure; each new cleanup batch needs a current preview and approval.

## Caveats — DO NOT kill these (they look suspicious but are normal)
- **`kernel_task`** — thermal throttling. High CPU = the Mac is hot and
  deliberately slowing itself. Fix ventilation; don't use on a soft surface.
- **`WindowServer`** — display compositor. High CPU = many monitors, heavy
  animations, or a GPU-heavy app. Close complex-UI apps.
- **`mds` / `mds_stores`** — Spotlight indexing. Temporary after OS updates or
  restores; resolves in 30–60 min. Killing it just restarts indexing.
- **`trustd`** — certificate checks. Brief spikes are normal.
- **`backupd`** — Time Machine backup running. Temporary.
- **`bird` / `cloudd`** — iCloud sync. Heavy with large libraries. Temporary.

## Key signals (explain these instead of "fixing" them)
- **"Slow after an update"** → `mds` re-indexing / Time Machine snapshot /
  iCloud re-sync. All temporary — resolves within hours. Reassure the user.
- **"Fans loud but nothing open"** → `mds`, `backupd`, or `softwareupdated`
  spiking in the background. Temporary.
- **"Slow only in the morning"** → Login Items launching at boot. Point the
  user to System Settings → General → Login Items to trim. (Diagnose and
  guide; the host Agent does not auto-delete login items — see `mac-tune-up` non-goals.)
- **"One specific app is slow"** → not a system issue. The app may need an
  update or a cache reset. Consider the `app-doctor` playbook.
- **Chrome/Electron apps eating memory** → each tab/window is its own process,
  by design. Fewer tabs is the fix — and in D2, the host Agent quits them for the user.

## Portability note
macOS versions vary across customers. For any `shell_run` step, check the
result and degrade gracefully — report "skipped" if a command isn't present
rather than failing the flow. Don't assume a specific macOS version.

## Tools referenced
- `mac_performance_diagnose` — one-call diagnosis: primary cause + signals +
  top memory/CPU processes (use this first; re-run it to verify after a fix)
- `mac_kill_process` — terminate a verified process after approval; SIGTERM may lose unsaved work
- `shell_run` — scoped native performance measurements
- `mac_system_info` / `mac_process_list` / `mac_disk_usage` — only if you need
  raw detail the diagnose tool didn't surface

## Escalation
If performance is still poor after diagnosis:
- Apple Diagnostics (restart holding D) to check for hardware faults.
- Older Mac with an HDD → an SSD is the single biggest upgrade.
- RAM consistently maxed → more physical RAM (if upgradeable) or fewer
  simultaneous apps.
