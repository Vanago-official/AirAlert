# 🚨 Balistika Alarm Bot

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green)
![kurigram](https://img.shields.io/badge/kurigram-pyrogram%20fork-blue)
![gemini](https://img.shields.io/badge/google--genai-latest-orange)
![License](https://img.shields.io/badge/license-MIT-yellow)

**Balistika Alarm Bot** is a Telegram bot that monitors the official Ukrainian air alert API and supplements it with real-time AI analysis of Telegram channels to instantly notify subscribed users about direct missile threats to their city.

---

## ✨ Features

- 🚀 **Missile Threat Filtering:** Polls the [alerts.in.ua](https://alerts.in.ua/) API every 10 seconds and activates exclusively for red-level missile threats (`ballistic_missiles`, `cruise_missiles`, `unspecified_missiles`).
- 🤖 **AI-Powered Channel Monitoring:** When an official missile threat is declared, the bot activates a built-in userbot (Kurigram, a maintained Pyrogram fork) that monitors specific Telegram channels. It feeds the messages to Google's Gemini AI to determine if a threat is active (`THREAT`), passed (`CLEAR`), or irrelevant (`IGNORE`).
- 🔕 **Smart Mute:** After the first warning, users are automatically muted to prevent spam. They receive the all-clear message when the threat ends, or can unmute manually at any time to receive subsequent warnings.
- ⚙️ **Granular Settings:** Users can individually opt in or out of official "Clear" messages and AI-generated "Probably clear" messages.
- 📊 **Status Dashboard:** Users can check the current alert state, active threat types, activation status, mute status, and AI channel status via a button.
- 💾 **Persistent Storage:** User preferences are stored in a local SQLite database via `aiosqlite`. Missing columns are added automatically on startup, so existing databases keep working after updates.
- 🔑 **Code-free Userbot Login:** The userbot authenticates with a session string created once via QR login, so the server never needs an interactive login or a confirmation code.

---

## 🏗 Architecture

```text
main.py        — Bot entry point, handlers, alert broadcast loop
alarm.py       — API client for alerts.in.ua
userbot.py     — Kurigram/Pyrogram channel monitor with polling logic
ai.py          — Gemini-based ThreatAnalyzer
database.py    — SQLite operations (users, mute, active, clear preferences)
qr_login.py    — One-time QR login that produces the PYRO_SESSION string
config.cfg     — City and monitored channels configuration
.env           — Tokens, API keys and session string (not committed)
```

**How the dual-level alert loop works:**

1. **Idle Mode:** The bot queries the alerts API every 10 seconds. The userbot sleeps and makes no requests to the Telegram API.
2. **Official Alert:** If a new threat is detected (`alert_level == "red"` AND a missile threat is present):
   - Broadcasts `🔴 Danger!` to all active, unmuted users and mutes everyone.
   - Wakes up the userbot (`set_listening(True)`), which immediately fetches the last 10 messages from monitored channels for context.
3. **AI Monitoring:** The userbot polls monitored channels every 10 seconds and analyzes new messages with Gemini.
   - On `CLEAR`, it sends `🟢 Probably clear.` to users who enabled AI clear messages (they stay muted until the official all-clear).
   - On `THREAT`, it sends `🔴 Danger!` to anyone who manually unmuted.
4. **End of Alert:** When the official API downgrades or clears the alert:
   - The userbot goes back to sleep.
   - Broadcasts `🟢 Clear.` to muted users who opted in, and unmutes everyone.

---

## 🛠 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Vanago-official/BalistikaAlarm.git
cd BalistikaAlarm
```

### 2. Create a virtual environment and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> If you previously installed `pyrogram`, remove it first (`pip uninstall -y pyrogram`), because Pyrogram and Kurigram install into the same `pyrogram` package directory.

### 3. Configure environment variables
Copy the example and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=your_telegram_bot_token      # Token from @BotFather
ALARM=your_alerts_api_token            # Token from https://alerts.in.ua/
GEMINI_API_KEY=your_gemini_api_key     # Key from Google AI Studio
API_ID=your_telegram_api_id            # API ID from https://my.telegram.org
API_HASH=your_telegram_api_hash        # API Hash from https://my.telegram.org
PYRO_SESSION=your_session_string       # Generated in step 5
```

### 4. Configure your city and channels
Edit `config.cfg`:
```ini
[Settings]
CITY=м. Київ
CHANNELS=-1001234567890, -1000987654321
```

> **Note:** `CITY` must match the exact `location_title` from the alerts.in.ua API. `CHANNELS` is a comma-separated list of Telegram channel IDs. The userbot account must be subscribed to all of them.

### 5. Log in the userbot (one time, on your own machine)
The userbot logs in with a session string instead of a phone number and confirmation code.

```bash
pip install telethon qrcode
python qr_login.py
```

Scan the QR code in Telegram (**Settings → Devices → Link Desktop Device**). If the account has two-step verification, the script asks for the password. It writes the session string to `pyro_session.txt`. Copy its content into `.env` as `PYRO_SESSION=...` and then delete `pyro_session.txt`.

`telethon` and `qrcode` are needed only for this step and are not part of `requirements.txt`.

### 6. Run the bot
```bash
python main.py
```

---

## 🔐 Session Security

- `PYRO_SESSION` gives **full access to the Telegram account**. Never commit it, and keep `.env`, `pyro_session.txt` and `*.session` in `.gitignore`.
- Use the session in **one place at a time**. Running the same string on two machines simultaneously makes Telegram invalidate it (`AUTH_KEY_DUPLICATED`), and you will have to repeat the QR login.
- Consider using a dedicated Telegram account for the userbot, so an account restriction never affects your main one.
- If the string leaks, terminate the session in **Settings → Devices** in Telegram.

---

## 🤖 Bot Buttons

**Main menu**

| Button | Action |
|--------|--------|
| 🔕 Mute | Silence alerts until the all-clear signal |
| 🔔 Unmute | Resume receiving alerts |
| 📊 Status | Show current alert state, AI status, and user settings |
| ⚙️ Settings | Open the settings menu |
| ℹ️ Info | About the bot |

**Settings menu**

| Button | Action |
|--------|--------|
| 🟢 Activate | Subscribe to threat alerts |
| 🛑 Deactivate | Unsubscribe from all alerts |
| 🟢 Send clear / 🔴 Don't send clear | Toggle official "Clear" messages |
| 🟢 Send AI clear / 🔴 Don't send AI clear | Toggle AI-generated "Probably clear" messages |
| 🔙 Back | Return to the main menu |

---

## 🧯 Troubleshooting

| Problem | Fix |
|---------|-----|
| `No API key was provided` | `GEMINI_API_KEY` is missing in `.env` on the machine running the bot. |
| `PYRO_SESSION не задано` | Run `qr_login.py` and put the resulting string in `.env`. |
| `AUTH_KEY_DUPLICATED` | The same session is running in two places. Stop one and repeat the QR login. |
| `PeerIdInvalid` for a channel | The userbot account is not subscribed to that channel, or the channel ID is wrong. |
| `no such column` in SQLite | Update to the latest `database.py` and restart. Missing columns are added automatically. |

---

## ⚠️ Disclaimer

This bot is a personal project and is intended as an **auxiliary tool only**. It does not replace official emergency alert systems. Stay safe! 🇺🇦
