---
name: setup-homebrew
description: Install and configure Homebrew package manager on macOS
platform: macos
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🍺
---

# Set Up Homebrew

## When to activate
User wants to install Homebrew, set up a package manager, or says they need to install software on their Mac and doesn't have Homebrew yet.

## Step 1: Check if Homebrew is already installed
Run `shell_run` with `which brew` or `brew --version` to see if it exists.
- If Homebrew is already installed, skip to Step 4 (install packages).
- If not found, continue with Step 2.

## Step 2: Install Homebrew
Do not execute the official installer through command substitution. Download it
into an isolated temporary directory, record the URL and SHA-256, and inspect
the local file first:

```
tmp_dir="$(mktemp -d)"
script_path="$tmp_dir/homebrew-install.sh"
curl --fail --location --silent --show-error \
  --output "$script_path" \
  https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh
shasum -a 256 "$script_path"
sed -n '1,260p' "$script_path"
```

Explain that the locally computed hash identifies the downloaded bytes but is
not a vendor signature. Use WAIT_FOR_USER for explicit confirmation of the
reviewed local script, then tell the user to run `/bin/bash "$script_path"` in
Terminal and follow any prompts (password entry, Xcode CLT installation). Do
not pipe or command-substitute the remote response. This can take 5–15
minutes.

## Step 3: Add Homebrew to PATH
After installation, Homebrew often needs to be added to the shell profile.
Check if `brew` is in PATH by running `which brew`.

The prefix differs by architecture: Apple Silicon installs to `/opt/homebrew`, Intel Macs
to `/usr/local`. Detect it by which binary actually exists rather than hardcoding one —
and note that Rosetta and migrated machines can have either, so `uname -m` alone is not
reliable:
```bash
for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  [ -x "$p" ] && BREW="$p" && break
done
[ -n "$BREW" ] || echo "Homebrew not found in either prefix"
```

Append to the profile the user's login shell actually reads — `~/.zprofile` for zsh (the
macOS default since Catalina), `~/.bash_profile` for bash:
```bash
PROFILE=~/.zprofile
[ "$(basename "$SHELL")" = "bash" ] && PROFILE=~/.bash_profile
echo "eval \"\$($BREW shellenv)\"" >> "$PROFILE"
eval "$($BREW shellenv)"
```
Then verify with `brew --version`.

## Step 4: Install requested packages
If the user had specific software in mind, help them install it via `brew install <package>` or `brew install --cask <app>`.
Common requests: Chrome (`google-chrome`), VS Code (`visual-studio-code`), Slack (`slack`), Zoom (`zoom`).

## Tools referenced
- `shell_run` — run shell commands to check/install
- `ui_spa` with WAIT_FOR_USER — for Terminal steps the user must do themselves
- `ui_user_question` — ask what packages they want

## Escalation
If Xcode CLT installation fails, the user may need to download it manually from developer.apple.com. If Homebrew install script fails, check proxy/firewall settings.
