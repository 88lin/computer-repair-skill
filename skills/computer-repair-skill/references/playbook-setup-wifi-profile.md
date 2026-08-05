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

On Windows, check the SSID immediately after collecting it and before asking for the
password. The `netsh` `name=` parser cannot reliably address an SSID containing `"`, `=`
or `>`; stop this automated branch and direct the user to the Windows Wi-Fi UI:
```powershell
if ($ssid -match '["=>]') {
  throw 'SSID contains ", =, or >; netsh name= cannot parse it reliably. Use the Windows Wi-Fi UI to connect or remove this network.'
}
```

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
concatenate it into a shell command string: SSIDs can contain spaces, quotes, and XML
metacharacters. Pass it only as a separate quoted argument and escape it in XML.

Before generating temporary files, run the Windows profile preflight. This keeps the
user cancellation outside the import path, so there is no secret file to clean up if the
flow stops:
```powershell
$existingProfileOutput = & netsh.exe wlan show profile "name=$ssid" 2>&1
$profileExisted = $LASTEXITCODE -eq 0
$existingProfileInfo = ($existingProfileOutput | Out-String).Trim()
```

If `$profileExisted` is true, present `$existingProfileInfo` to the user without adding
`key=clear`, then call `ui_user_question` with `options`: **Replace existing profile** /
**Cancel**. On Cancel, stop. On **Replace existing profile**, continue to step 1. The
`netsh wlan add profile` call below overwrites this exact same-SSID profile in place; do
not delete it first. If `$profileExisted` is false, continue to step 1 without a prompt.

1. Generate profile and secret paths that contain no user input:
   ```powershell
   $tempToken = 'computer-repair-' + [guid]::NewGuid().ToString('N')
   $profilePath = Join-Path $env:TEMP ($tempToken + '.xml')
   $secretPath = Join-Path $env:TEMP ($tempToken + '.secret')
   ```
2. Call `write_secret` for `$secretPath` with format `{{value}}` and an ACL restricted
   to the current user. This is a temporary plaintext file; never print it or include
   its contents in a command argument.
3. Build the XML in memory and escape both text fields before writing it. `$ssid` is the
   exact value collected by `text_input`:
   ```powershell
   $ssidXml = [System.Security.SecurityElement]::Escape($ssid)
   $password = (Get-Content -LiteralPath $secretPath -Raw).TrimEnd([char[]]"`r`n")
   $passwordXml = [System.Security.SecurityElement]::Escape($password)
   $xml = @"
   <?xml version="1.0"?>
   <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
     <name>$ssidXml</name>
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
   [IO.File]::WriteAllText($profilePath, $xml, [Text.UTF8Encoding]::new($false))
   ```
4. Import and connect with argument-safe PowerShell invocation. `user=current` needs no
   elevation; use `user=all` only when every account needs the profile (admin required):
   ```powershell
   $profileImported = $false
   $profileExistedAtImport = $false
   try {
     & netsh.exe wlan show profile "name=$ssid" *> $null
     $profileExistedAtImport = $LASTEXITCODE -eq 0
     & netsh.exe wlan add profile "filename=$profilePath" user=current
     if ($LASTEXITCODE -ne 0) { throw "netsh wlan add profile failed: $LASTEXITCODE" }
     $profileImported = $true
     & netsh.exe wlan connect "name=$ssid"
     if ($LASTEXITCODE -ne 0) { throw "netsh wlan connect failed: $LASTEXITCODE" }
   } catch {
     if ($profileImported -and -not $profileExistedAtImport) {
       & netsh.exe wlan delete profile "name=$ssid" | Out-Null
     }
     throw
   } finally {
     Remove-Item -LiteralPath $profilePath, $secretPath -Force -ErrorAction SilentlyContinue
   }

   # Run Step 5 after this block. A failed connection removes a newly created profile;
   # a replaced profile is left in place so the user can correct its settings.
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
- If the SSID contains `"`, `=` or `>`, the `netsh name=` parser is unreliable. Use
  Windows Settings → Network & internet → Wi-Fi to connect or remove the profile
  manually; do not try to escape these characters in `name=`.
- If the imported profile is no longer wanted or connectivity verification fails, remove
  a newly created profile explicitly: `& netsh.exe wlan delete profile "name=$ssid"`.
  If an existing same-SSID profile was replaced, do not delete it automatically: the
  new settings are already in place and the old settings cannot be restored by this flow.
  Never delete another profile by wildcard.

If the target device is already in an offline setup or recovery environment, do not assume the host Agent can connect it. Give the user a manual GUI or technician checklist and verify the result when a usable host is available again.

## Tools referenced
- `shell_run` — network commands
- `ui_user_question` with `options` — confirm replacing an existing same-SSID profile
- `ui_user_question` with `text_input` — SSID, username
- `ui_user_question` with `secure_input` — Wi-Fi password
- `write_secret` — write password to config file if needed
- `mac_check_network` — verify connectivity
