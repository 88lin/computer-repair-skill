---
name: setup-openclaw/add-feishu
description: Add Feishu (飞书) as a messaging channel for OpenClaw (built-in plugin)
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🦞
---

# Add Feishu Channel (Built-in Plugin)

Connect Feishu (飞书) to OpenClaw using the built-in plugin. This is the
simpler setup — the bot operates as a Feishu app (机器人). For the official
Feishu plugin (operates as user identity with document/calendar/task access),
activate `setup-openclaw/add-feishu-official` instead.

Feishu is the most common messaging platform for Chinese teams.

## When to activate
User wants to connect Feishu/飞书 to OpenClaw, set up a Feishu chatbot,
or mentions "feishu" or "飞书".

## Prerequisites
OpenClaw must be installed and the gateway must be running:
- `openclaw --version` should return ≥ 2026.2
- `openclaw gateway status` should show "running"

If not installed, activate `setup-openclaw` first.

## Step 1: Create a Feishu App

Tell the user to create an enterprise app in the Feishu developer console:

> 1. Go to [飞书开放平台](https://open.feishu.cn/app) and log in with your Feishu account
> 2. Click **创建企业自建应用** (Create enterprise app)
> 3. Enter an app name (e.g. "我的 AI 助手") and a description
> 4. Choose an icon (can be changed later)

Use WAIT_FOR_USER — the user does this in their browser.

## Step 2: Enable Bot Capability

Tell the user to enable the bot feature:

> In your app settings:
> 1. Find **应用能力** (App Capabilities) > **机器人** (Bot) in the left menu
> 2. **Enable** bot capability (开启机器人能力)
> 3. Give the bot a display name

Use WAIT_FOR_USER — the user does this in the Feishu developer console.

## Step 3: Configure Permissions

Tell the user to batch-import permissions:

Grant the **minimum** set first. Extra scopes are not free: a Feishu app secret that
leaks carries every scope you granted, so never import scopes "just in case".

> 1. Go to **权限管理** (Permissions) in the left menu
> 2. Click **批量导入** (Batch import)
> 3. Paste the following JSON and import:
>
> ```json
> {
>   "scopes": {
>     "tenant": [
>       "application:bot.menu:write",
>       "cardkit:card:write",
>       "contact:user.employee_id:readonly",
>       "event:ip_list",
>       "im:chat",
>       "im:chat.access_event.bot_p2p_chat:read",
>       "im:chat.members:bot_access",
>       "im:message",
>       "im:message.group_at_msg:readonly",
>       "im:message.group_msg",
>       "im:message.p2p_msg:readonly",
>       "im:message:readonly",
>       "im:message:send_as_bot",
>       "im:resource"
>     ],
>     "user": [
>       "im:chat.access_event.bot_p2p_chat:read"
>     ]
>   }
> }
> ```

`contact:user.employee_id:readonly` is only needed if `resolveSenderNames` stays on.
Drop it if the user is fine seeing raw sender IDs.

**Only if the user explicitly wants the bot to read or write their documents**, import
this second block as well. Say out loud what it grants before importing:

> ```json
> {
>   "scopes": {
>     "tenant": [
>       "docs:document.content:read",
>       "sheets:spreadsheet",
>       "wiki:wiki:readonly"
>     ]
>   }
> }
> ```

Do **not** grant these, which earlier versions of this playbook included by mistake:
- `aily:file:read` / `aily:file:write` — Aily platform file access, unrelated to a chat bot
- `corehr:file:download` — downloads HR files; an org's personnel data is not chat-bot scope
- `application:application:self_manage` — lets the app rewrite its own configuration

Use WAIT_FOR_USER — the user does this in the Feishu developer console.

## Step 4: Record Credentials

Tell the user to find their credentials:

> In your app settings, go to **凭证与基础信息** (Credentials & Basic Info):
> - Copy the **App ID** (格式如 `cli_xxxxxxxxx`)
> - Copy the **App Secret**
>
> Keep the App Secret private — do not share it.
>
> If it ever leaks: reset it in **凭证与基础信息**, update the stored value, then run
> `openclaw gateway restart`. Resetting invalidates the old secret immediately.

Collect the App ID via `text_input` (placeholder: "cli_xxxxxxxxx").
Collect the App Secret via `secure_input` (secret_name: "feishu_app_secret").

## Step 5: Publish the App

Tell the user to publish:

> 1. Go to **版本管理与发布** (Version Management) in the left menu
> 2. Click **创建版本** (Create version) → fill in a version note → submit
> 3. Wait for approval (enterprise apps usually auto-approve in seconds to minutes)

Use WAIT_FOR_USER — the user must publish before the bot can work.

## Step 6: Configure OpenClaw

Run `shell_run` with `openclaw channels add` — but this is interactive.
Instead, configure directly:

Run `shell_run` with:
```
openclaw config set channels.feishu.enabled true
```

Write the App ID (collected in Step 4). The App ID is not a secret:
Run `shell_run` with `openclaw config set channels.feishu.accounts.main.appId "<app_id from Step 4>"`.

**Write the App Secret — never through a shell argument.** A secret passed on a command
line lands in the process table and in shell history. Do not use
`openclaw config set env.FEISHU_APP_SECRET "$(cat ...)"` or any variant that expands the
value into `argv`.

Use `write_secret` to put it in the global runtime dotenv, which is the documented home
for credentials (`~/.openclaw/.env`, a.k.a. `$OPENCLAW_STATE_DIR/.env`):
- secret_name: `feishu_app_secret`
- file_path: expansion of `~/.openclaw/.env`
- format: `FEISHU_APP_SECRET={{value}}`
- append to the file rather than replacing it, and make sure the line ends with a newline

Then lock the file down and point the config at the variable **without letting the shell
expand it** — note the single quotes. On macOS/Linux use `chmod 600`; on Windows use the
ACL equivalent shown in the Telegram playbook:
```bash
chmod 600 ~/.openclaw/.env
openclaw config set channels.feishu.accounts.main.appSecret '${FEISHU_APP_SECRET}'
```

Double quotes here would make the shell substitute the value and write the plaintext
secret straight into `openclaw.json`, which is the exact outcome we are avoiding.
Verify with `openclaw config get channels.feishu.accounts.main.appSecret` — it must print
the literal `${FEISHU_APP_SECRET}`, not the secret.

If the user prefers structured secret storage, a SecretRef is equivalent and avoids
interpolation entirely:
```json5
{
  channels: { feishu: { accounts: { main: {
    appSecret: { source: "env", provider: "default", id: "FEISHU_APP_SECRET" },
  } } } }
}
```

Fully interactive alternative — the official wizard prompts for both values and never
puts them in `argv`:
```bash
openclaw channels login --channel feishu
```

See `playbook-setup-openclaw-config-reference.md` for the full env resolution order, and
`safety-policy.md` for the rule this follows.

Restart gateway:
```
openclaw gateway restart
```

## Step 7: Configure Event Subscription

**Important:** This step must happen AFTER the gateway is running (Step 6),
otherwise the long connection validation will fail.

Tell the user:

> 1. Go back to your app on [飞书开放平台](https://open.feishu.cn/app)
> 2. Find **事件与回调** (Events & Callbacks) > **事件配置** (Event Config) in the left menu
> 3. For request method, select **使用长连接接收事件** (Use long connection to receive events) — **this is critical, do NOT choose Webhook**
> 4. Add event: search for `im.message.receive_v1` (接收消息), check and add it
> 5. Save the configuration
>
> If saving fails with a connection error, make sure OpenClaw gateway is running (`openclaw gateway status`).

Use WAIT_FOR_USER — the user does this in the Feishu developer console.

After the user confirms, tell them they need to publish a new version for the
event subscription to take effect:

> Go to **版本管理与发布** → **创建版本** → submit and publish.

Use WAIT_FOR_USER.

## Step 8: Test

Have the user send a message to the bot in Feishu:

> 1. In Feishu, search for your bot's name and open the conversation
> 2. Send a message, e.g. "你好"
> 3. If the bot replies with a **pairing code** (配对码), that's normal —
>    it means pairing mode is active

If a pairing code was returned, run:
```
openclaw pairing approve feishu <code>
```

Then have the user send another message. A normal reply = success.

Verify channel status:
Run `shell_run` with `openclaw channels status --probe`.
Expected: Feishu channel shows "connected" or "ready".

If not working, run `shell_run` with `openclaw logs --follow` and look for errors:
- "permission denied" → Check `im:message:send_as_bot` permission is granted
- "app not published" → Step 5 was skipped or approval pending
- "event subscription" → Step 7 was skipped or not saved

## Step 9: Done

Show a done card summarizing:
- Feishu bot connected to OpenClaw
- Bot name and App ID
- Access policy: pairing mode (default — new users get a code, approve with `openclaw pairing approve feishu <code>`)
- How to check status: `openclaw channels status --probe`
- How to view logs: `openclaw logs --follow`
- Config file: `~/.openclaw/openclaw.json`
- Optional next steps:
  - Change access policy (pairing/open/allowlist) in config
  - Add the bot to group chats (requires @mention by default)
  - Set up auto-start: `openclaw gateway install`

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No message input box in Feishu | Event subscription not configured | Do Step 7, then publish a new version |
| Bot doesn't respond at all | App not published, or gateway not running | Check `openclaw gateway status`, verify app is published |
| Intermittent responses | Network instability or gateway restarting | Check `openclaw logs \| grep -i reconnect` |
| "permission denied" errors | Missing permissions | Re-import permission JSON from Step 3, publish new version |
| Bot works in DM but not groups | Bot not added to group, or @mention required | Add bot to group; default requires @mention |
| Images/files not received | Missing `im:resource` permission | Add permission, publish new version, restart gateway |
| API quota exhausted | Health check consuming 27k calls/month per machine | Disable Feishu on machines that don't need it, or ensure only one machine runs it |
| Proxy/VPN causes connection failure | `HTTP_PROXY` env var routes Feishu traffic through proxy | Set `NO_PROXY` to exclude `feishu.cn` domains |

## Advanced Configuration

### Access Control

| Policy (`dmPolicy`) | Behavior |
|---|---|
| `"pairing"` | **Default.** New users get a pairing code; admin approves |
| `"open"` | Anyone in the organization can message |
| `"allowlist"` | Only specific Open IDs (`ou_xxx`) can message |
| `"disabled"` | No private messages |

Set via: `openclaw config set channels.feishu.dmPolicy "open"`

### Group Chat

Default: all groups allowed, but @mention required.

Allow a specific group without @mention:
```
openclaw config set channels.feishu.groups.oc_GROUP_ID.requireMention false
```

Restrict to specific groups:
```
openclaw config set channels.feishu.groupPolicy "allowlist"
openclaw config set channels.feishu.groupAllowFrom '["oc_xxx", "oc_yyy"]'
```

**Finding IDs:** Have the user @mention the bot in a group, then check
`openclaw logs --follow` for the group ID (`oc_xxx`) and user ID (`ou_xxx`).

### Performance Tuning

Reduce API quota usage for high-traffic bots:
```
openclaw config set channels.feishu.typingIndicator false
openclaw config set channels.feishu.resolveSenderNames false
```

### Auto-Start

```
openclaw gateway install
```

The bot starts automatically when the computer boots.

## Tools referenced
- `shell_run` — openclaw CLI commands (config, gateway, pairing, logs)
- `ui_user_question` with `text_input` — App ID collection
- `ui_user_question` with `secure_input` — App Secret collection
- `ui_user_question` with options — access policy choice (if user wants non-default)
- `ui_spa` with WAIT_FOR_USER — Feishu developer console steps
- `write_secret` — write App Secret to config
- `ui_done` — completion summary
