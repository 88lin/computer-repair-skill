---
name: windows-configuration-review
description: Review reversible Windows privacy, AI, performance, and usability settings with version gates, diff, and rollback
platform: windows
last_reviewed: 2026-09-09
author: computer-repair-skill-maintainers
source: local
---

# Windows Configuration Review

## When to activate
Use for “optimize Windows”, debloat, privacy, power-plan, taskbar, update or gaming-tweak requests, requests to turn Windows AI features such as Recall or Copilot on or off, and when importing a configuration from another machine.

## Quick check
Collect Windows edition/build, hardware, BitLocker/recovery status, current power plan, security state, managed-policy indicators and available disk space. A setting supported on one build or GPU is not automatically safe on another.

## Standard diagnostic path

### 1. Build a setting catalog
For each proposed setting record its current value, target value, owner, scope (user or machine), dependency, risk (`low`, `medium`, `high`), restart requirement and documented revert. Prefer native Windows controls and vendor documentation over tweak-pack folklore. Also record the evidence that justifies it, the single-variable test that can validate it, and the user workflow that must remain unchanged. A setting copied from another build, GPU or laptop is a proposal, not a baseline.

### 2. Review imported configuration
Treat config files as untrusted data. Parse them without executing embedded commands, reject unknown fields, show a current-versus-proposed diff, and filter settings incompatible with the current build or hardware. Never silently apply a whole profile.

### 3. Audit Windows AI features separately
Requests to turn off Recall, Copilot or other Windows AI features are common and are configuration work, not debloating. Report the current state first: the documented policy values under `HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsAI` (for example `AllowRecallEnablement`), the optional-feature state for Recall, the installed Copilot packages with publisher and version, and whether any of it is already managed by policy. Note the Windows edition, because policy-based controls behave differently on Home builds.

Prefer the documented Settings UI or Group Policy path, and record the exact current value before changing it. Restore by writing the recorded value back — never delete the whole `WindowsAI` policy key, because it can hold other managed values that are unrelated to the requested change. Do not remove Copilot by filtering Appx package names for a vendor substring; confirm each package's identity, then use the documented per-package uninstall and record how to reinstall it. Uninstalling an AI component that ships as a Windows optional feature can be re-applied by a later cumulative update; say so instead of promising a permanent result.

### 4. Create a recovery point
For registry or policy changes, export only the exact keys with `win_registry_snapshot`; record services, tasks, power plans and relevant policy values. A system restore point is an additional option, not a substitute for a verified backup. Do not place backups in a directory that the proposed cleanup will touch.

### 5. Apply in small batches
Obtain one confirmation covering the displayed list. Apply low-risk user settings first, then pause and verify. Keep high-risk settings separate. Do not change Defender, SmartScreen, UAC, firewall, Windows Update, CPU mitigations, core isolation, secure boot, activation, trust chains or force-remove Edge. Do not run a remote installer or `irm | iex`.

A tweak pack shipping an "unapply" script is not a verified rollback. Read the revert path before applying: reject any revert that deletes a whole registry or policy key, re-enables a feature through an unaudited command, or relaunches PowerShell with `-ExecutionPolicy Bypass`. Record the concrete inverse of each change yourself.

### 6. Revert deliberately
If a setting breaks a workflow, use the recorded inverse or import the verified backup. Do not “reset everything” by deleting registry branches or changing every service to a guessed default.

## Verification
Re-read each setting, compare the recorded diff, and test the user's stated workflow plus security/update status. For changes requiring reboot, verify after reboot and preserve the before/after manifest.

## Caveats
- Privacy changes can break Store, notifications, search, accessibility, enterprise management or diagnostics.
- Windows AI and Copilot surfaces change name, packaging and policy support between builds; verify the current control against vendor documentation instead of reusing a tweak from an older build.
- Power and gaming changes can affect thermals, battery life, sleep and anti-cheat compatibility.
- Appx removal, ISO customization and autounattend generation are deployment work, not routine repair; route them to a reviewed build pipeline.

## Escalation
Escalate high-risk security controls, managed devices, missing recovery media, BitLocker recovery uncertainty, unsupported Windows builds, or a request for activation/cracked software.

## Tools referenced
- `win_system_info`
- `win_registry_snapshot`
- `win_service_list`
- `win_scheduled_task_list`
- `win_policy_list`
- `shell_run`
- `ui_spa`
