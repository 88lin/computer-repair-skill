---
name: setup-openclaw/china-models
description: Set up Chinese AI model providers for OpenClaw (Volcano Engine, Moonshot, DeepSeek, Qwen, GLM)
platform: all
last_reviewed: 2026-08-05
author: upstream-maintainers
source: bundled
emoji: 🦞
---

# Chinese Model Providers

Guide for setting up Chinese AI model providers with OpenClaw. These are
useful for users in China where Anthropic/OpenAI APIs may be slow or
unavailable, or who prefer domestic models.

## Step 1: Choose Provider

Ask the user which provider they want to use:

### Volcano Engine (火山引擎 / 豆包)
- Provider ID: `volcengine`
- Install the official provider first: `openclaw plugins install @openclaw/volcengine-provider`, then `openclaw gateway restart`
- General models (read the current catalog before pinning a dated id): `doubao-seed-evolving`, `doubao-seed-2-1-pro-260628`, `doubao-seed-2-1-turbo-260628`, `glm-5-2-260617`, `deepseek-v4-pro-260425`, `deepseek-v4-flash-260425`
- Coding models use the separate `volcengine-plan` provider: `ark-code-latest`, `doubao-seed-2.1-turbo`, `glm-5.2`, `deepseek-v4-pro`, `deepseek-v4-flash`
- API key env var: `VOLCANO_ENGINE_API_KEY`
- Sign up: https://www.volcengine.com/

### BytePlus (International alternative to Volcano Engine)
- Provider ID: `byteplus`
- Same models as Volcano Engine, for international users
- API key env var: `BYTEPLUS_API_KEY`

### Moonshot AI (月之暗面 / Kimi)
- Ships as an external plugin — install it before onboarding: `openclaw plugins install @openclaw/moonshot-provider` then `openclaw gateway restart`
- Model refs: `moonshot/kimi-k3` (onboarding default), `moonshot/kimi-k2.7-code`, `moonshot/kimi-k2.7-code-highspeed`
- API key env var: `MOONSHOT_API_KEY`
- Base URL: `https://api.moonshot.ai/v1` (international) or `https://api.moonshot.cn/v1` (China)
- Kimi Coding is a **separate** provider with its own key and a `kimi/` prefix (`kimi/kimi-for-coding`, `kimi/k3`). Keys are not interchangeable — do not mix the prefixes.
- Sign up: https://platform.moonshot.cn/

### Z.AI / GLM (智谱 AI)
- Provider ID: `zai`
- Models: the GLM-5 line (GLM-5 shipped 2026-02; 5.1/5.2 followed). Read the current id off the console rather than hardcoding it — this vendor renames on every minor release.
- API key env var: `ZAI_API_KEY`
- Sign up: https://open.bigmodel.cn/

### Qwen Portal (通义千问 — 免费)
- Free tier via OAuth (no API key needed)
- Models: Qwen Coder + Vision
- Auth via device code flow (see Step 3)

### DeepSeek (深度求索)
- Uses OpenAI-compatible endpoint
- Models: `deepseek-chat` and `deepseek-reasoner` on DeepSeek's own endpoint. "DeepSeek Coder" no longer exists as a separate model — it was folded into the mainline chat model. Newer V4 generations are reachable through Volcengine (`deepseek-v4-pro-260425`, `deepseek-v4-flash-260425`); confirm current ids on the provider console before pinning one.
- API key env var: `DEEPSEEK_API_KEY`
- Base URL: `https://api.deepseek.com/v1`
- Sign up: https://platform.deepseek.com/

## Step 2: Get API Key

For most providers, the user needs an API key. Collect it via `secure_input`.

Store it with `write_secret`, **not** as a shell argument — `openclaw config set env.X "<key>"`
would put the key in shell history and in the process table, and leave it in plaintext
inside `openclaw.json`:
- secret_name: the provider name, e.g. `volcengine_api_key`
- file_path: expansion of `~/.openclaw/.env`
- format: `<ENV_VAR_NAME>={{value}}` (append, keep the trailing newline)

For example, for Volcano Engine the line becomes `VOLCANO_ENGINE_API_KEY={{value}}`.
On macOS/Linux, run `chmod 600 ~/.openclaw/.env`. On Windows, apply the ACL equivalent
shown in the Telegram playbook instead of running `chmod`. Config fields reference it
as `"${VOLCANO_ENGINE_API_KEY}"`.

## Step 3: Configure the Model

**For Volcengine** (after installing `@openclaw/volcengine-provider`):
```
openclaw config set agents.defaults.model.primary "volcengine/doubao-seed-2-1-pro-260628"
```

**For Qwen Portal** (free, OAuth):
```
openclaw models auth login --provider qwen-portal --set-default
```
This opens a device code flow — use WAIT_FOR_USER.

**For OpenAI-compatible providers** (Moonshot, DeepSeek):
These need a custom provider entry in `~/.openclaw/openclaw.json`:
```json5
{
  models: {
    providers: {
      moonshot: {
        baseUrl: "https://api.moonshot.ai/v1",
        apiKey: "${MOONSHOT_API_KEY}",
        api: "openai-completions",
        models: [
          { id: "kimi-k3" },
          { id: "kimi-k2.7-code" }
        ]
      }
    }
  },
  agents: {
    defaults: {
      model: {
        primary: "moonshot/kimi-k3"
      }
    }
  }
}
```

For DeepSeek:
```json5
{
  models: {
    providers: {
      deepseek: {
        baseUrl: "https://api.deepseek.com/v1",
        apiKey: "${DEEPSEEK_API_KEY}",
        api: "openai-completions",
        models: [
          { id: "deepseek-chat" },
          { id: "deepseek-reasoner" }
        ]
      }
    }
  },
  agents: {
    defaults: {
      model: {
        primary: "deepseek/deepseek-chat"
      }
    }
  }
}
```

## Step 4: Verify

Check that the model is accessible:
```
openclaw models status
```

Send a test message through a connected channel to confirm the model responds.

If rate-limited (429 errors), the provider may require a paid plan or the
model may need switching. Check `openclaw logs --follow` for details.

## Step 5: Optional — Add Fallback Models

For reliability, configure fallback models from a different provider:
```json5
{
  agents: {
    defaults: {
      model: {
        primary: "volcengine/doubao-seed-2-1-pro-260628",
        fallbacks: ["moonshot/kimi-k3", "deepseek/deepseek-chat"]
      }
    }
  }
}
```

## Tools referenced
- `shell_run` — openclaw CLI commands, config edits
- `ui_user_question` with options — provider selection
- `ui_user_question` with `secure_input` — API keys
- `write_secret` — 把 API key 写入 `~/.openclaw/.env`，不经命令行参数
- `ui_spa` with WAIT_FOR_USER — OAuth flows (Qwen Portal)
