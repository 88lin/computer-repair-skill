---
name: local-data-audit
description: Audit a device for locally stored sensitive or company data — for offboarding or device reassignment
platform: all
last_reviewed: 2026-07-28
author: upstream-maintainers
source: bundled
emoji: 📂
---

# Local Data Audit

Scans the device for locally stored company data, personal files, and sensitive documents. Designed for employee offboarding or device reassignment — ensures nothing important is lost and no sensitive data remains on the device.

**Important**: This playbook only reads and reports. It does not delete anything without explicit user confirmation.

## When to activate
Employee offboarding, device reassignment, compliance audit, or when verifying that company data has been properly backed up before a wipe.

## Platform path map

Resolve the home directory and per-platform locations before scanning. `~` below
means the real home directory on each platform — do not paste POSIX paths into a
Windows shell.

| Target | Windows | macOS | Linux |
|---|---|---|---|
| Home | `$env:USERPROFILE` | `~` | `~` |
| Documents / Desktop / Downloads | `$env:USERPROFILE\Documents` etc. (may be redirected into OneDrive) | `~/Documents` etc. | `~/Documents` etc. (localized names live in `~/.config/user-dirs.dirs`) |
| Per-user app data | `$env:LOCALAPPDATA`, `$env:APPDATA` | `~/Library/Application Support`, `~/Library/Containers` | `~/.config`, `~/.local/share`, `~/.var/app` (Flatpak) |
| SSH keys | `$env:USERPROFILE\.ssh` | `~/.ssh` | `~/.ssh` |
| OS credential store | Credential Manager — list names only via `cmdkey /list` | Keychain — `security dump-keychain` is **not** allowed here; list items only | Secret Service / `~/.local/share/keyrings` — do not read |

## Standard check path

### 1. Check user profile directories
Scan the user's home directory for document-like files:
- Count files by type in the Documents / Desktop / Downloads paths from the table above.
- Report total size and file count for each directory.
- Flag large files (>100MB) that may need special handling.
- **Windows**: check for Known Folder redirection first — if Desktop/Documents point into OneDrive, the "local" data is already synced. `Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'`.
- **Linux**: user directories may be localized (`~/Documentos`). Read `~/.config/user-dirs.dirs` instead of assuming English names.

### 2. Check cloud sync status
Determine if the user has cloud storage synced locally:

| Service | Windows | macOS | Linux |
|---|---|---|---|
| OneDrive | `$env:OneDrive`, `$env:USERPROFILE\OneDrive*` | `~/Library/CloudStorage/OneDrive*` | rarely present (third-party clients such as `onedriver`, `rclone`) |
| Google Drive | `$env:USERPROFILE\My Drive`, `G:\` virtual drive | `~/Library/CloudStorage/GoogleDrive*`, `~/Google Drive` | `rclone` mounts, `google-drive-ocamlfuse` |
| Dropbox | `$env:USERPROFILE\Dropbox`, `$env:LOCALAPPDATA\Dropbox` | `~/Dropbox`, `~/.dropbox` | `~/Dropbox`, `~/.dropbox` |
| iCloud Drive | `$env:USERPROFILE\iCloudDrive` | `~/Library/Mobile Documents` | not supported |
| Nextcloud / Syncthing | `$env:USERPROFILE\Nextcloud` | `~/Nextcloud` | `~/Nextcloud`, `~/Sync` |

Report which services are synced and their local folder sizes. Synced data is generally safe (exists in the cloud), but confirm before removing.

### 3. Check for sensitive file patterns
Search for files that commonly contain sensitive data:
- Files with names containing: `password`, `credential`, `secret`, `key`, `token`, `.env`, `config`.
- Files with extensions: `.pem`, `.key`, `.pfx`, `.p12`, `.kdbx` (password databases).
- Check the SSH key path from the table above for private keys.
- **Windows also**: `cmdkey /list` (names only, never values), `$env:APPDATA\Microsoft\Crypto` for DPAPI material, `certutil -store -user My` for user certificates with private keys.
- **macOS also**: `~/Library/Keychains` presence and size; `~/.aws`, `~/.kube`, `~/.docker/config.json`.
- **Linux also**: `~/.gnupg`, `~/.aws`, `~/.kube`, `~/.docker/config.json`, `~/.netrc`, `~/.pgpass`.
- Check for database files (`.db`, `.sqlite`) in common locations.

Report found files **with paths, sizes and timestamps only**. Do not read, decrypt, or display file contents — the existence of a key is the finding.

### 4. Check application data
Look for locally stored application data that may contain company information. Report **sizes and paths only**, never contents.

| App class | Windows | macOS | Linux |
|---|---|---|---|
| Email | `$env:LOCALAPPDATA\Microsoft\Outlook` (`.ost`/`.pst`), `$env:APPDATA\Thunderbird` | `~/Library/Group Containers/*.Office`, `~/Library/Mail` | `~/.thunderbird`, `~/.local/share/evolution` |
| Chat | `$env:APPDATA\Slack`, `$env:APPDATA\Microsoft\Teams` | `~/Library/Application Support/Slack` / `Microsoft/Teams` | `~/.config/Slack`, `~/.config/Microsoft/Microsoft Teams` |
| Browser profiles | `$env:LOCALAPPDATA\Google\Chrome\User Data`, `...\Microsoft\Edge\User Data`, `$env:APPDATA\Mozilla\Firefox` | `~/Library/Application Support/Google/Chrome`, `~/Library/Safari` | `~/.config/google-chrome`, `~/.mozilla/firefox` |

Report which applications have significant local data stores. Do not open cookie stores, chat databases, or saved-password stores — that is out of scope for an offboarding size audit.

### 5. Check for code repositories
Search for git repositories that may contain company code:
- Look for `.git` directories in common locations (home, `src`, `code`, `projects`, `repos`, `dev`, `work`). On Windows also check `C:\dev`, `C:\src` and any WSL distro home via `\\wsl$\<distro>\home\<user>`.
- Report repository names and sizes.
- Note: code repos often contain credentials in config files or `.env` — flag these.

### 6. Summarize and recommend
Present a summary table:
- Which directories have company data
- Which cloud services are synced
- Any sensitive files found
- Recommended actions (backup, transfer ownership, or safe to wipe)

Ask the user whether to proceed with any cleanup, or just generate the report for the admin.

## Caveats
- **This is a read-only audit.** Nothing is deleted unless the user explicitly requests it.
- **Encrypted volumes** (FileVault, BitLocker) are searched normally when unlocked. If the device is encrypted and locked, this playbook cannot access the data.
- **Cloud-synced folders** may contain stubs (files not fully downloaded). The reported size may differ from what's actually on disk.
- **Time-sensitive**: Run this audit before disabling the user's account, as some cloud folders may become inaccessible after account deactivation.

> Steps 1-6 cover ~85% of locally stored company data. Most commonly missed: git repositories with embedded credentials and chat application local caches.

## Key signals
- **"Employee leaving, need to check for company data"** → run all steps, focus on cloud sync status (step 2) and sensitive files (step 3).
- **"Device being wiped, need to verify backup"** → focus on steps 1-2, confirm cloud sync is current before proceeding.
- **"Compliance audit"** → run all steps, generate full report for documentation.
- **"Developer offboarding"** → prioritize step 5 (code repos) and step 3 (credentials/keys).

## Escalation
If the audit reveals:
- Large amounts of unsynced local data — pause and arrange a backup before proceeding with offboarding.
- Credentials or secrets in plaintext — notify security team. These should be rotated, not just deleted.
- Personal data mixed with company data — consult HR/legal on data handling requirements.
- If the user is uncooperative or the device may be tampered with — involve IT security for supervised data collection.

## Tools referenced
- `shell_run` — file listing, directory size calculation, find/search (read-only)
- `win_disk_usage` / `mac_disk_usage` / `linux_disk_usage` — checking folder sizes
- `win_app_data_ls` / `mac_app_support_ls` — enumerate per-app data directories by size, metadata only
- `win_path_inventory` — Windows path/size/timestamp inventory without reading contents
- `ui_info` — report the audit table without asserting a cleanup decision
