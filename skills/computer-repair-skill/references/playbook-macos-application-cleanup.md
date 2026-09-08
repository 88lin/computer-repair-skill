---
name: macos-application-cleanup
description: Audit and clean regenerable macOS app caches or duplicates while preserving containers, chat data, and keychains
platform: macos
last_reviewed: 2026-09-09
author: computer-repair-skill-maintainers
source: local
---

# macOS Application Cleanup

## When to activate
Use for a named application's data growth on macOS: container or cache bloat, WeChat received-file duplication, browser cache growth, developer tool caches, or a request to reclaim application storage safely. For a general maintenance sweep use `mac-tune-up`; for volume-level space triage use `disk-space-recovery`. This playbook is for one application's data boundary at a time.

## Quick check
Identify the application, version, bundle identifier, signing status, profile/account, exact data root, running processes and helpers, sync state, and backup status. Use `mac_app_support_ls`, `mac_path_metadata` and `mac_process_list`; do not assume a path from a README or another machine.

Before proposing any deletion, read [cleanup-protocol.md](cleanup-protocol.md) and, for a community or vendor rule list, [rule-source-contract.md](rule-source-contract.md). Treat the rule as data to review, not as execution authorization.

## Standard diagnostic path

### 1. Locate the real data root
Resolve the bundle identifier first, then check every location the app may use, because sandboxed and non-sandboxed apps differ:

- sandboxed: `~/Library/Containers/<bundle-id>/Data/` (its own `Library/Application Support`, `Library/Caches`, `Documents`);
- non-sandboxed: `~/Library/Application Support/<id>`, `~/Library/Caches/<id>`, `~/Library/Logs/<id>`, `~/Library/Saved Application State/<id>.savedState`;
- shared between an app family: `~/Library/Group Containers/<group-id>`;
- preferences: `~/Library/Preferences/<id>.plist`.

WeChat stores its data under `~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/`. Received files and regenerable caches inside it may be candidates; chat databases, favorites, Moments data, custom emoji and any unverified account directory stay out of automatic cleanup.

A read denied by TCC is `unknown`, not "empty". Mail, Messages, Safari, cookie stores and the Photos library are protected regardless of the app being cleaned; if full enumeration is required, state that Full Disk Access is needed and let the user grant it in System Settings. Do not work around a privacy prompt.

### 2. Establish the data boundary
Separate `Caches`, `Logs`, thumbnails, shader/download caches and other regenerable scopes from container databases, chat history, favorites, cookies, credentials, account keys and user-created media. Keep `~/Library/Keychains`, Mail, Messages, the Photos library, `~/Library/Mobile Documents` (iCloud Drive) and any `Group Containers` directory shared with another installed app in the protected class.

Preferences are owned by `cfprefsd`, not by the file on disk. Editing or deleting a `.plist` while the app or the preferences daemon holds a cached copy can be silently reverted or corrupted; quit the app first and prefer `defaults` over hand-editing the file.

If the application is not running, still check for helper processes, login items and background sync. Never force-quit a process as an implicit cleanup step: quit through the application's own UI, and treat a `kill -9` on a helper as an escalation the user has to approve, not a prerequisite.

The most common way to destroy state while "clearing cache" is to delete a regenerable directory's sibling. Check these known pairs before proposing anything:

| Application | Deletable sibling (regenerates) | Protected sibling |
|---|---|---|
| Chromium-family profile | `Service Worker` | `IndexedDB`, `Local Storage`, `Login Data`, `Cookies`, `Preferences`, `Bookmarks` |
| Telegram | `Group Containers/<team-id>.ru.keepcoder.Telegram/account-*/postbox/media` | `postbox/db`, the local message database |
| Feishu / Lark | `Application Support/LarkShell/aha/users/<user-id>/profile_explorer` | `profile_main` (session — removing it forces a new QR login), `sdk_storage`, `database` |
| WeChat / QQ / DingTalk | the app's own storage-management screen | any hash-named directory inside the container |

Two things a scan of the default profile misses: automation or debugging launches Chromium with its own `--user-data-dir`, so a second profile directory can hold a large independent `Service Worker` cache; and multi-account apps keep one directory per account id, where the largest is often an account the user no longer uses. Enumerate every account directory and every non-default profile before reporting a total.

For WeChat, QQ, DingTalk and WeCom, route the user to the application's built-in storage management first. Deleting inside those containers by hand risks removing chat history that sits beside the caches, so do it only when the user explicitly asks, understands the risk, and the target is a documented cache subdirectory.

### 3. Detect duplicate files conservatively
When the request is duplicate cleanup, group candidates by size, then compare a bounded prefix hash, then a full SHA-256 hash with `mac_file_hash`. Only equal size and full hash make a duplicate candidate.

Before reporting reclaimable bytes, de-duplicate by inode with `mac_path_metadata`: two paths that are hard links to the same inode are not two copies, and deleting one frees nothing. APFS clones share blocks the same way, so apparent size is an upper bound on what a delete can return. On a case-insensitive APFS volume, two names differing only in case are the same file — do not report them as duplicates. Show every path, timestamp, owner, inode and hash; never choose "shortest path" or "oldest file" as an irreversible rule without user approval.

### 4. Use explicit scopes
Prefer the owning application's documented cleanup, or the tool's own cache command rather than deleting its directory — for example `brew cleanup` (preview with `--dry-run`), `uv cache clean`, `npm cache clean --force`, `pip cache purge`, `yarn cache clean`, `go clean -cache`, `cargo` registry cache maintenance, `pod cache clean --all`, and `docker system prune` instead of touching `Docker.raw`. A tool that manages its own cache can also update its index; a manual delete can leave it inconsistent. A non-zero exit from a cache command is not automatically failure — re-measure before concluding.

Xcode is the usual large offender: `~/Library/Developer/Xcode/DerivedData` rebuilds on the next build, and `~/Library/Developer/CoreSimulator/Caches` plus old iOS `DeviceSupport` directories are regenerable too. Say plainly that the first build or first page load after cleanup will be slower — rebuild cost is part of the plan, not a surprise.

Do not recursively match `*.tmp`, `node_modules`, or an entire container or `~/Library` subtree. A scope must state its positive targets and redlines, must not follow symlinks or firmlinks, and must be safe when a directory is absent.

For each reviewed rule, run a read-only preview first. Show the concrete files, exclusions, warnings, total bytes and locked/skipped items. If a rule cannot distinguish cache from container state, keep it report-only.

### 5. Stage a reversible action
After the user approves the exact list, quit the application through its normal UI or let the user do so. Move files with `mac_trash_path` to the Trash on the same volume, or to an isolated quarantine directory; do not use permanent deletion. Write an undo manifest with `mac_operation_log` containing original path, size, SHA-256, inode, timestamp and destination. Use a verified backup first when the boundary touches account, mail or chat data.

Re-check each path, inode and hash immediately before moving it. Stop the item if it changed, escaped the approved root or the manifest could not be written. Never turn this playbook into a silent scheduled delete; unattended runs may produce inventory or preview reports only.

## Verification
Re-scan the same scopes with the same rule, compare byte counts and duplicate groups, and launch the application or its relevant workflow. Confirm the undo manifest and Trash/quarantine entries exist and are readable.

Re-measure free space with `mac_disk_usage`. If it did not move as expected, check local Time Machine snapshots before concluding the cleanup failed: freed bytes can remain held as purgeable space. Report snapshot evidence instead of deleting snapshots as a follow-up step. Report skipped locked files rather than retrying with force.

## Caveats
- Browser `Cookies`, `Login Data`, profile preferences and extension stores are not caches.
- `~/Library/Caches` also holds data some apps never regenerate cleanly; a directory named `Caches` is not automatically disposable.
- Trash is not a backup, and emptying it is a separate confirmed action that must not run in the same batch as a cleanup that relies on it for rollback.
- Files inside `~/Library/Mobile Documents` are iCloud data; removing a local copy can delete it from the cloud and other devices.
- Unknown application directories stay in a report until the owner and redlines are known.

## Escalation
Escalate when the app has no documented data boundary, the target is synchronized, encrypted or managed by MDM, TCC blocks the evidence needed for a decision, hashes change during scanning, SIP-protected or system locations are involved, or a cleanup would require administrator access outside the user's home directory.

## Tools referenced
- `mac_app_support_ls`
- `mac_path_metadata`
- `mac_path_inventory`
- `mac_process_list`
- `mac_disk_usage`
- `disk_audit`
- `mac_file_hash`
- `mac_trash_path`
- `mac_operation_log`
- `ui_spa`
- `shell_run`
