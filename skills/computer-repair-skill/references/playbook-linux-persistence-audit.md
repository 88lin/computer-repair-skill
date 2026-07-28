---
name: linux-persistence-audit
description: Audit Linux systemd units, timers, cron, autostart and shell hooks with package ownership before changing anything
platform: linux
category: macos-linux-repair
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Linux Persistence Audit

## When to activate

User reports an unexpected process or listener, a service that restarts itself after being stopped, a slow boot with unknown units, a configuration change that "does not take effect", leftovers after removing a package, a cron job nobody claims, or asks what runs automatically on this host.

## Quick check

Run `linux_system_summary` and record distribution and version, kernel, init system, whether the host is bare metal, a VM, a container or WSL, the package manager, whether SELinux or AppArmor is enforcing, and whether a configuration-management tool (Ansible, Puppet, Chef, Salt, cloud-init) owns this host.

That last point decides the whole engagement: on a managed host, local edits are reverted on the next run, so the fix belongs in the management repository, not on the box.

If malicious activity is plausible, preserve evidence first. Use `activate_playbook` to bring in `malware-triage` before removing anything.

## Standard diagnostic path

### 1. Enumerate the autostart surface

Run `linux_startup_items`, `linux_service_list` and `linux_scheduled_task_list`, and collect:

- enabled system units and enabled per-user units, including units in `/etc/systemd/system` and `/usr/lib/systemd/system`;
- unit drop-ins under `*.service.d/` and overridden units, which is where "my config change did nothing" usually resolves;
- systemd timers with their next and last elapse times;
- cron: user crontabs, `/etc/crontab`, `/etc/cron.d`, the hourly through monthly directories, and pending `at` jobs;
- desktop autostart entries in the system and per-user autostart directories;
- shell initialisation files for the affected user and system-wide profile scripts;
- legacy and low-level hooks: `rc.local`, init scripts on non-systemd hosts, `/etc/ld.so.preload`, `modules-load.d`, udev rules, PAM stack changes, and package-manager hooks;
- SSH authorised keys, including forced-command and options entries;
- container and orchestration restart policies, which recreate workloads independently of systemd.

Record for each item: name, unit or file path, the exact command line, the user it runs as, the trigger, and the enable state.

### 2. Establish ownership with the package manager

This is the step that separates a distribution component from something added later. Run `linux_package_inventory` and ask, for every unit file, script and binary path of interest: which package owns this path?

- Owned by a distribution package, unmodified: leave it alone and explain what it does.
- Owned by a package but modified locally: the local change is the finding. Record the difference before touching it.
- Owned by nothing: added by hand, by a vendor installer, by a language package manager, or by an intruder. This is where attention belongs.

Where the package manager supports verification, use it to detect modified files owned by packages. Scope verification to the suspect paths first; a whole-system verify produces far more output than the question needs.

Take the SHA-256 of unowned or modified binaries with `linux_file_hash`, and read unit files and scripts with `linux_read_file` before forming a conclusion.

### 3. Read what the unit actually does

Read the effective unit definition including drop-ins, not just the file the user pointed at. Check `ExecStart`, `ExecStartPre`, `User`, `WorkingDirectory`, `Environment` and `EnvironmentFile`, `Restart`, and any `WantedBy` target.

Signals worth attention: an `ExecStart` that pipes or evaluates a downloaded script, a unit running as root with a program path in `/tmp`, `/dev/shm` or a user home directory, an environment file outside `/etc`, a timer with a very short interval, a unit named to imitate a distribution unit, and a service whose binary has been deleted from disk while the process still runs.

Where available, the systemd security review output gives a quick read on how much privilege a unit holds.

### 4. Correlate with logs and the timeline

Use `linux_read_log` to read the journal for the unit and the boot in question, scoped to the complaint window. Establish when the item first appeared: file modification times, package install history, shell history if in scope, and the journal's first record for that unit.

An item whose creation time matches a known software install is explained. An item created at an unexplained time, especially outside working hours, raises the severity.

### 5. Decide what may change

Review-only by default: distribution-owned units, SELinux or AppArmor policy, anything owned by configuration management, cloud-init artefacts, and container-managed workloads.

Candidates for change: a user-added unit or cron entry the user no longer wants, an autostart entry for removed software, an SSH key that should not be there, and a locally added drop-in that conflicts with the intended configuration.

### 6. Change one item, reversibly

For each approved item, in order:

1. Copy the file to a dated holding directory outside its load path, preserving ownership and mode in your notes.
2. Prefer disabling over deleting: masking or disabling a unit is reversible and records intent; removing a file is not.
3. Stop the running instance by its exact unit name, not by killing a process name.
4. Reload the manager configuration only after the change, and re-read the effective definition.
5. On a managed host, make the equivalent change in the management source and note that the local change is temporary.

Do not disable a firewall, mandatory access control, auditing, unattended security updates or SSH hardening as a side effect of cleanup. Do not remove keys from `authorized_keys` without confirming which key belongs to the current session, or the session will be locked out.

## Verification

Re-run the enumeration and confirm the item is absent from the autostart surface and not running. Reboot when the change affects boot, and confirm it did not return. On a managed host, run the management tool in check mode and confirm it does not intend to recreate the item. Confirm dependent services still start, the host still reaches its normal targets with no failed units, and remote access still works — verify a second SSH session before closing the first.

## Caveats

- Configuration management and cloud-init recreate removed items by design; a local fix on a managed host is temporary.
- Masking a unit can break dependent services that were relying on it; check reverse dependencies first.
- Containers restart workloads by policy, so stopping a process inside a container is not persistence removal.
- WSL and minimal or container images may lack systemd, cron, a desktop autostart directory or a journal; missing data is a coverage gap, not a clean result.
- A running process whose binary was deleted from disk is a strong incident signal and cannot be investigated by reading the file that is no longer there.
- Per-user units and per-user timers are invisible to a system-only enumeration; enumerate for every relevant user.
- Package verification reports legitimate differences for configuration files that are meant to be edited; read the flags rather than the count.

## Escalation

Escalate to the host or platform owner for any managed, production or shared host, and to security for: unowned root-level units, binaries running from writable temporary paths, deleted-on-disk running binaries, unexplained SSH keys, tampered package files, or an item that returns after a verified removal and reboot. Provide distribution and kernel, init system, management tooling, the full enumeration, package-ownership results, hashes, effective unit definitions, journal excerpts with timestamps, the holding directory location, and every change made.

## Tools referenced

- `linux_startup_items`
- `linux_service_list`
- `linux_scheduled_task_list`
- `linux_package_inventory`
- `linux_file_hash`
- `linux_system_summary`
- `linux_read_file`
- `linux_read_log`
- `activate_playbook`
