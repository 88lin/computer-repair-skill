---
name: setup-ssh-key
description: Generate an SSH key pair and add it to GitHub or another service
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🔑
---

# Set Up SSH Key

## When to activate
User wants to set up SSH keys, connect to GitHub via SSH, push to git without password, or says "permission denied (publickey)".

## Step 1: Check for existing SSH keys
Run a command to list `~/.ssh/` and look for `id_ed25519.pub` or `id_rsa.pub`.
- If a key exists, ask the user if they want to use the existing one or generate a new one.
- If no keys found, proceed to Step 2.

## Step 2: Collect email address
Ask the user for their email address (used as the SSH key comment). This is non-sensitive — use `text_input`.

## Step 3: Generate the SSH key
Default to a passphrase. An unprotected private key is a plaintext credential: anyone who
copies `~/.ssh/id_ed25519` — malware, a backup, a borrowed laptop — gets the user's Git
access with no further barrier. The agent will unlock it once per session, so the cost is
one prompt.

Run `ssh-keygen -t ed25519 -C "<email>"` and let the user type the passphrase into the
interactive prompt (never pass it via `-N` on the command line — that puts it in shell
history). Then load it into the agent so it is not retyped:
```bash
# macOS — store in the login keychain
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
# Linux
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
```
On macOS also add to `~/.ssh/config`:
```
Host *
  UseKeychain yes
  AddKeysToAgent yes
```

An empty passphrase is an explicit exception, not the default. Only use it when the user
asks after being told the tradeoff, or for an unattended CI/service key whose scope is
already limited. Record the choice either way.

Show the generated public key to the user.

## Step 4: Copy public key
Run `cat ~/.ssh/id_ed25519.pub` and display the key. Tell the user to copy it.
Use WAIT_FOR_USER — the user needs to go to GitHub (Settings → SSH Keys → New SSH Key) and paste it.

Provide a direct link: https://github.com/settings/ssh/new

## Step 5: Test the connection
Run: `ssh -T git@github.com` to verify.
Expected success output: "Hi username! You've successfully authenticated"
If it fails, check `~/.ssh/config` and suggest adding:
```
Host github.com
  IdentityFile ~/.ssh/id_ed25519
  AddKeysToAgent yes
```

## Tools referenced
- `shell_run` — run ssh-keygen and test commands
- `ui_user_question` with `text_input` — collect email
- `ui_spa` with WAIT_FOR_USER — GitHub key paste step
