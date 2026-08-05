---
name: setup-openclaw/add-telegram
description: Add Telegram as a messaging channel for OpenClaw
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🦞
---

# Add Telegram Channel

Add Telegram support to OpenClaw via a Telegram Bot.

## Prerequisites
OpenClaw must be installed (`openclaw --version` should work).

## Step 1: Create a Telegram Bot

Tell the user to create a bot via BotFather:

> 1. Open Telegram and search for **@BotFather**
> 2. Send `/newbot` and follow the prompts
> 3. Choose a display name (e.g., "My AI Assistant")
> 4. Choose a username ending in "bot" (e.g., "my_ai_assistant_bot")
> 5. Copy the bot token — looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

Use WAIT_FOR_USER — the user does this in Telegram.

## Step 2: Configure the Bot Token

Collect the bot token via `secure_input` (secret_name: "telegram_bot_token").

Enable the channel, then store the token via the env reference (see below) so the token
never appears in a shell argument:
```bash
openclaw config set channels.telegram.enabled true
openclaw config set channels.telegram.botToken '${TELEGRAM_BOT_TOKEN}'
```
Single quotes are required — double quotes would let the shell expand the variable and
write the plaintext token into `openclaw.json`.

Or write directly to `~/.openclaw/openclaw.json`:
```json5
{
  channels: {
    telegram: {
      botToken: "${TELEGRAM_BOT_TOKEN}",
      enabled: true,
      dmPolicy: "pairing"  // approve first message from each user
    }
  }
}
```

And store the token. Do **not** run `openclaw config set env.TELEGRAM_BOT_TOKEN "<token>"` —
that puts the token in shell history and in the process table, and leaves it in plaintext
inside `openclaw.json`. Use `write_secret` instead:
- secret_name: `telegram_bot_token`
- file_path: expansion of `~/.openclaw/.env`
- format: `TELEGRAM_BOT_TOKEN={{value}}` (append, keep the trailing newline)

On macOS/Linux, run `chmod 600 ~/.openclaw/.env`. On Windows, do not run `chmod`:
restrict the file to the current user and `SYSTEM` with the host's ACL tool, for example
`icacls.exe $env:USERPROFILE\.openclaw\.env /inheritance:r /grant:r "$($env:USERNAME):(F)" "SYSTEM:(F)"`.
The `"${TELEGRAM_BOT_TOKEN}"` reference above resolves from that file — see
`playbook-setup-openclaw-config-reference.md` for the resolution order. If the token
leaks, revoke it with `/revoke` in BotFather and repeat this step.

## Step 3: Set Access Policy

Ask the user who should be allowed to message the bot:

- **Pairing mode** (default, recommended): First message from any user requires
  approval. Good for personal use.
- **Allowlist**: Only specific Telegram user IDs can interact.
- **Open**: Anyone can message (use with caution).

For allowlist, the user needs their Telegram numeric user ID. They can get it
from `@userinfobot` on Telegram.

## Step 4: Restart and Test

Restart the gateway to pick up channel changes:
```
openclaw gateway restart
```

Verify: `openclaw channels status --probe`

Have the user send a message to their bot on Telegram. If using pairing mode,
approve the pairing request when prompted.

## Step 5: Optional — Group Setup

If the user wants the bot in a group:

1. Disable group privacy in BotFather:
   > Send `/mybots` → select bot → Bot Settings → Group Privacy → Turn OFF

2. Add the bot to the Telegram group.

3. Configure group policy:
   ```
   openclaw config set channels.telegram.groupPolicy "open"
   ```
   Or use "allowlist" with specific sender IDs.

By default, the bot requires an @mention in groups.

## Tools referenced
- `shell_run` — openclaw CLI commands
- `ui_user_question` with `secure_input` — bot token
- `write_secret` — 把 bot token 写入 `~/.openclaw/.env`，不经命令行参数
- `ui_user_question` with options — access policy
- `ui_spa` with WAIT_FOR_USER — BotFather setup
