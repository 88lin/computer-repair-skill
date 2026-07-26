---
name: performance-forensics
description: Diagnose slowness, high CPU, memory pressure, and hangs
platform: macos
last_reviewed: 2026-06-08
author: noah-team
source: bundled
emoji: ⚡
---

# Performance Forensics

## When to activate
User reports: computer is slow, fans are loud, spinning beach ball, apps freezing, system lagging, "everything takes forever."

## The iron rule: close the loop, never hand off a chore
Every path below ends with **Noah taking the action (with the user's OK) and
then verifying the result** — not with "now you go close some tabs." A user
who came to Noah because their Mac is slow should not be handed homework.

- ✅ "I'll quit Safari and Chrome to free that 2 GB — ready?" → do it → re-measure → report freed RAM.
- ❌ "Try closing some Safari tabs and let me know."

If an action genuinely requires the user (e.g. a doc with unsaved changes),
say *specifically* what and why, then **verify after** they confirm — never
leave the session dangling on a `WAIT_FOR_USER` with no follow-up.

## Quick check
Run **`mac_performance_diagnose`** — one call returns the `primary` cause
(memory / cpu / disk / thermal / healthy), the raw signals, RAM/swap/disk/
uptime, and the top memory + CPU processes (each flagged `system: true` if it's
protected). Use its `primary` to pick the path below. Don't fan out
`mac_system_info` + `mac_process_list` + `mac_disk_usage` separately — the
diagnose tool already gathered all of it in one pass.

## The diagnoses (try in order)

### D1 — `primary: cpu` — Runaway process (most common single cause)
The diagnose tool's top `top_cpu` entry is pinning the CPU.
- Offer to force-quit it with `mac_kill_process` (it isn't a `system: true`
  process — the tool already excluded those).
- **Close the loop:** re-run `mac_performance_diagnose`, confirm CPU dropped,
  report it in a `ui_done`.

### D2 — `primary: memory` — Memory pressure (the dangling-loop trap)
`signals.memory_pressure` is true (swap in use). Read `top_memory` for the hogs.
- **Noah quits them itself** (one approval), naming each from `top_memory`:
  "Firefox is using 2.3 GB and TextNow another 760 MB — I'll quit both to free
  ~3 GB. OK?" → quit via `mac_kill_process`.
- **Safe-quit rule:** ALWAYS use `mac_kill_process` (graceful SIGTERM, signal
  15) so the app saves its session/tabs. **Never** `shell_run` a `kill -9` /
  `killall -9` on a user's app — SIGKILL loses unsaved work.
- Then **relieve and verify**: `shell_run` `sudo purge`, re-run
  `mac_performance_diagnose`, report freed memory in a `ui_done`.
- **Never** end on "close some tabs yourself." If a browser must stay open,
  quit the *other* hogs and still verify.
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

> Resolves ~80% of performance complaints. **Durable advice (don't skip):** for
> the common case — an 8 GB Mac with many browser tabs — quitting apps is only a
> band-aid; it recurs. Tell the user plainly and give prevention: keep tabs
> modest, restart weekly, and offer the **`mac-tune-up`** sweep. If they want it
> hands-off, mention Noah can run a scheduled cleanup so it doesn't keep coming
> back.

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
  guide; Noah does not auto-delete login items — see `mac-tune-up` non-goals.)
- **"One specific app is slow"** → not a system issue. The app may need an
  update or a cache reset. Consider the `app-doctor` playbook.
- **Chrome/Electron apps eating memory** → each tab/window is its own process,
  by design. Fewer tabs is the fix — and in D2, Noah quits them for the user.

## Portability note
macOS versions vary across customers. For any `shell_run` step, check the
result and degrade gracefully — report "skipped" if a command isn't present
rather than failing the flow. Don't assume a specific macOS version.

## Tools referenced
- `mac_performance_diagnose` — one-call diagnosis: primary cause + signals +
  top memory/CPU processes (use this first; re-run it to verify after a fix)
- `mac_kill_process` — graceful force-quit (SIGTERM/15) (NeedsApproval tier)
- `shell_run` — `sudo purge` (memory relief)
- `mac_system_info` / `mac_process_list` / `mac_disk_usage` — only if you need
  raw detail the diagnose tool didn't surface

## Escalation
If performance is still poor after diagnosis:
- Apple Diagnostics (restart holding D) to check for hardware faults.
- Older Mac with an HDD → an SSD is the single biggest upgrade.
- RAM consistently maxed → more physical RAM (if upgradeable) or fewer
  simultaneous apps.
