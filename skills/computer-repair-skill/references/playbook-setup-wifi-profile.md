---
name: setup-wifi-profile
description: Connect to a new Wi-Fi network including enterprise/WPA2-Enterprise networks
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 📶
---

# Set Up Wi-Fi Network

## When to activate
User needs to connect to Wi-Fi, join a corporate network, enter Wi-Fi credentials, or set up WPA2-Enterprise / 802.1x.

## Step 1: Identify the network type
Ask the user what kind of network they're connecting to:
- Home/simple Wi-Fi (WPA2 Personal) — just needs password
- Work/school Wi-Fi (WPA2 Enterprise) — needs username and password
- Guest/captive portal — needs browser sign-in

## Step 2: Collect network name
Ask for the Wi-Fi network name (SSID). Use `text_input` — this is not sensitive.

## Step 3: Collect credentials
For WPA2 Personal: collect the Wi-Fi password using `secure_input` (secret_name: "wifi_password").
For WPA2 Enterprise: collect username via `text_input`, then password via `secure_input`.

## Step 4: Connect to the network
Never interpolate the password into a transcript, shell command, process argument, or shell history.

**macOS** — prefer the system Wi-Fi UI, or let the user type the password into the native
prompt locally. Do **not** use `networksetup -setairportnetwork <device> <ssid> <password>`:
the password becomes a process argument visible to every user via `ps`.

**Windows** — build a WLAN profile XML and import it. Never put the password in a
command argument, transcript, or shell history. Do not use the SSID as a filename or
interpolate it into a shell command: SSIDs can contain spaces, quotes, and XML
metacharacters.

1. Generate profile and secret paths that contain no user input:
   ```powershell
   $profileName = 'computer-repair-' + [guid]::NewGuid().ToString('N')
   $profilePath = Join-Path $env:TEMP ($profileName + '.xml')
   $secretPath = Join-Path $env:TEMP ($profileName + '.secret')
   ```
2. Call `write_secret` for `$secretPath` with format `{{value}}` and an ACL restricted
   to the current user. This is a temporary plaintext file; never print it or include
   its contents in a command argument.
3. Build the XML in memory and escape both text fields before writing it. `$ssid` is the
   exact value collected by `text_input`:
   ```powershell
   $ssidXml = [System.Security.SecurityElement]::Escape($ssid)
   $password = Get-Content -LiteralPath $secretPath -Raw
   $passwordXml = [System.Security.SecurityElement]::Escape($password)
   $xml = @"
   <?xml version="1.0"?>
   <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
     <name>$profileName</name>
     <SSIDConfig><SSID><name>$ssidXml</name></SSID></SSIDConfig>
     <connectionType>ESS</connectionType>
     <connectionMode>auto</connectionMode>
     <MSM><security>
       <authEncryption>
         <authentication>WPA2PSK</authentication>
         <encryption>AES</encryption>
         <useOneX>false</useOneX>
       </authEncryption>
       <sharedKey>
         <keyType>passPhrase</keyType>
         <protected>false</protected>
         <keyMaterial>$passwordXml</keyMaterial>
       </sharedKey>
     </security></MSM>
   </WLANProfile>
   "@
   Set-Content -LiteralPath $profilePath -Value $xml -Encoding UTF8 -NoNewline
   ```
4. Import and connect with argument-safe PowerShell invocation. `user=current` needs no
   elevation; use `user=all` only when every account needs the profile (admin required):
   ```powershell
   $profileImported = $false
   try {
     & netsh.exe wlan add profile "filename=$profilePath" user=current
     if ($LASTEXITCODE -ne 0) { throw "netsh wlan add profile failed: $LASTEXITCODE" }
     $profileImported = $true
     & netsh.exe wlan connect "name=$profileName"
     if ($LASTEXITCODE -ne 0) { throw "netsh wlan connect failed: $LASTEXITCODE" }
   } catch {
     if ($profileImported) {
       & netsh.exe wlan delete profile "name=$profileName" | Out-Null
     }
     throw
   } finally {
     Remove-Item -LiteralPath $profilePath, $secretPath -Force -ErrorAction SilentlyContinue
   }

   # Run Step 5 after this block. A failed connection removes the imported profile.
   # If later verification fails, delete the profile explicitly and regenerate it.
   ```

The `finally` block deletes both temporary files even when import or connection fails.
For WPA2 Enterprise the profile needs an `<OneX>` EAP block instead of `<sharedKey>`;
those profiles are usually supplied by the organization, so ask for the official one
rather than hand-writing it.

## Step 5: Verify connectivity
Run a connectivity test (ping, curl, or DNS lookup) to confirm the connection works.
If the connection fails:
- Wrong password → ask user to re-enter
- Enterprise auth failed → check username format (may need domain\user or user@domain)
- Captive portal → tell user to open a browser
- If the imported profile is no longer wanted or connectivity verification fails, remove
  this run's profile explicitly: `& netsh.exe wlan delete profile "name=$profileName"`.
  Do not delete other profiles by SSID or by wildcard.

If the target device is already in an offline setup or recovery environment, do not assume the host Agent can connect it. Give the user a manual GUI or technician checklist and verify the result when a usable host is available again.

## Tools referenced
- `shell_run` — network commands
- `ui_user_question` with `text_input` — SSID, username
- `ui_user_question` with `secure_input` — Wi-Fi password
- `write_secret` — write password to config file if needed
- `mac_check_network` — verify connectivity
