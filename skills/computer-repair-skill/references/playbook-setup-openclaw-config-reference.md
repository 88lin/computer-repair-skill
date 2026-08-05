---
name: setup-openclaw/config-reference
description: Comprehensive OpenClaw configuration field reference
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🦞
---

# OpenClaw Configuration Reference

**Config file**: `~/.openclaw/openclaw.json` (JSON5 format)
**NOT** YAML, **NOT** `config.yaml` — always `openclaw.json`.

Use `openclaw configure` for interactive wizard, or edit the file directly.
Use `openclaw config get <path>` / `openclaw config set <path> <value>` for CLI.

## Agent & Model Settings

```json5
{
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",  // agent working directory
      model: {
        primary: "anthropic/claude-sonnet-4-5",
        fallbacks: ["openai/gpt-4o"]       // failover models
      },
      models: { /* model catalog/allowlist */ },
      imageMaxDimensionPx: 1200,           // vision token optimization
      heartbeat: {
        every: "30m",                       // check-in interval
        target: "last"                      // "last", channel name, or "none"
      },
      sandbox: {
        mode: "non-main",                   // "off" | "non-main" | "all"
        scope: "session"                    // "session" | "agent" | "shared"
      },
      groupChat: {
        mentionPatterns: ["@openclaw"]      // regex patterns for group activation
      }
    },
    list: [
      // Multiple agent definitions with per-agent overrides
    ]
  }
}
```

## Channel Settings

All channels share the same field patterns:

```json5
{
  channels: {
    whatsapp: {
      enabled: true,
      dmPolicy: "pairing",        // "pairing" | "allowlist" | "open" | "disabled"
      allowFrom: ["+8613812345678"],
      groupPolicy: "open",        // "open" | "allowlist" | "disabled"
      groupAllowFrom: [],          // falls back to allowFrom if unset
      sendReadReceipts: true,
      mediaMaxMb: 50,
      groups: {
        "<group-id>": { requireMention: true }   // per-group override
      },
      accounts: { /* multi-account overrides */ }
    },
    telegram: {
      botToken: "${TELEGRAM_BOT_TOKEN}",
      enabled: true,
      dmPolicy: "pairing",
      streaming: "partial"        // "off" | "partial" | "block"
    },
    discord: { /* same pattern */ },
    signal: { /* same pattern */ },
    slack: { /* same pattern */ }
  }
}
```

## Feishu-specific channel settings

These optimization flags belong only to the Feishu channel; do not copy them
into the shared channel pattern above. Both fields are optional booleans and
default to `true` in the Feishu plugin:

```json5
{
  channels: {
    feishu: {
      typingIndicator: true,       // set false to skip typing reaction calls
      resolveSenderNames: true     // set false to skip sender profile lookups
    }
  }
}
```

Google Chat has a different `typingIndicator` contract: it is a string enum,
for example `channels.googlechat.typingIndicator: "message"`, not a boolean.
Do not reuse the Feishu example for Google Chat, and do not assume either field
is shared by every channel.

**DM policies:**
- `pairing` — new senders need approval (expires 1h, max 3 pending)
- `allowlist` — only `allowFrom` senders allowed
- `open` — anyone can message
- `disabled` — channel off

**Group behaviour:**
- `requireMention` — in group chats, only respond when the bot is @mentioned. Defaults to `true`. Set it to `false` under `channels.<channel>.groups.<group-id>` to let one group talk to the bot without @mentions.

## Gateway Settings

```json5
{
  gateway: {
    mode: "local",                 // how the CLI reaches the gateway
    port: 18789,                   // default port
    reload: {
      mode: "hybrid",              // "hybrid" | "hot" | "restart" | "off"
      debounceMs: 300
    },
    auth: {
      token: "your-secret-token"   // access control for Control UI
    }
  }
}
```

**`gateway.mode`** selects how the CLI talks to the gateway. Read the live value with
`openclaw config get gateway.mode` — after an upgrade this is the first thing to check,
because a stale value makes every CLI command look like a connection failure.

**Port/bind changes require restart.** All other settings hot-reload.

## Session Management

```json5
{
  session: {
    dmScope: "main",               // "main" | "per-peer" | "per-channel-peer"
    threadBindings: {
      enabled: false,
      idleHours: 24
    },
    reset: {
      mode: "daily",
      atHour: 4,                   // UTC hour
      idleMinutes: 120
    }
  }
}
```

## Automation

```json5
{
  cron: {
    enabled: true,
    maxConcurrentRuns: 2,
    sessionRetention: "7d",
    jobs: {
      "job-name": {
        schedule: "0 9 * * *",     // cron expression
        prompt: "What to do",
        target: "whatsapp:+861381234"
      }
    }
  },
  hooks: {
    enabled: true,
    token: "webhook-secret",
    path: "/hooks",
    mappings: { /* route definitions */ }
  }
}
```

## Environment Variables

```json5
{
  env: {
    ANTHROPIC_API_KEY: "sk-ant-...",
    TELEGRAM_BOT_TOKEN: "123456:ABC...",
    // Reference in other fields as "${ANTHROPIC_API_KEY}"
    shellEnv: {
      enabled: false,              // auto-import from login shell
      timeoutMs: 5000
    }
  }
}
```

Variable substitution: `"${VAR_NAME}"` in any string value.
Only uppercase `[A-Z_][A-Z0-9_]*`. Missing vars cause load errors.

**Where a value actually comes from** (highest priority first — an existing value is never overridden):
1. Process environment of the gateway (shell, launchd/systemd unit, container or CI secret)
2. `.env` in the current working directory — *lower trust*: provider credentials are deliberately ignored from here
3. Global `.env` at `~/.openclaw/.env` (or `$OPENCLAW_STATE_DIR/.env`) — **the recommended place for API keys and app secrets**
4. The `env` block in `openclaw.json` — applied only if the variable is still missing
5. Optional login-shell import (`env.shellEnv.enabled`) — only fills in expected keys that are still missing

Because of rule 3, put secrets in `~/.openclaw/.env`, not in the `env` block of
`openclaw.json`. On macOS/Linux use `chmod 600`; on Windows apply an ACL that grants
access only to the gateway user (and `SYSTEM`). For structured secret storage use a
SecretRef instead of a literal, e.g. `{ source: "env", provider: "default", id: "FEISHU_APP_SECRET" }`,
or a file-backed provider declared under `secrets.providers`.

## Custom Model Providers

```json5
{
  models: {
    providers: {
      "my-provider": {
        baseUrl: "https://api.example.com/v1",
        apiKey: "${MY_API_KEY}",
        api: "openai",             // "openai" | "anthropic" | "auto"
        models: [
          { id: "model-name" }
        ]
      }
    }
  }
}
```

Then reference as: `"my-provider/model-name"`

## File Inclusion

Split large configs across files:
```json5
{
  agents: { $include: "./agents.json5" },
  channels: { $include: "./channels.json5" }
}
```

Supports recursive merge, relative paths, up to 10 nesting levels.

## CLI Commands Quick Reference

```
openclaw configure                 # interactive wizard
openclaw config get <path>         # read a field
openclaw config set <path> <value> # set a field
openclaw config unset <path>       # remove a field
openclaw doctor                    # validate config + diagnose issues
openclaw doctor --fix              # auto-repair common issues
openclaw gateway status            # check gateway health
openclaw gateway restart           # restart after config changes
openclaw channels status --probe   # check channel connections
openclaw models status             # check model availability
openclaw logs --follow             # real-time logs
openclaw status                    # overall system status
openclaw dashboard                 # open Control UI in browser
```
