---
name: setup-openclaw/uninstall
description: Completely uninstall OpenClaw — stop services, remove config, uninstall CLI
platform: all
last_reviewed: 2026-08-05
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
- Remove the desktop app on macOS or Windows (if present)
- This cannot be undone

Use `ui_user_question` with options: **Yes, uninstall everything** / **Cancel**.
If the user cancels, use `ui_done` and stop.

## Step 2: Remove Everything

Execute all cleanup operations in this single step. Show progress via `ui_spa`
with `action_type: "RUN_STEP"` as you work through each sub-task.

### 2a. Stop and remove gateway service

First check if the `openclaw` CLI is available:
Run `shell_run` with `which openclaw` (on Windows: `where openclaw`).

**If CLI is available (preferred path — use the official uninstaller):**

OpenClaw ships a first-party uninstall command. Always preview first:

```bash
openclaw uninstall --dry-run --all
```

Show the user the plan it prints, then execute it non-interactively:

```bash
openclaw uninstall --all --yes --non-interactive
```

Scope flags let you remove only part of the install: `--service` (daemon/service
definition), `--state` (`~/.openclaw`), `--workspace`, `--app` (desktop app),
`--all` (everything). If `--all` succeeds, sub-steps 2b–2d are already covered —
skip to Step 3 and only use the manual steps to verify residue.

**If the CLI is NOT available, or `openclaw uninstall` fails (manual fallback):**

Run `shell_run` with `openclaw gateway stop` then `openclaw gateway uninstall`
if the CLI exists at all, ignoring errors, then continue with the manual
per-platform steps below.

On macOS:
- Check for service: `launchctl list | grep openclaw`
- Stop it: `launchctl bootout gui/$(id -u)/ai.openclaw.gateway` (ignore errors)
- Remove plist: `rm -f ~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- Also clean legacy: `rm -f ~/Library/LaunchAgents/com.openclaw.gateway.plist`

On Linux:
- Stop service: `systemctl --user disable --now openclaw-gateway.service` (ignore errors)
- Remove unit file: `rm -f ~/.config/systemd/user/openclaw-gateway.service`
- Reload: `systemctl --user daemon-reload`

On Windows, the gateway runs as a **Scheduled Task**, not a service:
```powershell
Get-ScheduledTask -TaskName 'OpenClaw Gateway' -ErrorAction SilentlyContinue |
  Unregister-ScheduledTask -Confirm:$false
```
The task points at `gateway.vbs`, which in turn calls `gateway.cmd` inside the
state directory, so removing the state dir (2b) without unregistering the task
leaves a task that fails on every logon. Unregister the task first.

### 2b. Delete configuration and state

The main state directory is `~/.openclaw` (or `$OPENCLAW_STATE_DIR` if set).

Run `shell_run` with `rm -rf ~/.openclaw`.
This removes config, state, workspace, and all stored data.

Also check for multi-profile directories (legacy feature):
Run `shell_run` with `ls -d ~/.openclaw-* 2>/dev/null || echo "none"`.
If any exist, delete each one: `rm -rf ~/.openclaw-*`.

### 2c. Uninstall CLI

Try each package manager in order (only one will have it installed):

1. npm: `npm list -g openclaw 2>/dev/null && npm rm -g openclaw`
2. pnpm: `pnpm list -g openclaw 2>/dev/null && pnpm remove -g openclaw`
3. bun: `bun remove -g openclaw 2>/dev/null`

If none succeed, warn the user the CLI may need manual removal.

Verify removal: `which openclaw` should return "not found".

### 2d. Remove desktop app (macOS and Windows)

On macOS, check for the desktop app:
Run `shell_run` with `ls /Applications/OpenClaw.app 2>/dev/null || echo "not found"`.
If it exists: `rm -rf /Applications/OpenClaw.app`.

On Windows there **is** a desktop app — the Windows Hub / OpenClaw Companion
(WinUI, Windows 10 20H2+). It installs per-user without admin rights, so it does
not appear in machine-wide uninstall lists:
```powershell
Get-AppxPackage *OpenClaw* | Select-Object Name, PackageFullName
Get-Package -Name '*OpenClaw*' -ErrorAction SilentlyContinue
```
Remove whichever one matches (`Remove-AppxPackage` for the packaged build, or
Settings → Apps → Installed apps for the installer build). Also check
`%LOCALAPPDATA%\Programs` for a leftover folder.

Skip on Linux (no desktop app).

## Step 3: Done

Show a done card summarizing what was removed:
- Gateway service: stopped and removed
- Configuration: `~/.openclaw/` deleted
- Multi-profile directories: cleaned (if any existed)
- CLI: uninstalled
- Desktop app: removed (if applicable, macOS or Windows)
- Reminder: if the user wants to reinstall later, activate `setup-openclaw`

## Escalation
- If gateway service won't stop: `kill $(pgrep -f openclaw)` as a last resort
- If files can't be deleted: check permissions, may need `sudo`
- If CLI uninstall fails: `rm -f $(which openclaw)` to remove the binary directly

## Tools referenced
- `shell_run` — stop services, delete files, uninstall packages
- `ui_user_question` with options — confirm uninstall
- `ui_spa` with RUN_STEP — show progress during automated cleanup
- `ui_done` — completion summary
