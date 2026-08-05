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

**Windows** — build a WLAN profile XML and import it. Write the file with `write_secret` so
the key never passes through a command line:

1. `write_secret` to a protected temp path (e.g. `%TEMP%\wlan-<ssid>.xml`, ACL'd to the
   current user) with this template — `{{value}}` is the `secure_input` password:
   ```xml
   <?xml version="1.0"?>
   <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
     <name>SSID_HERE</name>
     <SSIDConfig><SSID><name>SSID_HERE</name></SSID></SSIDConfig>
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
         <keyMaterial>{{value}}</keyMaterial>
       </sharedKey>
     </security></MSM>
   </WLANProfile>
   ```
2. Import and connect. `user=current` needs no elevation; only use `user=all` when the
   profile must be available to every account on the machine, which requires admin:
   ```powershell
   netsh wlan add profile filename="$env:TEMP\wlan-<ssid>.xml" user=current
   netsh wlan connect name="<SSID>"
   ```
3. After Step 5 confirms connectivity, delete the temp file:
   ```powershell
   Remove-Item "$env:TEMP\wlan-<ssid>.xml" -Force
   ```

Delete the file even if the connection failed — it holds the plaintext passphrase.
For WPA2 Enterprise the profile needs an `<OneX>` EAP block instead of `<sharedKey>`;
those profiles are usually supplied by the organization, so ask for the official one
rather than hand-writing it.

## Step 5: Verify connectivity
Run a connectivity test (ping, curl, or DNS lookup) to confirm the connection works.
If the connection fails:
- Wrong password → ask user to re-enter
- Enterprise auth failed → check username format (may need domain\user or user@domain)
- Captive portal → tell user to open a browser

If the target device is already in an offline setup or recovery environment, do not assume the host Agent can connect it. Give the user a manual GUI or technician checklist and verify the result when a usable host is available again.

## Tools referenced
- `shell_run` — network commands
- `ui_user_question` with `text_input` — SSID, username
- `ui_user_question` with `secure_input` — Wi-Fi password
- `write_secret` — write password to config file if needed
- `mac_check_network` — verify connectivity
