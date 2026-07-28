---
name: windows-network-diagnostics
description: Systematic Windows connectivity troubleshooting for adapters, DHCP, routes, DNS, proxy, VPN, and HTTP
platform: windows
last_reviewed: 2026-07-26
author: computer-care-maintainers
source: local
---

# Windows Network Diagnostics

## When to activate
User reports no internet, limited connectivity, DNS failures, Wi-Fi or Ethernet drops, VPN side effects, proxy errors, or one service not loading on Windows.

## Quick check
Run `win_network_info`. Identify the active adapter, IPv4 address, default gateway, DNS servers, and route metric.

Then test in order:
1. `win_ping` to the default gateway.
2. `win_ping` to `1.1.1.1`.
3. `win_dns_check` for the affected domain and `example.com`.
4. `win_http_check` for the affected URL.

Keep each result separate. A successful IP ping does not prove DNS or HTTP works.

## Standard diagnostic path

### 0. Use a boundary test before changing settings
Treat the path as a chain: service or site, upstream network, access point or cable, adapter, driver, Windows settings, then browser/application. Compare a known-good device on the same link, the affected device on another link, and a second application. Record the exact failing layer instead of resetting the whole network.

### 1. Validate adapter and address
Run `Get-NetAdapter` and inspect only connected or expected adapters.
- `169.254.x.x` means DHCP did not provide an address.
- Missing gateway means local link may exist without a usable route.
- Multiple active VPN, virtual, Wi-Fi, and Ethernet adapters can create route conflicts.

Use `Get-NetIPConfiguration` and `Get-NetRoute -DestinationPrefix '0.0.0.0/0'` to confirm which adapter owns the default route.

### 2. Validate the local path
Ping the gateway.
- Gateway fails: inspect link state, Wi-Fi association, cable, access point, VLAN, and adapter errors.
- Gateway succeeds: local networking works; continue upstream.

For Wi-Fi, inspect `netsh wlan show interfaces` for SSID, signal, radio type, receive rate, and transmit rate.

### 3. Validate upstream reachability
Ping `1.1.1.1` and `8.8.8.8`.
- Both fail while gateway works: suspect router, ISP, firewall, captive portal, or VPN route.
- One works: avoid declaring a total outage; the failed endpoint may filter ICMP.

Run `tracert -d 1.1.1.1` only when hop location matters. Stop if it becomes slow or noisy.

### 4. Validate DNS
Run `Resolve-DnsName` for the affected domain and a known-good domain.
- Known-good also fails: inspect configured DNS servers and resolver reachability.
- Known-good works but target fails: inspect the target record, suffix search, split DNS, or authoritative DNS.
- Public DNS works while corporate DNS fails: check VPN and organization policy before changing DNS.

Flush DNS only after observing stale or inconsistent resolver results. Re-run the original query after `win_flush_dns`.

### 5. Validate proxy, VPN, and captive portal
Inspect:
```
netsh winhttp show proxy
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Get-NetAdapter | Where-Object InterfaceDescription -Match 'VPN|Virtual|Tunnel'
```

Do not disable a managed proxy or security client. Compare behavior with the user's approved VPN state and check organization policy.

Test `http://www.msftconnecttest.com/connecttest.txt` or the organization's approved captive-portal endpoint when a sign-in page is suspected.

If a campus or enterprise network uses separate wired and wireless identities, record the adapter's MAC address and authentication state without changing randomized-MAC settings blindly. A “No Internet” icon may only indicate that an external connectivity probe or captive portal is not authenticated; test an approved internal endpoint and the original URL.

### 6. Apply the narrow repair
Show a plan and obtain approval before state changes.
- DHCP lease problem: renew the active adapter lease, then confirm address, gateway, and DNS.
- Stale resolver cache: flush DNS, then repeat the failed lookup.
- Disabled adapter: enable only the user-confirmed adapter.
- Winsock corruption: use `netsh winsock reset` only after narrower evidence; explain that a restart is required.
- Driver issue: collect adapter and driver versions before proposing update or rollback.

## Verification
Repeat the original failing action plus gateway, DNS, and HTTP checks. Record final adapter, route, DNS server, HTTP status, and timing.

## Caveats
- ICMP may be blocked even when HTTP works.
- Corporate DNS and proxy settings may be intentional policy.
- Hyper-V, WSL, Docker, VPN, and endpoint clients add virtual adapters that should not be removed merely because they are inactive.
- Network reset removes adapter configuration and is a last-resort, separately approved action.

## Key signals
- `169.254.x.x` -> DHCP or link problem.
- Gateway works, IP works, names fail -> DNS path.
- Browser fails but PowerShell HTTP works -> browser profile, proxy, certificate, or extension.
- Works without VPN -> VPN route, DNS, proxy, or MTU issue.
- Only one host fails -> target service or target-specific DNS/TLS issue.

## Tools referenced
- `win_network_info`
- `win_ping`
- `win_dns_check`
- `win_http_check`
- `win_flush_dns`
- `shell_run`

## Escalation
Escalate with adapter details, IP/gateway/DNS, route table, exact failing URL, timestamps, VPN/proxy state, and the first failing layer. For managed devices, preserve policy and involve the network administrator.
