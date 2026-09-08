---
name: setup-openclaw/install-node
description: Install Node.js 22+ for OpenClaw (sub-module)
platform: all
last_reviewed: 2026-09-09
author: upstream-maintainers
source: bundled
emoji: 🦞
---

# Install Node.js

OpenClaw requires Node.js 22+. This module installs it.

## Step 1: Choose Installation Method

Check the platform first.

**macOS:**
- **Homebrew** (recommended if brew is available): `brew install node@22`
- **nvm**: install nvm then `nvm install 22`
- **Direct download** from nodejs.org

**Windows:**
- **nvm-windows**: `nvm install 22 && nvm use 22`
- **Direct download** from nodejs.org (LTS installer)
- **winget**: `winget install OpenJS.NodeJS.LTS`

**Linux:**
- **nvm** (recommended): install nvm then `nvm install 22`
- **Package manager**: check distro-specific instructions

## Step 2: Install

For Homebrew: `brew install node@22 && brew link node@22`.
For nvm, do not pipe the remote installer into a shell. First resolve the current
nvm release tag from the official repository's releases page instead of trusting a
tag written here — `v0.40.7` was the latest tag verified on 2026-09-09, and a pin
copied from an old runbook silently installs an outdated installer. Then download
the pinned script into an isolated temporary directory, record its SHA-256, read it
and show the URL, tag, hash and relevant commands:

```bash
nvm_tag='<NVM_TAG>'   # 例如 v0.40.7；执行前先核对官方 releases 页面
tmp_dir="$(mktemp -d)"
script_path="$tmp_dir/nvm-install.sh"
curl --fail --location --silent --show-error \
  --output "$script_path" \
  "https://raw.githubusercontent.com/nvm-sh/nvm/$nvm_tag/install.sh"
sha256sum "$script_path"
sed -n '1,240p' "$script_path"
```

Use WAIT_FOR_USER for explicit confirmation of the reviewed local script. A
locally computed hash identifies the downloaded bytes but is not a vendor
signature. After confirmation, run `bash "$script_path"`, restart the shell,
then run `nvm install 22 && nvm use 22`.
For direct download: use WAIT_FOR_USER and guide to nodejs.org download page.

## Step 3: Verify

Run `node --version` and confirm it shows v22.x or higher.
If it shows an old version, check PATH ordering. On macOS with Homebrew,
may need `brew link --overwrite node@22`.

## Tools referenced
- `shell_run` — install and verify Node.js
- `ui_user_question` — installation method choice
- `ui_spa` with WAIT_FOR_USER — for manual download
