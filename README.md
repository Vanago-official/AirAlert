# 🚨 Balistika Alarm Bot

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

**Balistika Alarm Bot** is a Telegram bot that monitors the official Ukrainian air alert API in real-time and instantly notifies subscribed users about direct missile threats to their city.

---

## ✨ Features

- 🚀 **Missile Threat Filtering:** Polls the [alerts.in.ua](https://alerts.in.ua/) API every 10 seconds and broadcasts alerts exclusively for red-level missile threats (`ballistic_missiles`, `cruise_missiles`, `unspecified_missiles`), ignoring general or drone-only alerts.
- 🔕 **Smart Mute:** After the first warning, users are automatically muted to prevent spam. They receive the all-clear message when the threat ends, or can unmute manually at any time.
- 📊 **Status Dashboard:** Users can check the current alert state, active threat types, activation status, and mute status via a button.
- 💾 **Persistent Storage:** User preferences (active/muted) are stored in a local SQLite database via `aiosqlite`.
- 🔄 **Built-in Caching:** Uses the official `alerts-in-ua` client with HTTP caching to minimize API load.

---

## 🏗 Architecture

```
main.py       — Bot handlers, keyboard, alert loop
alarm.py      — API client for alerts.in.ua
database.py   — SQLite operations (users, mute, active)
config.cfg    — City configuration
.env          — Bot token and API key (not committed)
```

**How the alert loop works:**

1. Every 10 seconds, the bot queries the alerts API for the configured city.
2. If a new threat is detected (`alert_level == "red"` AND missile threat is present), it broadcasts `🔴 Danger!` to all active, unmuted users and mutes everyone.
3. When the threat ends (all-clear or downgrade), it broadcasts `🟢 Clear.` to all muted users and resets mute status.

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
BOT_TOKEN=your_telegram_bot_token # Token from @BotFather
ALARM=your_alerts_api_token       # Token from https://alerts.in.ua/
```

### 4. Configure your city
Edit `config.cfg`:
```ini
[Settings]
CITY=м. Київ
```

> **Note:** `CITY` must match the exact `location_title` from the alerts.in.ua API (e.g., `м. Київ` for Kyiv city).

### 5. Run the bot
```bash
python main.py
```

---

## 🤖 Bot Commands & Buttons

| Button | Action |
|--------|--------|
| ✅ Activate | Subscribe to threat alerts |
| 🛑 Deactivate | Unsubscribe from all alerts |
| 🔕 Mute | Silence alerts until the all-clear signal |
| 🔔 Unmute | Resume receiving alerts |
| 📊 Status | Show current alert state and user settings |
| ℹ️ Info | About the bot |

---

## 📁 Project Structure

| File | Description |
|------|-------------|
| `main.py` | Bot entry point, command handlers, alert broadcast loop |
| `alarm.py` | Fetches and parses alert data from the API |
| `database.py` | Async SQLite operations for user management |
| `config.cfg` | City configuration |
| `.env` | Secret tokens (not committed to git) |
| `requirements.txt` | Python dependencies |

---

## ⚠️ Disclaimer

This bot is a personal project and is intended as an **auxiliary tool only**. It does not replace official emergency alert systems. Stay safe! 🇺🇦
