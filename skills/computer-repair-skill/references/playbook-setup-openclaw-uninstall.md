---
name: setup-openclaw/uninstall
description: Completely uninstall OpenClaw — stop services, remove config, uninstall CLI
platform: all
last_reviewed: 2026-07-28
author: upstream-maintainers
source: bundled
emoji: 🦞
---

# Uninstall OpenClaw

Completely remove OpenClaw from the user's system: stop the gateway service,
remove service definitions, delete configuration and state, uninstall the CLI,
and clean up any leftover profiles. This is destructive and irreversible.

## When to activate
User wants to uninstall OpenClaw, remove OpenClaw, mentions "openclaw killer",
or wants to completely clean up / get rid of OpenClaw / 龙虾.

## Step 1: Confirm Uninstall

Ask the user to confirm they want to completely remove OpenClaw. Explain:
- This will stop the gateway service
- Delete all configuration and state (`~/.openclaw/`)
- Uninstall the CLI tool
- Remove the macOS desktop app (if present)
- This cannot be undone

Use `ui_user_question` with options: **Yes, uninstall everything** / **Cancel**.
If the user cancels, use `ui_done` and stop.

## Step 2: Offer a config snapshot before deleting

Deleting the state directory is irreversible, and users who "uninstall" often
still want their channel and model configuration back later. Before Step 3, offer
to copy the config out:

- **Windows**: `Copy-Item -Recurse "$env:USERPROFILE\.openclaw" "$env:USERPROFILE\Desktop\openclaw-config-backup-$(Get-Date -Format yyyyMMdd)"`
- **macOS / Linux**: `cp -a ~/.openclaw ~/Desktop/openclaw-config-backup-$(date +%Y%m%d)`

Then verify the copy exists and is non-empty before anything is removed. Warn the
user that the snapshot may contain API keys and tokens — it should be treated as a
secret and deleted once no longer needed. Do not print its contents.

If the user declines, record that they declined and continue.

## Step 3: Remove Everything

Execute all cleanup operations in this single step. Show progress via `ui_spa`
with `action_type: "RUN_STEP"` as you work through each sub-task.

### 3a. Stop and remove gateway service

First check if the `openclaw` CLI is available:
- **Windows**: `Get-Command openclaw -ErrorAction SilentlyContinue`
- **macOS / Linux**: `which openclaw`

**If CLI is available (easy path):**
Run `shell_run` with `openclaw gateway stop`. Ignore errors (may already be stopped).
Run `shell_run` with `openclaw gateway uninstall`. Ignore errors.

**If CLI is NOT available (manual path):**

On Windows — discover what actually exists rather than assuming a mechanism:
- Scheduled task: `Get-ScheduledTask -TaskName '*openclaw*' -ErrorAction SilentlyContinue`
- Service: `Get-Service -Name '*openclaw*' -ErrorAction SilentlyContinue`
- Startup entry: `Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' | Select-Object openclaw*`
- Stop and remove only the entries that were found, one at a time, and show the
  user each one first: `Stop-ScheduledTask`, then `Unregister-ScheduledTask -Confirm:$false`.
- Live process check: `Get-Process -Name '*openclaw*' -ErrorAction SilentlyContinue`

On macOS:
- Check for service: `launchctl list | grep openclaw`
- Stop it: `launchctl bootout gui/$(id -u)/ai.openclaw.gateway` (ignore errors)
- Remove plist: `rm -f ~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- Also clean legacy: `rm -f ~/Library/LaunchAgents/com.openclaw.gateway.plist`

On Linux:
- Stop service: `systemctl --user disable --now openclaw-gateway.service` (ignore errors)
- Remove unit file: `rm -f ~/.config/systemd/user/openclaw-gateway.service`
- Reload: `systemctl --user daemon-reload`

### 3b. Delete configuration and state

The main state directory is `.openclaw` in the user's home (or `OPENCLAW_STATE_DIR`
if that variable is set — check it first on every platform).

**List before deleting** so the user sees what is going away:
- **Windows**: `Get-ChildItem "$env:USERPROFILE\.openclaw" -Force | Select-Object Name, Length, LastWriteTime`
- **macOS / Linux**: `ls -la ~/.openclaw`

Then remove it:
- **Windows**: `Remove-Item -Recurse -Force "$env:USERPROFILE\.openclaw"`
- **macOS / Linux**: `rm -rf ~/.openclaw`

This removes config, state, workspace, and all stored data.

Also check for multi-profile directories (legacy feature):
- **Windows**: `Get-ChildItem "$env:USERPROFILE" -Directory -Filter '.openclaw-*' -Force`
- **macOS / Linux**: `ls -d ~/.openclaw-* 2>/dev/null || echo "none"`

If any exist, delete each one explicitly by its literal path. Do not run a
recursive delete against a wildcard the user has not seen expanded.

### 3c. Uninstall CLI

Try each package manager in order (only one will have it installed). These commands
are identical on all three platforms:

1. npm: `npm list -g openclaw` then `npm rm -g openclaw`
2. pnpm: `pnpm list -g openclaw` then `pnpm remove -g openclaw`
3. bun: `bun remove -g openclaw`

If none succeed, warn the user the CLI may need manual removal.

Verify removal:
- **Windows**: `Get-Command openclaw -ErrorAction SilentlyContinue` should return nothing.
- **macOS / Linux**: `which openclaw` should return "not found".

On Windows also check for a stale shim left behind in
`$env:APPDATA\npm` — npm global bin shims (`openclaw.cmd`, `openclaw.ps1`) sometimes
survive an uninstall and keep the command "working" while pointing at nothing.

### 3d. Remove desktop app

- **macOS**: check for the desktop app with `ls /Applications/OpenClaw.app 2>/dev/null || echo "not found"`. If it exists: `rm -rf /Applications/OpenClaw.app`. Also check `~/Applications`.
- **Windows**: verify whether a desktop build is even installed before acting — `winget list --name OpenClaw`, `Get-ChildItem "$env:LOCALAPPDATA\Programs" -Filter '*OpenClaw*'`, and Start Menu shortcuts under `$env:APPDATA\Microsoft\Windows\Start Menu\Programs`. If an installer entry exists, uninstall through it (`winget uninstall`) rather than deleting the program directory.
- **Linux**: skip — no desktop app. Also check `~/.local/share/applications` for a stale `.desktop` launcher if one was created manually.

Confirm the current OpenClaw release actually ships a build for the user's platform
before promising removal steps for it; this list follows what upstream documented at
`last_reviewed` time.

## Step 4: Done

Show a done card summarizing what was removed:
- Config snapshot: saved to `<path>` / declined by user
- Gateway service: stopped and removed
- Configuration: state directory deleted
- Multi-profile directories: cleaned (if any existed)
- CLI: uninstalled
- Desktop app: removed (if applicable)
- Reminder: if the user wants to reinstall later, activate `setup-openclaw`

If a config snapshot was taken, remind the user it may contain credentials and
should be stored securely or deleted.

## Escalation
- If gateway service won't stop:
  - **Windows**: `Get-Process -Name '*openclaw*' | Stop-Process` — show the matched processes to the user first.
  - **macOS / Linux**: `pgrep -af openclaw` to review matches, then `kill <PID>` for the specific PIDs. Avoid `kill $(pgrep -f openclaw)` blind — the pattern can match your own shell or an unrelated process.
- If files can't be deleted:
  - **Windows**: a running process usually holds the lock. Find it with `Get-Process` / Resource Monitor, close it, then retry. Do not take ownership of system paths to force a delete.
  - **macOS / Linux**: check permissions; `sudo` may be needed. Prefer fixing ownership on the user's own directory over running the whole uninstall as root.
- If CLI uninstall fails: remove the resolved binary or shim directly — `Get-Command openclaw | Select-Object Source` on Windows, `rm -f "$(which openclaw)"` on macOS/Linux — after confirming the path is inside a package-manager prefix and not a system directory.

## Tools referenced
- `shell_run` — stop services, delete files, uninstall packages
- `ui_user_question` with options — confirm uninstall
- `ui_spa` with RUN_STEP — show progress during automated cleanup
- `ui_done` — completion summary
