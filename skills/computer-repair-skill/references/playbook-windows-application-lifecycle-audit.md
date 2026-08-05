---
name: windows-application-lifecycle-audit
description: Audit Windows app install/uninstall candidates by exact package ID, publisher, source, and reversible verification
platform: windows
last_reviewed: 2026-08-05
author: computer-repair-skill-maintainers
source: local
---

# Windows Application Lifecycle Audit

## When to activate
Use when the user wants to remove bloatware, review installed applications,
install a named package, compare WinGet and Chocolatey candidates, or check
whether an uninstall left services, startup entries or files behind.

## Quick check
Record Windows edition/build, current user, management status, package-manager
availability and the exact application name the user means. Enumerate installed
desktop and Appx packages without reading application data. Do not treat a
display name as a unique identifier.

## Standard diagnostic path

### 1. Establish exact identity
For every candidate record:

- display name, package ID/family name, version and architecture;
- publisher and Authenticode status for the installer or executable;
- install location, source (`winget`, `msstore`, `chocolatey` or registry) and
  uninstall command metadata;
- dependencies, update channel, current user versus all users, and whether the
  package owns a service, startup item, scheduled task or file association.

Use `win_package_inventory`, `win_app_list` and `win_persistence_snapshot`.
The same display name from two sources is two separate candidates until the
publisher, ID and version match.

### 2. Review the candidate before changing state
For installation, inspect the official source, exact version, installer URL,
SHA-256 and signature, license and requested elevation. Prefer the native
package manager's metadata and interactive confirmation. Never run a remote
PowerShell pipeline or an unreviewed installer.

For removal, classify the package as user-installed, optional Appx, shared
runtime, driver, security software, management agent or unknown. Keep Store
dependencies, mail, browser, cloud-sync, development, accessibility and
enterprise software in review-only status until the user identifies them.

### 3. Build a single-item plan
Show the exact package ID, version, source, command, elevation, expected
dependencies, restart requirement and rollback path. Do not use display-name
wildcards, batch uninstall, `--silent` flags or automatic source fallback
without approval. For Appx, distinguish removing the current user's package
from provisioning changes that affect future users.

Before removal, export relevant uninstall metadata and snapshot persistence
entries. Before installation, record the pre-install package list and available
disk space. If the application stores user data, use
`windows-application-cleanup` or a verified application backup first; uninstall
does not equal data migration.

### 4. Apply and verify one item
After explicit confirmation, use the verified native uninstaller or package
manager. Capture the exit code and output, report whether a reboot is pending,
and stop on a failed or ambiguous result instead of retrying with force.

Re-enumerate the package by exact ID, inspect services/startup/tasks and the
uninstall registry entry, then test the user's stated workflow. Do not delete
leftover files or registry keys until they are separately identified, hashed or
exported, and approved. For a dedicated post-uninstall residue preview or
guarded force-removal review, continue with
[windows-uninstall-residue-cleanup](playbook-windows-uninstall-residue-cleanup.md).

## Verification
Compare the before/after package inventory, persistence snapshot and disk
usage. For installation, verify publisher, version and launch behavior. For
removal, verify that the exact package is absent while shared dependencies,
security controls, update services and unrelated applications remain present.

## Caveats
- WinGet or Chocolatey metadata can change; record the source and query time.
- Package IDs are not proof of trust. Verify publisher, signature and hash for
  downloaded installers.
- An uninstall string can contain arbitrary arguments; parse and display it,
  but do not execute it blindly.
- Store package removal may be restored by Windows updates or organization
  policy. Report the policy owner rather than repeatedly removing it.
- Third-party Windows "debloat" or tweak utilities (Sparkle for Windows, O&O
  ShutUp10, Winutil and similar) apply presets that may be non-reversible even
  when the UI says they are safe — Sparkle's own documentation states some
  tweaks cannot be unapplied. Treat each item as an independent change, and
  record what was applied before applying it. Note this is the Windows tool
  named Sparkle, not the macOS `Sparkle` app-update framework.

## Escalation
Escalate unsigned installers, unknown publishers, drivers, security or MDM
agents, shared runtimes, license-managed software, package-manager source
errors, or a request to remove Edge, Defender, OneDrive or Windows components.

## Tools referenced
- `win_package_inventory`
- `win_package_metadata`
- `win_app_list`
- `win_persistence_snapshot`
- `win_file_hash`
- `win_file_signature`
- `win_package_install`
- `win_package_uninstall`
- `ui_spa`
