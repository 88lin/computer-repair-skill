---
name: mac-tune-up
description: Safe maintenance sweep for a generally-sluggish Mac — refresh caches and reclaim memory without risk
platform: macos
last_reviewed: 2026-06-08
author: noah-team
source: bundled
emoji: 🧹
---

# Mac Tune-Up

A bounded, **safe** maintenance sweep for a Mac that feels generally sluggish
but isn't pinned by one runaway process or a full disk. Every step is
reversible or self-rebuilding — nothing here risks data or system stability.
For a Mac that's merely "a bit slow," this sweep noticeably helps in the
**majority (~70%)** of cases; when one specific cause dominates, route there
instead (see When to activate).

## When to activate
- User asks to "tune up", "optimize", "speed up", or "clean up" their Mac in
  the general sense (not a specific app, not a disk-full situation).
- Or as the follow-on when `performance-forensics` finds no single cause.

If there IS a single cause — one app pinning CPU, real memory pressure, a full
disk — handle that first via `performance-forensics` / `disk-space-recovery`.

## How to run it
Tell the user up front what the sweep does and that it's safe, then run the
steps. **Each step is independent**: check its result, report what it did, and
continue even if one is skipped. Never abort the whole sweep because one step
wasn't applicable. Measure memory before (`vm_stat`) so the final `ui_done`
can show what was reclaimed.

### Step 1 — Flush DNS cache
Resolves "some sites won't load / load slowly" and stale DNS entries.
`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
Needs admin (Noah prompts natively). Harmless — the cache repopulates on use.

### Step 2 — Rebuild Finder / icon / QuickLook caches
Fixes wrong or slow-to-draw icons and laggy previews.
`qlmanage -r cache >/dev/null 2>&1; killall Finder`
`killall Finder` relaunches Finder (a brief flash) — warn the user it'll blink.

### Step 3 — Clear stale saved-application-state
Old window-restore data that accumulates and can slow app launches.
`rm -rf ~/Library/Saved\ Application\ State/*.savedState`
Apps reopen with fresh windows. If the folder is absent, report "nothing to
clean" and continue.

### Step 4 — Relieve memory pressure (only if elevated)
If `vm_stat` / `memory_pressure` shows pages under pressure, reclaim inactive
memory with `sudo purge`. Skip if memory is already healthy (it's a no-op
there). Re-read `vm_stat` after to show the change.

### Step 5 — Rebuild LaunchServices ("Open With" duplicates)
Fixes duplicate or wrong entries in the "Open With" menu.
`…/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain user`
If `lsregister` isn't present on this macOS version, skip and report it.

### Optional — Spotlight reindex (ONLY if user reports search is slow)
Heavy and slow (re-indexes the whole disk over the following hour). Do **not**
run by default — only when the user explicitly says Spotlight search is slow or
wrong, and only with their OK: `sudo mdutil -E /`. Warn that search is degraded
for ~30–60 min while it rebuilds.

## Close with a summary
End in one `ui_done` listing what each step did and the memory reclaimed, e.g.
"Flushed DNS, rebuilt Finder + icon caches, cleared 14 saved states, reclaimed
1.8 GB inactive memory. Your Mac should feel snappier."

## Key signals
- **"Icons wrong / previews laggy"** → Step 2 (Finder/QuickLook cache rebuild).
- **"Some websites won't load but others do"** → Step 1 (DNS flush).
- **"Apps slow to launch / restore weird windows"** → Step 3 (saved state).
- **"Memory feels tight after long uptime"** → Step 4 (purge), then suggest a
  restart if uptime > 7 days.
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
  Noah *shows* them and lets the user decide, never deletes silently.
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
