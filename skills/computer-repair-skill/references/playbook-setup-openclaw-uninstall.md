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
Run `shell_run` with `command -v openclaw` on macOS/Linux, or `where.exe openclaw`
on Windows.

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
`--all` (everything). A successful `--all` covers the OpenClaw-managed service,
state and workspace cleanup, but it does **not** replace the package-manager CLI
uninstall or the Windows app/package checks below. Continue with 2b to review custom
paths and profiles, then always run 2c and 2d.

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

On Windows, the gateway runs as a **Scheduled Task**, not a service. Enumerate all
candidate tasks first and inspect their actions:
```powershell
Get-ScheduledTask -ErrorAction SilentlyContinue |
  Where-Object {
    $_.TaskName -like 'OpenClaw Gateway*' -and
    ($_.Actions.Execute -match '(?i)openclaw|gateway\.vbs|gateway\.cmd' -or
     $_.Actions.Arguments -match '(?i)openclaw|gateway\.vbs|gateway\.cmd')
  } |
  Select-Object TaskPath, TaskName, Actions
```
The task points at `gateway.vbs`, which in turn calls `gateway.cmd` inside the
state directory, so removing the state dir (2b) without unregistering the task
leaves a task that fails on every logon. Unregister the task first.

### 2b. Delete configuration and state

The main state directory is `~/.openclaw`, or the directory derived from the
environment overrides below. Resolve and display every exact path before deleting it;
never pass a wildcard or an unreviewed parent directory to a recursive delete.

Resolve paths in this order:
- `OPENCLAW_STATE_DIR` — exact state directory override.
- Otherwise `OPENCLAW_HOME` — use `$OPENCLAW_HOME/.openclaw`.
- Otherwise the default `$HOME/.openclaw`.
- `OPENCLAW_CONFIG_PATH` is a separate config file override. Inspect that exact file
  and remove it only after confirmation; it is not a directory to recurse into.

On macOS/Linux:
```bash
home_dir="${OPENCLAW_HOME:-$HOME}"
state_dir="${OPENCLAW_STATE_DIR:-$home_dir/.openclaw}"
config_path="${OPENCLAW_CONFIG_PATH:-$state_dir/openclaw.json}"
if [ -e "$state_dir" ]; then
  state_dir="$(cd -P -- "$state_dir" 2>/dev/null && pwd)" || {
    echo "State directory cannot be resolved; stop before deleting." >&2
    exit 1
  }
  case "$state_dir" in
    /|"$HOME"|"$home_dir")
      echo "Refusing to delete filesystem or home root: $state_dir" >&2
      exit 1
      ;;
  esac
  printf 'Review state: %s\n' "$state_dir"
else
  printf 'State already absent (possibly removed by openclaw --all): %s\n' "$state_dir"
fi
printf 'Review config: %s\n' "$config_path"
```

On Windows:
```powershell
$homeDir = if ([string]::IsNullOrWhiteSpace($env:OPENCLAW_HOME)) {
  $env:USERPROFILE
} else { $env:OPENCLAW_HOME }
$stateDir = if ([string]::IsNullOrWhiteSpace($env:OPENCLAW_STATE_DIR)) {
  Join-Path $homeDir '.openclaw'
} else { $env:OPENCLAW_STATE_DIR }
$configPath = if ([string]::IsNullOrWhiteSpace($env:OPENCLAW_CONFIG_PATH)) {
  Join-Path $stateDir 'openclaw.json'
} else { $env:OPENCLAW_CONFIG_PATH }
$resolvedHome = (Resolve-Path -LiteralPath $homeDir -ErrorAction Stop).Path.TrimEnd('\')
if (Test-Path -LiteralPath $stateDir) {
  $resolvedState = (Resolve-Path -LiteralPath $stateDir -ErrorAction Stop).Path
  $stateRoot = [IO.Path]::GetPathRoot($resolvedState).TrimEnd('\')
  if ($resolvedState.TrimEnd('\') -in @($stateRoot, $resolvedHome)) {
    throw "Refusing to delete filesystem or home root: $resolvedState"
  }
  Write-Host "Review state: $resolvedState"
} else {
  Write-Host "State already absent (possibly removed by openclaw --all): $stateDir"
}
Write-Host "Review config: $configPath"
```

After confirmation, delete only the reviewed state directory and, if it is outside that
directory, the reviewed `config_path`. Also inspect multi-profile state directories
using a bounded listing (for example `~/.openclaw-*` directly under the selected home),
show every resolved candidate, and delete each one only after the user confirms that
profile. Never use `rm -rf ~/.openclaw-*` or an equivalent wildcard deletion.

For a reviewed existing state directory, run the platform-specific deletion with the
resolved literal path (skip it when the path is already absent):
```bash
if [ -n "${state_dir:-}" ] && [ -d "$state_dir" ]; then
  rm -rf -- "$state_dir"
fi
if [ -f "$config_path" ] && [ "$config_path" != "$state_dir/openclaw.json" ]; then
  rm -f -- "$config_path"
fi
```
```powershell
if ($resolvedState -and (Test-Path -LiteralPath $resolvedState -PathType Container)) {
  Remove-Item -LiteralPath $resolvedState -Recurse -Force
}
if ((Test-Path -LiteralPath $configPath -PathType Leaf) -and
    (-not $resolvedState -or ([IO.Path]::GetFullPath($configPath) -ne [IO.Path]::GetFullPath((Join-Path $resolvedState 'openclaw.json'))))) {
  Remove-Item -LiteralPath $configPath -Force
}
```

The service cleanup must cover every profile. On macOS, list and inspect matching
LaunchAgents (`ai.openclaw.gateway*.plist` and legacy `com.openclaw.gateway*.plist`),
boot out each exact loaded label, then remove only the reviewed plist files. On Linux,
list every user unit matching `openclaw*.service`, disable/stop each exact unit, run
`systemctl --user daemon-reload`, and remove only matching unit files under
`~/.config/systemd/user`. On Windows, after review, unregister each exact task from the
listing above with `Unregister-ScheduledTask -TaskPath <reviewed-path> -TaskName <reviewed-name> -Confirm:$false`.
Do not remove unrelated tasks, services, or launch agents.

### 2c. Uninstall CLI

On macOS/Linux, try each package manager in order (only one will have it installed):

1. npm: `npm list -g openclaw 2>/dev/null && npm rm -g openclaw`
2. pnpm: `pnpm list -g openclaw 2>/dev/null && pnpm remove -g openclaw`
3. bun: `bun remove -g openclaw 2>/dev/null`

On Windows, use PowerShell without Unix redirection:
```powershell
foreach ($manager in @('npm', 'pnpm', 'bun')) {
  $command = Get-Command $manager -ErrorAction SilentlyContinue
  if (-not $command) { continue }
  & $manager list -g openclaw --depth=0
  if ($LASTEXITCODE -eq 0) {
    if ($manager -eq 'npm') { & npm rm -g openclaw }
    elseif ($manager -eq 'pnpm') { & pnpm remove -g openclaw }
    else { & bun remove -g openclaw }
    break
  }
}
```

If none succeed, warn the user the CLI may need manual removal.

Verify removal with `command -v openclaw || echo "not found"` on macOS/Linux. On
Windows run `where.exe openclaw`; if `$LASTEXITCODE -ne 0`, report `not found`.

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
`%LOCALAPPDATA%\Programs` for a leftover folder. These checks are required even when
`openclaw uninstall --all` reported success.

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
- If CLI uninstall fails: report the exact executable path and use the owning package
  manager or the vendor's documented uninstaller; never delete an unresolved path.

## Tools referenced
- `shell_run` — stop services, delete files, uninstall packages
- `ui_user_question` with options — confirm uninstall
- `ui_spa` with RUN_STEP — show progress during automated cleanup
- `ui_done` — completion summary
