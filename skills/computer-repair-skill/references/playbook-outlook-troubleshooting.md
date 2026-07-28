---
name: outlook-troubleshooting
description: Fix Outlook sync failures, crashes, stuck email, and profile corruption
platform: all
category: apps-updates-printing
last_reviewed: 2026-03-04
author: upstream-maintainers
source: bundled
emoji: 📧
---

# Outlook Troubleshooting

## When to activate
User reports: Outlook won't sync, email stuck in outbox, calendar not updating, Outlook crashes, search not working, "need password" loop, Outlook slow, OST corrupted.

## Quick check
Verify this is an Outlook-specific issue, not a network problem:
- Can the user access email at https://outlook.office.com in a browser?
- If webmail also fails → this is a server or account issue, not an Outlook client issue. Check https://status.office.com for M365 outages.
- If webmail works but Outlook doesn't → proceed with fix path below.

Treat credential removal, cache/profile changes, and Office repair as state changes. Inspect first, show the exact target and rollback, and wait for approval before changing them. Never ask the user to paste a password or token into chat.

## Standard fix path (try in order)

### 1. Restart Outlook
Quit Outlook completely (not just close the window), then relaunch.
- macOS: Cmd+Q, or force-quit via Activity Monitor if unresponsive.
- Windows: check Task Manager for lingering OUTLOOK.EXE processes and end them.
This alone fixes transient sync hangs, stuck outbox items, and temporary auth failures.

### 2. Clear cached credentials
The #1 cause of "keeps asking for password" loops.
- macOS: Keychain Access → search "Microsoft" or "Exchange" or the user's email. List matching metadata first; delete only the exact approved entries, then restart Outlook.
- Windows: Control Panel → Credential Manager → Windows Credentials → list "MicrosoftOffice" entries and exact matches for the account. Remove only the approved entries, then restart Outlook.
- If using M365 with MFA, have the user sign in at https://outlook.office.com first to confirm credentials work.

### 3. Rebuild the cache (OST/local data)
Outlook stores a local copy of the mailbox. If corrupted, sync breaks.
- macOS: Outlook → Preferences → Accounts → select account → "Empty Cache" only after confirming the mailbox is synchronized and the user approves the cache reset.
- Windows: File → Account Settings → Account Settings → Data Files tab → note the `.ost` path. Confirm the mailbox is synchronized and a rollback copy is available; after approval, close Outlook and rename the exact `.ost` file to `.ost.bak` (never delete it), then reopen Outlook.
- **Do not assume this is safe for every account.** Confirm the account type, synchronization state and backup before resetting local data.

### 4. Rebuild the profile
If cache rebuild didn't fix it, the profile itself may be corrupted.
- macOS: Outlook profiles live in `~/Library/Group Containers/UBF8T346G9.Office/Outlook/Outlook 15 Profiles/`. Verify server sync and local-only archives, record the exact path, then rename it only after approval. Relaunch Outlook and re-add the account.
- Windows: After approval, use Control Panel → Mail → Show Profiles to add a new profile, retain the old profile for rollback, and select the new one for the test.
- Preserving the old profile makes rollback possible but does not prove that local-only data is backed up; verify archives and synchronization first.

### 5. Repair Office installation
If Outlook still crashes or misbehaves with a fresh profile:
- macOS: After checking the current version and licensing, propose the official Office download URL and reinstall only after the user approves the installer, impact and rollback.
- Windows: Settings → Apps → Microsoft Office → Modify → propose "Online Repair" (not Quick Repair) with the expected downtime and approval before starting.

Apply one step at a time and stop when the original workflow is verified.

## Caveats
- If the OST file is >10 GB, step 3 (cache rebuild) takes 30+ minutes. Warn the user and suggest doing it over lunch or end of day.
- If this is a **shared mailbox** issue (not the user's own mailbox), it's almost always a permissions problem, not a profile issue. Don't rebuild — check if the user still has delegate access.
- If Outlook crashes on launch and you can't even open it: on Windows, try `outlook.exe /safe` to start in Safe Mode with add-ins disabled. Common culprit add-ins: antivirus email scanners, CRM plugins, old Teams add-in.
- If the user says "search doesn't work" but everything else is fine, that's a search index issue:
  - macOS: Spotlight indexes Outlook data. Reindex: Outlook → Preferences → Spotlight rebuild.
  - Windows: File → Options → Search → Indexing Options → Advanced → Rebuild.

## Key signals
- **"It worked yesterday"** → likely an expired auth token. Jump to step 2 (credentials).
- **"Nobody in the office can send email"** → server-side outage, not local. Check https://status.office.com before touching anything.
- **"Only calendar won't sync"** → usually permissions on a shared calendar, not a sync issue. Have the calendar owner re-share it.
- **"Keeps crashing after macOS/Windows update"** → Office version may be incompatible with the new OS. Jump to step 5 (repair/update Office).
- **"Email stuck in outbox"** → check attachment size first (>25 MB fails for most providers). If small, toggle Work Offline on/off (Outlook menu), then back online.
- **"Your mailbox is full"** → Exchange quota hit. User needs to archive or delete old mail. This is not an Outlook bug.

## Verification
After each approved change, verify webmail access, Outlook launch, send/receive, calendar sync and search. Record whether credentials, cache files or profiles were changed and keep the rollback copy until the user confirms the result.

## Escalation
If all 5 steps fail:
- Check if the problem is account-specific: try adding a different email account to the same Outlook. If the other account works, the issue is server-side for that specific account.
- For enterprise/M365 accounts: the IT admin may need to check Conditional Access policies, app passwords, or account lockouts in Azure AD.
- For persistent crashes: collect the crash log and Office version number for Microsoft support.

## Tools referenced
- `shell_run` — inspect processes, versions and platform diagnostics
- `web_fetch` — read the explicitly approved Microsoft status or download page
- `ui_user_question` — request account type, approval and non-secret choices
- `secure_input` — collect a password only through the host's masked input
- `ui_spa` — show the proposed change, impact, rollback and verification
