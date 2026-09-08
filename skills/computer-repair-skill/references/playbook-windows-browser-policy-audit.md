---
name: windows-browser-policy-audit
description: Audit Chrome, Edge, Firefox, and Brave policies, including AI and extension controls, without weakening security
platform: windows
last_reviewed: 2026-09-09
author: computer-repair-skill-maintainers
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

### 2. Cover the AI, sharing, and extension-availability policies
Recent browser releases moved several data-sharing and assistant features behind their own policies, so a policy audit from an older baseline is incomplete. Read the current value and management source of at least: Chrome's page-sharing and DevTools GenAI controls (`SearchContentSharingSettings`, `DevToolsGenAiSettings`), Edge's Copilot browser-action control (`CopilotCoworkToolActionsEnabled`), and Edge's extension-manifest control (`ExtensionManifestV2Availability`). Verify each name and its accepted values against current vendor documentation before proposing a change — policy names, defaults, and removal timelines change between releases.

Treat `ExtensionManifestV2Availability` as a compatibility bridge, not a fix: it only keeps Manifest v2 extensions working while the vendor still supports them, so record the vendor's announced removal date and tell the user their content blocker will need a Manifest v3 replacement. Do not present an AI/telemetry policy as a security control, and do not enumerate policies from a cached list without reading the browser's own policy page.

### 3. Explain tradeoffs
Separate privacy/UI policies from security controls. Disabling sponsored content or optional integrations may be reversible; disabling Safe Browsing, certificate checks, password protections or automatic browser updates is not an acceptable optimization. Do not infer that a hidden policy is safe because a browser accepts it.

### 4. Review an upstream configuration safely
If the user names an upstream project, download its text from the official repository to an isolated directory, record URL/commit/SHA-256/license, inspect the diff and adapt only the selected policies. Never run a remote PowerShell or shell pipeline. Do not overwrite a live profile or enterprise policy.

Upstream policy sets are updated as browsers ship new features. Compare the project's current revision against the version the user already applied, list added/removed policy names, and re-confirm each addition individually instead of re-importing the whole set.

### 5. Apply with backup and confirmation
Export the exact registry policy keys or copy only the selected policy JSON to a dated backup. Apply the smallest user-scope change, obtain confirmation, and leave organization-managed values untouched. Use the browser's documented settings when they provide the same result.

## Verification
Reopen the browser, re-check its policy page, confirm extension/search behavior and verify that automatic browser updates and security protections remain enabled. Restore the exact policy backup if the user's workflow regresses.

## Caveats
- Browser policies can be recreated by MDM, domain policy or an installed security product.
- Policy names are release-specific: a name that works today may be renamed, deprecated or ignored after an update. Re-read the browser's policy page after every browser upgrade instead of trusting a saved list.
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
