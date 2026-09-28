---
name: mac-tune-up
description: Diagnose a sluggish Mac and apply only symptom-matched maintenance with approval and rollback
platform: macos
last_reviewed: 2026-09-28
author: upstream-maintainers
source: bundled
emoji: 🧹
---

# Mac Tune-Up

A symptom-directed maintenance review for a sluggish Mac. Cache resets can discard
useful state and increase subsequent load times; they are not a general speed fix.
Establish a performance baseline and select only a step supported by evidence.

## When to activate
- User asks to "tune up", "optimize", "speed up", or "clean up" their Mac in
  the general sense (not a specific app, not a disk-full situation).
- Or as the follow-on when `performance-forensics` finds no single cause.

If there IS a single cause — one app pinning CPU, real memory pressure, a full
disk — handle that first via `performance-forensics` / `disk-space-recovery`.

## How to run it
Read [cleanup-protocol.md](cleanup-protocol.md) before changing app state. Show each
proposed action, impact and rollback, and obtain approval. Skip irrelevant steps;
on unexpected effects stop and reassess. Record memory pressure, swap activity and
the actual symptom before and after, rather than treating freed RAM as success.

### Step 1 — Flush DNS cache
Resolves "some sites won't load / load slowly" and stale DNS entries.
`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
Needs admin approval through the host Agent. Harmless — the cache repopulates on use.

### Step 2 — Rebuild Finder / icon / QuickLook caches
Fixes wrong or slow-to-draw icons and laggy previews.
`qlmanage -r cache >/dev/null 2>&1; killall Finder`
`killall Finder` relaunches Finder (a brief flash) — warn the user it'll blink.

### Step 3 — Clear stale saved-application-state
Only consider a reset when one identified app has a reproducible window-restore
failure. Saved state may contain unsaved work. Ask the user to save work and close
that app, then inspect its exact state directory. After approval, quarantine only
that directory with a manifest and restore path; never sweep all `*.savedState`.
Reopen the app to verify and retain the recovery copy until the user accepts it.

### Step 4 — Relieve memory pressure (only if elevated)
Use `vm_stat` and `memory_pressure` to distinguish cache usage from sustained
pressure and swap. Do not run `sudo purge` as a tune-up: macOS manages reclaimable
cache, and discarding it can increase I/O and slow the next workload. Identify the
responsible process and ask the user to save work before closing or restarting it.

### Step 5 — Rebuild LaunchServices ("Open With" duplicates)
Fixes duplicate or wrong entries in the "Open With" menu.
Inspect `/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister`
and its local help first. Prefer correcting the affected file type in Finder's
Get Info → Open With. A full registry rebuild can change associations and needs a
separate plan recording the current defaults before execution.
If `lsregister` isn't present on this macOS version, skip and report it.

### Optional — Spotlight reindex (ONLY if user reports search is slow)
Heavy and slow (re-indexes the whole disk over the following hour). Do **not**
run by default — only when the user explicitly says Spotlight search is slow or
wrong, and only with their OK: `sudo mdutil -E /`. Warn that search is degraded
for ~30–60 min while it rebuilds.

## Close with a summary
Report each action or skipped step, the before/after symptom and measured evidence,
and retained recovery copies. Do not promise an improvement without verification.

## Key signals
- **"Icons wrong / previews laggy"** → Step 2 (Finder/QuickLook cache rebuild).
- **"Some websites won't load but others do"** → Step 1 (DNS flush).
- **"Apps slow to launch / restore weird windows"** → Step 3 (saved state).
- **"Memory feels tight after long uptime"** → Step 4 (pressure and swap diagnosis).
- **"Wrong app opens my files / duplicate Open-With entries"** → Step 5.
- **"Spotlight search is slow or wrong"** → Optional reindex (opt-in only).

## Caveats — what this sweep will NOT do (and why)
Declining unsafe "optimizations" is part of being trustworthy. State these if
the user asks for them:
- **No swap / virtual-memory surgery** — risks crashes; macOS manages VM better
  than any manual trick.
- **No deleting Time Machine local snapshots** — they're recovery points;
  removing them breaks backup continuity.
- **No killing system services or "refreshing" WiFi/Bluetooth radios** — drops
  the user's active connections for no durable gain.
- **No auto-deleting startup / login items** — many are legitimate app helpers;
  The host Agent *shows* them and lets the user decide, never deletes silently.
- **No registry-style "cleaners" or made-up speed hacks** — macOS has no
  registry; such steps are placebo at best, harmful at worst.

## Portability
Customers run many macOS versions. These commands have been stable across
recent releases, but check each step's exit status and **skip-and-report rather
than error** if a command or path is missing. Do not assume a macOS version.

## Escalation
If the Mac is still slow after the sweep:
- Re-run `performance-forensics` — a single cause (runaway process, memory
  pressure, full disk) may have emerged that the sweep doesn't address.
- Suggest a restart if uptime > 7 days.
- Older Mac with an HDD → an SSD is the biggest single upgrade.

## Tools referenced
- `shell_run` — runs each maintenance command (safe / sudo-gated tier)
- `mac_system_info`, `vm_stat` — before/after measurement
- `mac_disk_usage` — confirm this isn't actually a disk-full case first
