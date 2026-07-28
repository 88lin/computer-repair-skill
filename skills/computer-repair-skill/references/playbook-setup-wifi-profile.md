---
name: setup-wifi-profile
description: Connect to a new Wi-Fi network including enterprise/WPA2-Enterprise networks
platform: all
category: network-identity-email
last_reviewed: 2026-03-07
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
Never interpolate the password into a transcript, shell command, process argument, or shell history. On macOS, prefer the system Wi-Fi UI or a host API that accepts the `secure_input` value without logging it; if an interactive prompt is required, let the user enter the password locally. On Windows, create the WLAN profile in a protected temporary location with `write_secret`, apply it with the native WLAN flow (`netsh wlan add profile filename=<path> user=current`), and remove the temporary secret only after connectivity is verified. On Linux with NetworkManager, let `nmcli` read the secret from a file or agent rather than passing it as an argument — `nmcli --ask device wifi connect '<SSID>'` prompts locally, whereas `nmcli device wifi connect '<SSID>' password '<PSK>'` leaks the key into the process list and shell history.

> Note: the password collected via secure_input can be written to a temp config file using `write_secret` if needed for scripted connection.

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
