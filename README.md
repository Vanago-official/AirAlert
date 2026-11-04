# 🚨 Balistika Alarm Bot

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

**Balistika Alarm Bot** is a Telegram bot that monitors the official Ukrainian air alert API to instantly notify subscribed users about direct missile threats to their city.

---

## ✨ Features

- 🚀 **Missile Threat Filtering:** Polls the [alerts.in.ua](https://alerts.in.ua/) API every 10 seconds and activates exclusively for red-level missile threats (`ballistic_missiles`, `cruise_missiles`, `unspecified_missiles`).
- 🔕 **Smart Mute:** After the first warning, users are automatically muted to prevent spam. They receive the all-clear message when the threat ends, or can unmute manually at any time to receive subsequent warnings.
- ⚙️ **Granular Settings:** Users can individually opt in or out of official "Clear" messages.
- 📊 **Status Dashboard:** Users can check the current alert state, active threat types, activation status, and mute status via a button.
- 💾 **Persistent Storage:** User preferences are stored in a local SQLite database via `aiosqlite`. Schema changes are applied automatically on startup, so existing databases keep working after updates.

---

## 🏗 Architecture

```text
main.py        — Bot entry point, handlers, alert broadcast loop
alarm.py       — API client for alerts.in.ua
database.py    — SQLite operations (users, mute, active, clear preferences)
config.cfg     — City configuration
.env           — Tokens and API keys (not committed)
```

**How the alert loop works:**

1. **Idle Mode:** The bot queries the alerts API every 10 seconds.
2. **Official Alert:** If a new threat is detected (`alert_level == "red"` AND a missile threat is present), it broadcasts `🔴 Danger!` to all active, unmuted users and mutes everyone.
3. **End of Alert:** When the official API downgrades or clears the alert, it broadcasts `🟢 Clear.` to muted users who opted in, and unmutes everyone.

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

### 3. Configure environment variables
Copy the example and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=your_telegram_bot_token      # Token from @BotFather
ALARM=your_alerts_api_token            # Token from https://alerts.in.ua/
```

### 4. Configure your city
Edit `config.cfg`:
```ini
[Settings]
CITY=м. Київ
```

> **Note:** `CITY` must match the exact `location_title` from the alerts.in.ua API.

### 5. Run the bot
```bash
python main.py
```

---

## 🤖 Bot Buttons

**Main menu**

| Button | Action |
|--------|--------|
| 🔕 Mute | Silence alerts until the all-clear signal |
| 🔔 Unmute | Resume receiving alerts |
| 📊 Status | Show current alert state and user settings |
| ⚙️ Settings | Open the settings menu |
| ℹ️ Info | About the bot |

**Settings menu**

| Button | Action |
|--------|--------|
| 🟢 Activate | Subscribe to threat alerts |
| 🛑 Deactivate | Unsubscribe from all alerts |
| 🟢 Send clear / 🔴 Don't send clear | Toggle official "Clear" messages |
| 🔙 Back | Return to the main menu |

---

## 🧯 Troubleshooting

| Problem | Fix |
|---------|-----|
| `no such column` in SQLite | Update to the latest `database.py` and restart. Schema changes are applied automatically. |

---

## ⚠️ Disclaimer

This bot is a personal project and is intended as an **auxiliary tool only**. It does not replace official emergency alert systems. Stay safe! 🇺🇦
