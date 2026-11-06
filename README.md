# 🚨 AirAlert

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

**AirAlert** is a Telegram bot that monitors the official Ukrainian alert API and notifies subscribed users whenever any alert starts or ends in their city, naming the alert type.

---

## ✨ Features

- 🚨 **Any Alert:** Polls the [alerts.in.ua](https://alerts.in.ua/) API every 10 seconds and detects every alert type (air raid, artillery, urban fights, chemical, nuclear) and every threat (missiles, drones, aviation, guided bombs, etc.).
- 📨 **Typed Messages:** Each message says which alerts started or ended.
- 🎛 **Per-Type Toggles:** Every alert type can be turned on or off in Settings → 🎛 Alert types.
- 🔕 **Mute:** Mute notifications until all alerts end. You still get the final all-clear.
- 🔕 **Auto-mute mode:** Optional setting. After the first alert message you are muted automatically until the all-clear.
- ⚙️ **Clear Messages:** Opt in or out of end-of-alert messages.
- 📊 **Status Dashboard:** Shows active alerts, alert level and your settings.
- 💾 **Persistent Storage:** SQLite via `aiosqlite`. Schema changes are applied automatically on startup.

---

## 🏗 Architecture

```text
main.py        — Bot entry point, handlers, alert broadcast loop
alarm.py       — API client for alerts.in.ua, list of alert types
database.py    — SQLite operations (users, mute, active, clear, disabled alert types)
config.cfg     — City configuration
.env           — Tokens and API keys (not committed)
```

**How the alert loop works:**

1. The bot queries the alerts API every 10 seconds and collects all `alert_type` and `threat_type` values for the city.
2. **Started:** New types are sent to active, unmuted users who have those types enabled. Users with auto-mute on are muted right after.
3. **Ended:** Types that disappeared are sent to unmuted users with clear messages on.
4. **All clear:** When no alerts remain, muted users also get the message, and all mutes are lifted.
5. If the API request fails, the bot skips that check. It does not send a false all-clear.

---

## 📨 Message Types

| Type | Header | Sent to |
|------|--------|---------|
| Started | `🚨 Alert started — <city>` | Active, unmuted users with the type enabled |
| Ended | `🟢 Alert ended — <city>` | Active, unmuted users with clear on and the type enabled; other alerts still active |
| All clear | `🟢 All clear — <city>` | Active users (muted too) with clear on and the type enabled; no alerts left |

Each message lists the types under the header, e.g. `• 🛸 Drones (UAV)`.

| Key | Label |
|-----|-------|
| `air_raid` | 🚨 Air raid |
| `artillery_shelling` | 💥 Artillery shelling |
| `urban_fights` | ⚔️ Urban fights |
| `chemical` | ☣️ Chemical danger |
| `nuclear` | ☢️ Nuclear danger |
| `ballistic_missiles` | 🚀 Ballistic missiles |
| `cruise_missiles` | 🚀 Cruise missiles |
| `unspecified_missiles` | 🚀 Missiles (unspecified) |
| `mig31k_departure` | ✈️ MiG-31K departure (Kinzhal) |
| `strategic_aircraft_activity` | ✈️ Strategic aviation |
| `tactic_aircraft_activity` | ✈️ Tactical aviation |
| `drones` | 🛸 Drones (UAV) |
| `guided_aerial_bombs` | 💣 Guided aerial bombs |
| `air_defense` | 🛡 Air defense active |
| `unknown` | ❓ Unknown threat |

---

## 🛠 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Vanago-official/AirAlert.git
cd AirAlert
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
| 🔕 Mute | Silence alerts until all alerts end |
| 🔔 Unmute | Resume receiving alerts |
| 📊 Status | Show current alert state and user settings |
| ⚙️ Settings | Open the settings menu |
| ℹ️ Info | About the bot |

**Settings menu**

| Button | Action |
|--------|--------|
| 🟢 Activate | Subscribe to alerts |
| 🛑 Deactivate | Unsubscribe from all alerts |
| 🟢 Send clear / 🔴 Don't send clear | Toggle end-of-alert messages |
| 🔕 Auto-mute: ON / 🔔 Auto-mute: OFF | Toggle auto-mute until all-clear |
| 🎛 Alert types | Turn each alert type on (✅) or off (❌), or all at once |
| 🔙 Back | Return to the main menu |

---

## 🧯 Troubleshooting

| Problem | Fix |
|---------|-----|
| `no such column` in SQLite | Update to the latest `database.py` and restart. Schema changes are applied automatically. |

---

## ⚠️ Disclaimer

This bot is a personal project and is intended as an **auxiliary tool only**. It does not replace official emergency alert systems. Stay safe! 🇺🇦
