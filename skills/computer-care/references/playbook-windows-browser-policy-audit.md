---
name: windows-browser-policy-audit
description: Audit Chrome, Edge, Firefox, and Brave policies without touching profiles or disabling security updates
platform: windows
last_reviewed: 2026-07-28
author: computer-care-maintainers
source: local
---

# Windows Browser Policy Audit

## When to activate
Use when the user wants a minimal browser, less telemetry or sponsored content, suspects policy tampering, or needs to understand a browser configuration file.

## Quick check
Identify every installed browser, version, profile and whether it is managed by an organization. Close browsers before reading or backing up mutable JSON. Preserve `Login Data`, `Cookies`, `Web Data`, extension stores and profile keys; inspect metadata only.

## Standard diagnostic path

### 1. Read the effective policy
Inspect documented policy locations under HKLM/HKCU and the browser's own policy page (`chrome://policy`, `edge://policy`, `about:policies` or the Brave equivalent). Record policy name, source, value, timestamp and whether it is machine-, user- or enterprise-managed. Also list extensions and their permissions through `browser-security-audit`.

### 2. Explain tradeoffs
Separate privacy/UI policies from security controls. Disabling sponsored content or optional integrations may be reversible; disabling Safe Browsing, certificate checks, password protections or automatic browser updates is not an acceptable optimization. Do not infer that a hidden policy is safe because a browser accepts it.

### 3. Review an upstream configuration safely
If the user names an upstream project, download its text from the official repository to an isolated directory, record URL/commit/SHA-256/license, inspect the diff and adapt only the selected policies. Never run a remote PowerShell or shell pipeline. Do not overwrite a live profile or enterprise policy.

### 4. Apply with backup and confirmation
Export the exact registry policy keys or copy only the selected policy JSON to a dated backup. Apply the smallest user-scope change, obtain confirmation, and leave organization-managed values untouched. Use the browser's documented settings when they provide the same result.

## Verification
Reopen the browser, re-check its policy page, confirm extension/search behavior and verify that automatic browser updates and security protections remain enabled. Restore the exact policy backup if the user's workflow regresses.

## Caveats
- Browser policies can be recreated by MDM, domain policy or an installed security product.
- Profile JSON can contain tokens and personal history even when it looks like configuration; do not paste it into chat or an external model.
- A policy audit does not prove that an extension or website is trustworthy; use endpoint and browser security checks for incidents.

## Escalation
Escalate enterprise-managed policies, certificate interception, unknown extensions with broad permissions, disabled updates, or a request to weaken Safe Browsing/UAC/Defender.

## Tools referenced
- `win_policy_list`
- `win_registry_snapshot`
- `win_file_hash`
- `win_startup_programs`
- `ui_spa`
- `web_fetch`
