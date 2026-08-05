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
- Provider registration and model IDs are version- and account-dependent: run
  `openclaw models status` and use the exact `volcengine` provider/model ID shown by
  the current OpenClaw build and the Ark console. Never copy a dated model ID from an
  old guide.
- API key env var: `VOLCANO_ENGINE_API_KEY`
- Sign up: https://www.volcengine.com/

### BytePlus (International alternative to Volcano Engine)
- Provider ID: `byteplus`
- Do not assume `byteplus` is registered in the current build. Confirm it with
  `openclaw models status` and the BytePlus console first; if it is absent, configure
  the vendor's documented OpenAI-compatible endpoint as a custom provider instead.
- API key env var: `BYTEPLUS_API_KEY`

### Moonshot AI (月之暗面 / Kimi)
- Provider registration and model IDs vary by OpenClaw version and account. Confirm the
  provider and exact model IDs with `openclaw models status` and the Moonshot console;
  do not install an unverified plugin package or copy model names from this guide.
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
- Uses an OpenAI-compatible endpoint. Confirm the currently available model IDs in
  the DeepSeek console before configuring them; do not copy a dated model ID from this
  guide. "DeepSeek Coder" is not a separate model in the current API.
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

**For Volcengine** (after confirming the provider and model ID in `openclaw models status`):
```
openclaw config set agents.defaults.model.primary "volcengine/<model-id-from-current-catalog>"
```
Replace the example with the exact ID returned by the current catalog; it is not a
copy-pasteable model name.

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
        models: [{ id: "<verified-moonshot-model-id>" }]
      }
    }
  },
  agents: {
    defaults: {
      model: {
        primary: "moonshot/<verified-moonshot-model-id>"
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
        models: [{ id: "<verified-deepseek-model-id>" }]
      }
    }
  },
  agents: {
    defaults: {
      model: {
        primary: "deepseek/<verified-deepseek-model-id>"
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
        primary: "volcengine/<model-id-from-current-catalog>",
        fallbacks: ["<verified-model-from-another-provider>"]
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
