---
name: macos-persistence-audit
description: Audit macOS launch agents, daemons, login items, profiles and extensions before disabling or removing anything
platform: macos
category: macos-linux-repair
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# macOS Persistence Audit

## When to activate

User reports unexpected pop-ups, an application that reopens itself after being quit or deleted, a slow login, unknown menu-bar items, browser search or homepage changes, network activity from an unknown process, leftovers from an uninstalled application, or a "helper" that reinstalls itself.

## Quick check

Run `mac_system_summary` and record the macOS version, whether the Mac is Intel or Apple silicon, the current user and whether that user is an administrator, System Integrity Protection status, and whether the Mac is enrolled in MDM or managed by an organisation.

Establish whether this is a cleanup request or a suspected compromise. If malicious activity is plausible, evidence preservation comes before removal: use `activate_playbook` to bring in `malware-triage` and follow that flow first.

## Standard diagnostic path

### 1. Enumerate every persistence location

Run `mac_persistence_snapshot` and collect, as structured output:

- `/Library/LaunchAgents`, `/Library/LaunchDaemons`, and per-user `~/Library/LaunchAgents`;
- `launchctl` disabled-item state for the system and the current GUI session, so a "missing" item is not confused with a disabled one;
- login items and background task management entries;
- configuration profiles and MDM enrolment state;
- system extensions, network extensions, and any remaining kernel extensions;
- user cron entries, periodic scripts, and shell startup files;
- browser extensions and managed browser policies.

Record for each item: label, plist path, program arguments, `RunAtLoad` and `KeepAlive` settings, watch paths, owning user, and file ownership and permissions. `/System/Library` items are Apple-owned and protected; list them for completeness and do not modify them.

### 2. Attribute each item to something real

Cross-reference against installed software with `mac_app_list`, then verify identity rather than trusting the name.

For each suspicious program path:

- take the SHA-256 with `mac_file_hash`;
- read the code signature authority, team identifier and whether the binary is notarised;
- check the Gatekeeper assessment;
- check whether the path lives inside a legitimate application bundle or in a writable location such as a temporary directory, a user library folder or a hidden directory.

Signals worth attention: an unsigned or ad-hoc-signed binary in a user-writable path, a label that imitates an Apple label, a plist whose program argument is a shell one-liner, a `StartInterval` measured in seconds, a watch path on the user's home directory, and a helper with no corresponding installed application.

"Unknown" is not the same as "malicious". Many legitimate vendors ship poorly documented helpers. Say which category the evidence supports.

### 3. Read the logs around the complaint

Use `mac_read_log` to query the unified log for the suspect process and label, scoped to the complaint window. Look for repeated respawns, crash-and-relaunch loops driven by `KeepAlive`, and the parent that started the item.

An agent that respawns within seconds of being stopped is being relaunched by launchd or by a second component; find the parent before trying again.

### 4. Decide what may change

Review-only by default: Apple-owned launchd items, MDM-delivered configuration profiles, security software required by the organisation, and anything under System Integrity Protection.

Candidates for change: a user-owned launch agent belonging to software the user wants removed, a login item for a deleted application, a browser extension the user did not install, and a vendor updater the user explicitly declines.

Prefer the vendor's own uninstaller when one exists. It knows about components this audit cannot see.

### 5. Stage a reversible change, one item at a time

For each approved item:

1. Copy the plist and note its full path, ownership and permissions as evidence.
2. Stop the running job through launchd using its exact label rather than killing the process by name.
3. Move the plist out of the load path with `mac_move_file` into a dated holding directory outside the suspect application's own folder. Moving is reversible; deleting is not.
4. Record what was moved, from where, and when.

Do not batch-delete by vendor name, wildcard or pattern. Do not remove privacy database entries, disable System Integrity Protection, or edit protected system paths. Never `sudo rm -rf` a library directory to "clean up".

## Verification

Re-run `mac_persistence_snapshot` and confirm the item is absent from the load path and no longer running. Log out and back in, then reboot, and confirm it did not return. Confirm the holding directory contains readable copies of everything moved. Re-run the user's original workflow and confirm no dependent feature broke — printing, VPN, cloud sync, backup, security agent check-in and the menu-bar items the user relies on.

## Caveats

- MDM and configuration profiles recreate managed items by design; report the management source instead of fighting it locally.
- A valid signature and notarisation prove origin, not intent. Unsigned does not prove malice.
- Apple silicon system extensions require user approval and a reboot to change state; a pending approval looks like a failure but is not.
- Removing a launch agent does not uninstall the application, and removing an application does not remove its agents.
- Full Disk Access is required to read some locations; missing data must be reported as missing, not as clean.
- Background task management state on recent macOS versions is not fully visible without elevated access; note the gap.
- Some helpers are reinstalled by their parent application on next launch. That is a supported behaviour, not persistence-as-malware.

## Escalation

Escalate to the organisation's IT or security owner for a managed Mac, an MDM-delivered profile, a security agent, an unsigned binary in a system path, or any item that returns after a verified removal and reboot. Provide: macOS version and architecture, System Integrity Protection and enrolment state, the full enumeration, hashes and signature results for suspect binaries, log excerpts showing respawn behaviour, the holding directory location, and every change made with its timestamp. For a suspected compromise, stop the cleanup and hand off with evidence intact.

## Tools referenced

- `mac_persistence_snapshot`
- `mac_system_summary`
- `mac_app_list`
- `mac_file_hash`
- `mac_move_file`
- `mac_read_log`
- `activate_playbook`
