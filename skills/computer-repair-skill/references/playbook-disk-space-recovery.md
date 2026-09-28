---
name: disk-space-recovery
description: Reclaim disk space on macOS — measure, audit, clean cache-class data, report freed bytes
platform: macos
last_reviewed: 2026-09-28
author: upstream-maintainers
source: bundled
emoji: 💾
---

# Disk Space Recovery

## When to activate
Explicit: "clean up my storage", "free disk space", "find space hogs", "check storage", "storage almost full", "low storage", "can't install update". Symptom-driven: Mac feels slow AND free space is below the healthy target.

## Scope
**In**: cache-class data — package managers, Xcode/simulators/DerivedData, app caches (Slack, Discord, Code, Cursor), Trash, old logs, stale incomplete downloads, old macOS installers.
**Out (redirect)**: moving files to cloud — that means *offload* (copy → verify the copy exists → only then delete local), never straight-delete; uninstalling apps (Applications folder for now); Photos/Mail/Messages bodies (TCC — System Settings → Storage). If a quota forces touching irreplaceable data, stop and surface it — do not delete it to hit a number.

## Heuristics
- ≥20% free → healthy, don't push cleanup.
- 10–20% → tight, cleanup recommended.
- <10% → critical; APFS performance degrades.
- macOS major updates need 15–30 GB free regardless of percent.
- Approval covers only the displayed targets and actions; newly discovered targets require a new preview.
- ~0 bytes freed → run the holder diagnostic, surface the process, ask user to quit. Don't auto-quit. Don't loop.

## Pipeline
1. **Measure**: `mac_disk_usage` + `disk_audit`. If healthier than target AND the prompt was symptom-driven (not explicit), say so and stop.
2. **Propose**: read [cleanup-protocol.md](cleanup-protocol.md) and [macOS application cleanup](playbook-macos-application-cleanup.md). List each literal target, ownership evidence, size, exclusions, impact and recovery path. No cache category is automatically authorized.
3. **Execute**: after approval, recheck each target and move only the approved items to Trash or a same-volume quarantine with a manifest. Stop that item if backup or path verification fails. Native cache-clean commands can permanently discard data; explain that limitation and obtain specific approval before using one.
4. **Verify**: re-run `mac_disk_usage`; compute delta vs step 1.
5. **Report** via SPA findings: starting free, ending free, per-category freed, items skipped with reason. If target not met, ONE concrete next move — not a list.

## Recipes

**Candidate inventory, not a batch deletion script:**
- Package managers: discover their actual cache roots using their current CLI. Preview a native cleanup's scope; do not chain multiple managers or run `brew autoremove` as cache cleanup (it uninstalls packages).
- Slack, Discord, Teams and editors: confirm the installed version and profile, close the app normally, and inspect exact cache children. Preserve `User`, databases, sessions and credentials; do not infer a target from a brace-expanded list of app names.
- Xcode: inspect individual DerivedData projects. DeviceSupport, archives and simulator devices may contain needed debugging or test data; treat them separately and preserve a recovery copy.
- Logs: age alone does not make a log disposable. Preserve incident evidence and current logs, then preview individual archived files.
- Mail downloads and incomplete downloads may be the only copy of user data. Use the owning app's Storage UI after review; do not treat them as caches.
- Old macOS installers: review the exact app bundle and whether it is a needed recovery installer before moving it to Trash.
- Trash: never empty it in a cleanup batch that relies on Trash for rollback. Emptying Trash is a separate irreversible action with its own review.

**iOS Simulator:** first run `xcrun simctl list devices` and identify the exact devices,
availability, ownership and data to retain. Prefer Xcode's device management UI. Do not
reset all simulators or stop active devices as a disk cleanup shortcut. Removal of a
reviewed device requires its exact UDID, a recovery plan and separate approval.
On `currently in use` / `Failed to eject`, report the holding process and stop that item.

**Holder diagnostic** (use when a row returns ~0 freed; replace the path with the actual cleanup target):
```bash
lsof +D /absolute/path/to/check 2>/dev/null | awk 'NR>1 {print $1}' | sort -u | head
```

**Cloud provider detection** (when user mentions cloud):
```bash
ls -la ~/Library/CloudStorage/ ~/Library/Mobile\ Documents/ 2>/dev/null
```
Folder hints: `GoogleDrive-*`, `Dropbox`, `OneDrive*`, `com~apple~CloudDocs` (iCloud).

## Critical exclusions
Deletes inside protected trees (Application Support, Containers, Messages, etc.) are **gated by the harness**: you must inspect a folder (`ls`/`du`) before deleting it, and blind wildcard sweeps like `rm -rf .../Application Support/*` are held back — enumerate and remove specific, inspected subdirs instead. Refuse even with user blessing:
- `~/.claude/`, `~/.local/share/claude/`, `~/Library/Application Support/Codex/`, `~/Library/Logs/com.openai.codex/` — AI assistant state and history (Claude Code, Codex Desktop).
- `~/Library/Application Support/{Code,Cursor,Zed}/User/` — editor settings (Cache* subdirs are fine).
- `~/Library/Application Support/{1Password,Bitwarden,Dashlane}/` — credential vaults.
- `~/Library/Application Support/Spotify/` (incl. `PersistentCache/`) — offline music.
- `~/Library/Application Support/Final Cut Pro/`, `*.fcpbundle/Original\ Media/`, `*.flexolibrary` — irreplaceable media.
- `~/Library/Keychains/`, `~/Library/Application Support/com.apple.TCC/`, `com.apple.security*` — auth and permission state.
- `~/Library/Mobile Documents/`, `~/Library/Photos/Libraries/`, `~/Pictures/Photos\ Library.photoslibrary/` — iCloud / user media.
- `~/Library/Application Support/MobileSync/Backup/` — iOS device backups.
- `~/Documents/`, `~/Desktop/`, `~/Movies/`, `~/Music/`.
- Any `<App>.app/Contents/Frameworks/*/Versions/Current` symlink target or newest version.
- `~/.docker/Desktop/{vms,data}/` — use `docker system prune` instead.
- `.DocumentRevisions-V100` (anywhere) — macOS document versioning DB.
- `/Volumes/*/.Trashes/` — external-drive trash.

## Caveats
- **Purgeable space** is freed automatically (real available = free + purgeable). **System Data** in About This Mac is mostly auto-managed.
- `disk_audit` is a semantic alias, not a guaranteed background scanner or Diagnostics UI. Map it through `tool-contract.md` and record the scan time and scope.

## Key signals
- "Can't install macOS update" → needs 15–30 GB free; run pipeline, retry update.
- "Disk was fine yesterday" → runaway log or crash loop. Audit `~/Library/Logs` and `~/Library/Logs/DiagnosticReports`.
- "Already emptied Trash" → big consumers are dev artifacts (Xcode, simulators, Docker) and iOS backups.
- After the standard pipeline, anything still pinning the drive is usually user media (Photos, iOS backups) or genuinely-needed working files — surface them, don't push deletion.

## Tools referenced
- `mac_disk_usage` — top-line stats.
- `disk_audit` — categorized breakdown.
- `mac_clear_caches` — clears `~/Library/Caches/`.
- `shell_run` — runs the recipes; policy gates destructive `rm`/`sudo`.

## Escalation
If the pipeline doesn't free enough:
- iCloud / Optimize Mac Storage for Documents, Desktop, Photos.
- For developers, Xcode + simulators + Docker can legitimately use 100+ GB — don't push to delete working files.
- External or larger internal drive is the real answer if still stuck.
