---
name: windows-update-troubleshooting
description: Fix stuck Windows Updates, failed installations, and update service errors
platform: windows
category: apps-updates-printing
last_reviewed: 2026-07-28
author: upstream-maintainers
source: bundled
emoji: 🔄
---

# Windows Update Troubleshooting

## When to activate
User reports: Windows Update stuck, update won't install, update error code, system slow after update, "something went wrong" during update, pending restart that won't complete.

## Quick check
Run `shell_run` with `powershell -Command "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID, Description, InstalledOn"` to see recent updates.

For a read-only view of what is still pending, run `shell_run` with:

```powershell
(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0 AND IsHidden=0").Updates |
  Select-Object -First 10 Title, IsDownloaded, @{ n = 'SizeMB'; e = { [math]::Round($_.MaxDownloadSize / 1MB, 1) } }
```

- If recent updates installed fine → problem may be a specific failed update. Ask for the error code.
- If no recent updates → update service may be stuck. Proceed with fix path.
- Do **not** reach for `Get-WindowsUpdate` / `Install-WindowsUpdate`: those come from the third-party `PSWindowsUpdate` module, not from Windows. On a stock machine they fail, and this skill does not silently install third-party modules.

Also check `win_system_info` for the OS build — some fixes only apply to Windows 11 24H2 and newer.

Also check `win_disk_usage` — Windows Update needs 10-20 GB free.

## Standard fix path (try in order)

### 1. Check for pending reboot
Run `shell_run` with `powershell -Command "Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'"`.
- If `True` → a previous update is waiting for reboot. Reboot first, then check if the problem is resolved.
- This is the #1 cause of "updates won't install" — a pending reboot blocks new updates.

### 2. Restart Windows Update services
Run `win_restart_service` for `wuauserv` (Windows Update).
Also restart these related services via `shell_run` in an **elevated** PowerShell:
```powershell
Restart-Service -Name bits -Force
Restart-Service -Name cryptSvc -Force
```
- `wuauserv` — the update engine
- `bits` — Background Intelligent Transfer Service (downloads updates)
- `cryptSvc` — Cryptographic Services (verifies update signatures)

Restarting these three services fixes most transient update failures.

### 3. Clear the update cache
If restarting services didn't help, clear the cached update files.
Confirm with the user first — this is a state change, and the next update run has to re-download everything.
Run `shell_run` in an **elevated** PowerShell with:
```powershell
Stop-Service -Name wuauserv, bits, cryptSvc -Force
Rename-Item -LiteralPath 'C:\Windows\SoftwareDistribution' -NewName 'SoftwareDistribution.old'
Rename-Item -LiteralPath 'C:\Windows\System32\catroot2' -NewName 'catroot2.old'
Start-Service -Name cryptSvc, bits, wuauserv
```
This forces Windows to re-download updates from scratch. Rename — do not delete: if the machine gets worse, stop the services again and rename the folders back.
- If `Rename-Item` fails with "being used by another process", `TrustedInstaller` or `msiserver` still holds a handle. Reboot and retry before escalating; do not force-unlock the handle.
- The `.old` folders can be removed after updates succeed, following the Inspect Before Delete steps in `safety-policy.md`.

### 4. Run the Windows Update troubleshooter (legacy platform — check availability first)
The MSDT troubleshooters are deprecated: Microsoft began redirecting them to the Get Help platform in 2023 and planned removal of MSDT itself, so on current Windows 11 builds the pack is often gone.
Probe before using it — run `shell_run` with `powershell -Command "Get-Command Get-TroubleshootingPack -ErrorAction SilentlyContinue; Test-Path 'C:\Windows\diagnostics\system\WindowsUpdate'"`.
- Both present → `shell_run` with `powershell -Command "Get-TroubleshootingPack -Path 'C:\Windows\diagnostics\system\WindowsUpdate' | Invoke-TroubleshootingPack -Unattended"`.
- Either missing → tell the user to open **Settings → System → Troubleshoot → Other troubleshooters → Windows Update** and run it there. There is no scriptable replacement; do not try to reinstall the legacy pack.

### 5. DISM and SFC repair
If updates still fail, the system image may be corrupted:
Run `shell_run` with:
```powershell
DISM /Online /Cleanup-Image /RestoreHealth
sfc /scannow
```
- DISM repairs the Windows component store (downloads clean copies from Windows Update).
- SFC repairs protected system files using the component store.
- Run DISM first, then SFC. This order matters.
- DISM can take 15-30 minutes. Warn the user.

> Steps 1-3 resolve ~80% of Windows Update issues. #1 cause: pending reboot blocking new updates.

## Caveats
- **Error code 0x80070057** — invalid parameter. Usually caused by corrupted update cache. Step 3 fixes it.
- **Error code 0x800f081f** — source files not found. DISM can't download repair files. Try: `DISM /Online /Cleanup-Image /RestoreHealth /Source:C:\path\to\mounted\iso\sources\install.wim` with a mounted Windows ISO.
- **"Updates are managed by your organization"** — Group Policy or MDM is controlling updates. Nothing to fix locally — contact IT admin.
- **Metered connection blocking updates** — Windows won't download large updates on metered connections. Settings → Network & Internet → check if current connection is set to metered.
- **Update loops (install → reboot → install again)** — a broken update is being retried. Uninstall it from Settings → Windows Update → Update history → Uninstall updates, then pause updates for 1-2 weeks so the same build is not immediately re-offered. `Hide-WindowsUpdate` is a `PSWindowsUpdate` (third-party) cmdlet and is not available on a stock machine; do not install it without the user reviewing the module first.
- **Elevation** — steps 2, 3 and 5 all require an elevated shell. Without it, `Stop-Service` and `Rename-Item` fail with access denied and the run looks like a Windows Update fault when it is not.

## Key signals
- **"Stuck at a percentage for hours"** → if actively downloading/installing, wait up to 2 hours. If truly stuck, force-reboot and retry. Step 3 to clear cache.
- **"Blue screen after update"** → boot to Safe Mode (hold Shift + click Restart), uninstall the problematic update from Settings → Recovery → Advanced startup.
- **"Not enough space"** → run `win_disk_usage`. Clear temp files with `win_clear_caches`. Windows Update needs 10-20 GB free.
- **"Updates disabled by admin"** → check `win_service_list` for `wuauserv`. If disabled, it's likely a policy decision — contact IT.
- **Specific KB error** → search the error code. Microsoft documents most update errors with specific fixes.

## Tools referenced
- `shell_run` — run elevated PowerShell commands for update management
- `win_restart_service` — restart Windows Update and related services
- `win_disk_usage` — check free space
- `win_service_list` — check Windows Update service status
- `win_clear_caches` — clear temp files to free space
- `win_system_info` — check Windows version and build

## Escalation
If all steps fail:
- Download the `.msu` manually from the Microsoft Update Catalog (https://catalog.update.microsoft.com) and install it with `wusa.exe '<PATH>.msu'`, or scriptably with `DISM /Online /Add-Package /PackagePath:'<PATH>.msu'`. Verify the KB number matches the OS build before installing.
- For feature updates (e.g., 23H2 → 24H2): download the Update Assistant or Media Creation Tool from Microsoft.
- For managed PCs: WSUS or SCCM may be blocking updates. Contact IT admin.
- Persistent BSOD after updates: may need system restore or Windows repair install.
