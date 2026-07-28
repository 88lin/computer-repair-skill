---
name: linux-network-diagnostics
description: Systematic Linux connectivity troubleshooting for links, addresses, routes, DNS, HTTP, firewall, and namespaces
platform: linux
last_reviewed: 2026-07-26
author: computer-repair-skill-maintainers
source: local
---

# Linux Network Diagnostics

## When to activate
User reports no connectivity, DNS failure, intermittent network, service reachability problems, VPN side effects, or container versus host networking differences on Linux.

## Quick check
Run `linux_network_info`, then test the active route's gateway, `1.1.1.1`, a known-good DNS name, and the affected URL.

Also identify whether the command runs on the host, in a container, over SSH, or inside a network namespace. Do not mix observations from different namespaces.

## Standard diagnostic path

### 1. Validate link and address
Run:
```
ip -brief link
ip -brief address
ip route show
```

- Interface down: inspect carrier, Wi-Fi association, NetworkManager/systemd-networkd state, or virtual interface ownership.
- `169.254.x.x` only: DHCP failed or the interface is link-local by design.
- Address present but no default route: local subnet access may work without internet.

### 2. Validate the local route
Use `ip route get 1.1.1.1` to see the selected interface, source address, and gateway. Ping the gateway from that path.

- Gateway fails: inspect link, VLAN, bridge, bonding, Wi-Fi, cable, and neighbor discovery.
- Gateway succeeds: continue to upstream reachability.

Use `ip neigh show` to distinguish unresolved neighbors from higher-layer failures.

### 3. Validate upstream reachability
Run `linux_ping` to `1.1.1.1` and `8.8.8.8`.
- Both fail after the gateway: suspect upstream routing, firewall, VPN, ISP, or namespace policy.
- Ping fails but HTTP works: ICMP filtering is likely; use application-layer evidence.

Use `tracepath 1.1.1.1` when MTU or hop location matters. Prefer `tracepath` over privileged traceroute where available.

### 4. Validate DNS
Inspect `resolvectl status` or `/etc/resolv.conf` and identify who manages it. Run `getent ahosts <DOMAIN>` and, when available, `dig` against the configured resolver.

- Resolver unreachable: inspect route and firewall to the DNS server.
- Public name works but internal name fails: check VPN split DNS and search domains.
- `/etc/resolv.conf` points at `127.0.0.53`: inspect systemd-resolved rather than replacing the file.

Flush caches only after confirming a cache inconsistency and only through the active resolver service.

### 5. Validate HTTP, TLS, proxy, and firewall
Run `linux_http_check` for the exact URL and record HTTP status, final URL, DNS time, connect time, TLS result, and total time.

Inspect proxy environment names without printing secret values. Check the active firewall manager (`nft`, `iptables`, `firewalld`, or `ufw`) read-only before proposing changes.

For containers, compare host and container DNS, route, proxy, and MTU. For SSH sessions, avoid restarting the interface carrying the session.

### 6. Apply the narrow repair
Show the exact plan and obtain approval.
- DHCP issue: renew through the active network manager, then re-check address and route.
- Resolver cache issue: flush only the active resolver cache.
- NetworkManager profile issue: reconnect the specific profile rather than restarting all networking.
- MTU issue: verify with `tracepath` or packet-size tests before changing an interface.
- Firewall issue: change one explicit rule with a rollback command; do not flush the ruleset.

## Verification
Repeat the original request plus route selection, gateway, DNS, and HTTP checks. Confirm service behavior from the same namespace and user context that originally failed.

## Caveats
- Restarting networking remotely can terminate the repair session.
- Containers and network namespaces have independent routes and DNS.
- Cloud instances may enforce security groups outside the machine.
- Managed VPN and security agents may intentionally control routes, DNS, or firewall rules.

## Key signals
- Link up, no address -> DHCP or static configuration.
- Address present, no route -> routing configuration.
- IP works, name fails -> resolver path.
- Host works, container fails -> namespace, bridge, DNS, proxy, or MTU.
- Small requests work, large TLS transfers stall -> MTU or path-MTU discovery.

## Tools referenced
- `linux_network_info`
- `linux_ping`
- `linux_dns_check`
- `linux_http_check`
- `linux_flush_dns`
- `shell_run`

## Escalation
Escalate with distribution, network manager, namespace, interface/address, selected route, resolver, firewall manager, proxy presence, exact target, timestamps, and the first failing layer.
