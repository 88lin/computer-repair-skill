---
name: linux-application-cleanup
description: Audit and clean regenerable Linux app caches or duplicates across XDG, Flatpak, and Snap data roots
platform: linux
last_reviewed: 2026-09-09
author: computer-repair-skill-maintainers
source: local
---

# Linux Application Cleanup

## When to activate
Use for a named application's data growth on Linux: XDG cache bloat, a Flatpak or Snap application's data directory, chat-client received-file duplication, developer tool caches, or a request to reclaim application storage safely. For filesystem-, inode-, journal- or container-level space triage use `linux-disk-space-recovery`. This playbook is for one application's data boundary at a time.

## Quick check
Identify the application, version, packaging format, the user account that owns the data, the exact data root, running processes, sync state and backup status. Use `linux_app_data_ls`, `linux_path_metadata` and `linux_process_list`; do not assume a path from a README, another distribution, or another machine.

Before proposing any deletion, read [cleanup-protocol.md](cleanup-protocol.md) and, for a community or vendor rule list, [rule-source-contract.md](rule-source-contract.md). Treat the rule as data to review, not as execution authorization.

## Standard diagnostic path

### 1. Resolve packaging before paths
The packaging format decides where the data lives, so determine it first:

- native package (deb/rpm/pacman): `${XDG_CONFIG_HOME:-$HOME/.config}`, `${XDG_DATA_HOME:-$HOME/.local/share}`, `${XDG_CACHE_HOME:-$HOME/.cache}`, `${XDG_STATE_HOME:-$HOME/.local/state}`;
- Flatpak: `~/.var/app/<app-id>/{cache,config,data}` — only `cache` is presumed regenerable;
- Snap: `~/snap/<name>/{current,common}`, with old revisions retained by snapd under system-managed paths;
- AppImage: usually a self-chosen directory under `~/.config` or `~/.local/share`;
- Wine/Bottles: an application directory inside a prefix such as `~/.wine/drive_c/...`.

There is no standard cross-distribution data path for WeChat on Linux — the official client, a Flatpak build and a Wine prefix all differ, and upstream tooling deliberately ships no Linux default. Discover the real root from the running process, the package's file list and the user's own configuration; never guess it from the Windows or macOS layout.

Verify which user owns the data. Do not read or clean another user's home directory, and do not silently escalate to `sudo` for a user-scope cleanup.

### 2. Establish the data boundary
Separate caches, logs, thumbnails and shader/download caches from configuration, databases, chat history, credentials, keyrings, mail and user-created media. Keep `~/.ssh`, `~/.gnupg`, `~/.local/share/keyrings`, mail stores under `~/.local/share`, browser profiles, and any synchronized directory in the protected class.

`~/.cache` is a convention, not a guarantee: some applications keep state there that they never regenerate cleanly. Clean named subdirectories with a known owner, not the whole tree. Equally, a Flatpak `data` directory is user data even though it sits beside `cache`.

If the application is not running, still check for helper processes, user services (`systemctl --user`) and background sync. Never kill a process as an implicit cleanup step.

### 3. Detect duplicate files conservatively
When the request is duplicate cleanup, group candidates by size, then compare a bounded prefix hash, then a full SHA-256 hash with `linux_file_hash`. Only equal size and full hash make a duplicate candidate.

Before reporting reclaimable bytes, de-duplicate by device and inode with `linux_path_metadata`. A link count above 1 means the paths may be hard links to one inode, where deleting one frees nothing; btrfs/XFS reflinks and sparse files also share or omit blocks, so apparent size is an upper bound on what a delete can return. Show every path, timestamp, owner, inode, link count and hash; never choose "shortest path" or "oldest file" as an irreversible rule without user approval.

### 4. Use explicit scopes
Prefer the owning application's or package manager's documented cleanup: `apt clean` / `dnf clean packages` / `pacman -Sc` for package caches, `flatpak uninstall --unused` for unreferenced runtimes, snapd's retention setting for old revisions. Explain the tradeoff — removing cached packages breaks offline reinstall and downgrade — and treat a retention setting as a configuration change with its own confirmation, not as a delete.

Do not recursively match `*.log`, `*.tmp`, `node_modules`, an entire data root, or anything outside the approved directory. A scope must state its positive targets and redlines, must not cross a filesystem boundary or follow symlinks, and must be safe when a directory is absent. Journal, container and image cleanup belongs to `linux-disk-space-recovery`; reference it instead of duplicating it here.

For each reviewed rule, run a read-only preview first. Show the concrete files, exclusions, warnings, total bytes and locked/skipped items. If a rule cannot distinguish cache from application state, keep it report-only.

### 5. Stage a reversible action
After the user approves the exact list, close the application normally or let the user do so. Move files with `linux_trash_path` — the XDG trash on the same filesystem, the mount point's `.Trash-$UID` for another filesystem, or an isolated quarantine directory when neither is available. Do not use permanent deletion. Write an undo manifest with `linux_operation_log` containing original path, size, SHA-256, device/inode, timestamp and destination. Use a verified backup first when the boundary touches mail, chat or credential data.

Re-check each path, inode and hash immediately before moving it. Stop the item if it changed, escaped the approved root or the manifest could not be written. Never turn this playbook into a silent cron or timer delete; unattended runs may produce inventory or preview reports only.

## Verification
Re-scan the same scopes with the same rule, compare byte counts and duplicate groups, and launch the application or its relevant workflow. Re-measure with `linux_disk_usage`, and account for the difference between apparent size and reclaimed blocks when the numbers disagree. Confirm the undo manifest and trash/quarantine entries exist and are readable. Report skipped locked files rather than retrying with force.

## Caveats
- Browser cookie stores, login data, profile preferences and extension stores are not caches.
- Deleted-but-open files keep their blocks until the holding process exits, so freed space may appear only after the application is closed.
- The XDG trash is not a backup, and emptying it is a separate confirmed action that must not run in the same batch as a cleanup that relies on it for rollback.
- A cleanup rule written for one distribution or packaging format may point at a path that means something different on another.
- Unknown application directories stay in a report until the owner and redlines are known.

## Escalation
Escalate when the app has no documented data boundary, the data is synchronized, encrypted (ecryptfs/fscrypt/LUKS-per-home) or on network storage such as NFS, SELinux/AppArmor denies access, files carry immutable attributes, the target belongs to another user or to a container/orchestrator, hashes change during scanning, or a cleanup would need root outside the user's home directory.

## Tools referenced
- `linux_app_data_ls`
- `linux_path_metadata`
- `linux_path_inventory`
- `linux_process_list`
- `linux_disk_usage`
- `linux_file_hash`
- `linux_trash_path`
- `linux_operation_log`
- `ui_spa`
- `shell_run`
