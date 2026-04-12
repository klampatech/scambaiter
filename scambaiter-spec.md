# Scambaiter — Build Specification
> Hand this document to Claude Code to build the project from scratch.

---

## Project Overview

A lightweight Python application that runs 24/7 on a Raspberry Pi 5 and automatically replies to Telegram scammers **from the user's own Telegram account** (not a bot account). It identifies scammers by a simple heuristic: any incoming private message from a user who is **not in the account owner's contact list** is treated as a potential scammer.

The bot uses a remote LLM (OpenAI-compatible API) to generate dynamic, human-like replies designed to waste as much of the scammer's time as possible. All conversations are stored in SQLite in a schema designed to support a future web dashboard.

---

## Scammer Playbook Context

The bot is designed specifically to counter **"pig butchering"** romance/investment scams. These follow a near-identical script:

1. **Wrong number opener** — "Hi! Sorry, is this [name]? I think I have the wrong number 😊"
2. **Friendly pivot** — Casual conversation, often with an attractive profile photo
3. **Love bombing** — Daily messages, pet names ("honey", "darling"), fake emotional connection
4. **Lifestyle flex** — Casual mention of crypto wealth, successful relative, investment platform
5. **The hook** — "I can teach you how I made $40k last month, start with just a little"
6. **Fake gains** — Allow small withdrawals to build trust
7. **The slaughter** — Victim goes all in, platform freezes, demands fees

**The bot's goal: stay stuck in phases 1–3 indefinitely.**

---

## Project Structure

```
~/scambaiter/
├── config.py               # All user-configurable settings
├── persona.py              # LLM system prompt / character definition
├── database.py             # SQLite schema + all DB operations
├── llm.py                  # Async LLM client (OpenAI-compatible)
├── bot.py                  # Telethon userbot — event handling logic
├── main.py                 # Entrypoint
├── requirements.txt        # Python dependencies
├── scambaiter.service      # Systemd unit file (output, not run directly)
└── scambaiter.db           # Auto-created on first run (gitignore this)
```

---

## Tech Stack

| Component | Choice | Notes |
|---|---|---|
| Telegram library | **Telethon** | Userbot (acts as real account, not bot API) |
| LLM | **Remote OpenAI-compatible API** | URL + key supplied by user in config |
| HTTP client | **aiohttp** | Async, used for LLM calls |
| Database | **SQLite via stdlib `sqlite3`** | No ORM, plain SQL, dashboard-ready schema |
| Process manager | **systemd** | Generate `.service` file as part of output |
| Python | **3.11+** | Uses `list[dict]` type hints, `match` not required |

---

## File Specifications

### `requirements.txt`
```
telethon
aiohttp
```

---

### `config.py`

All user-configurable values in one place. No values should be hardcoded elsewhere.

```python
# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_API_ID   = 0                        # Integer. From my.telegram.org
TELEGRAM_API_HASH = "your_api_hash_here"     # String. From my.telegram.org
YOUR_USER_ID      = 0                        # Integer. Your own Telegram user ID

# ── LLM (OpenAI-compatible endpoint) ─────────────────────────────────────────
LLM_BASE_URL   = "http://192.168.1.50:1234/v1"   # Base URL, no trailing slash
LLM_API_KEY    = "your-key-or-any-string"         # Some servers require non-empty
LLM_MODEL      = "your-model-name"                # Model identifier your server uses
LLM_MAX_TOKENS = 220
LLM_TEMPERATURE = 0.85

# ── Bot Behaviour ─────────────────────────────────────────────────────────────
REPLY_DELAY_MIN   = 40    # Seconds. Min wait before sending reply (seem human)
REPLY_DELAY_MAX   = 200   # Seconds. Max wait before sending reply
TYPING_SPEED_CPS  = 8     # Chars/second to calculate typing indicator duration
MAX_TYPING_SECS   = 12    # Cap on typing indicator duration regardless of length
MAX_HISTORY_MSGS  = 40    # How many past messages to include in LLM context
```

---

### `persona.py`

The LLM system prompt that defines the character. This should be the only place the persona is defined.

```python
SYSTEM_PROMPT = """
You are replying as the owner of this Telegram account.
Behave like a friendly, slightly lonely 58-year-old retired school teacher named Pat from Ohio.

YOUR PERSONALITY:
- Warm, chatty, a little scattered
- Not very tech-savvy ("sorry, my phone does weird things sometimes!")
- Genuinely curious — ask lots of questions about the other person
- Love to go on tangents about your dog Chester, your garden, your neighbour Linda,
  and your sister Deborah who "knows about money stuff"
- Make occasional small typos, sometimes correct yourself
- Always end your message with a question to keep them engaged

YOUR GOAL: Keep the conversation alive as long as possible without giving money or real personal info.

TACTICS:
- If they mention investing, crypto, or a trading platform: sound intrigued but confused.
  Ask them to explain it more simply. Say you'd need to ask your sister Deborah first.
  Never commit — always "maybe soon, let me think about it!"
- If they push for money: use rotating excuses — car needs new brakes, vet bills for Chester,
  helping nephew with college, roof leak. Stay enthusiastic about the topic despite not committing.
- If they ask for personal info (address, bank details, etc.): misunderstand the question,
  get distracted by a story, or give a vague non-answer.
- If they try to move to another platform: say your phone is confusing and you prefer to
  stay where you are.

TONE: Casual, warm, a little slow to catch on. Not stupid — just trusting and chatty.
Keep replies to 2–4 conversational sentences. Vary your length naturally.

NEVER: Reveal you are automated. Send money. Provide real personal data. Click links.
"""
```

---

### `database.py`

All database logic. Schema is designed to support a future dashboard — **do not simplify it**.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS scammers (
    user_id       INTEGER PRIMARY KEY,
    username      TEXT,
    display_name  TEXT,
    first_seen    DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen     DATETIME DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'active'  -- 'active' | 'ignored' | 'blocked'
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    role        TEXT NOT NULL,        -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    llm_model   TEXT,                 -- model name that generated this reply
    latency_ms  INTEGER,              -- LLM round-trip time in milliseconds
    FOREIGN KEY (user_id) REFERENCES scammers(user_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts   ON messages(timestamp);
```

**Functions to implement:**

| Function | Signature | Behaviour |
|---|---|---|
| `init_db` | `() -> None` | Create tables if not exist. Called once at startup. |
| `upsert_scammer` | `(user_id, username, display_name) -> None` | Insert or update scammer record. On conflict: update username, display_name, last_seen, increment message_count. |
| `save_message` | `(user_id, role, content, model=None, latency_ms=None) -> None` | Insert a message row. |
| `get_history` | `(user_id, limit) -> list[dict]` | Return last `limit` messages as `[{"role": ..., "content": ...}]` ordered oldest-first. |
| `get_all_scammers` | `() -> list` | Return all scammers joined with their latest message timestamp, ordered by most recent activity. |

Use `sqlite3.connect()` with `conn.row_factory = sqlite3.Row`. Use a context manager (`with get_conn() as conn`) for all queries so commits happen automatically.

---

### `llm.py`

Async LLM client. Must use the OpenAI `/v1/chat/completions` endpoint format.

**Function to implement:**

```python
async def get_reply(history: list[dict], incoming: str) -> tuple[str, int]:
    """
    Calls the LLM with the system prompt + conversation history + new message.
    Returns (reply_text, latency_ms).
    Raises on HTTP error or timeout.
    """
```

**Request format:**
```json
{
  "model": "<LLM_MODEL>",
  "messages": [
    {"role": "system", "content": "<SYSTEM_PROMPT>"},
    ...history...,
    {"role": "user", "content": "<incoming>"}
  ],
  "max_tokens": 220,
  "temperature": 0.85
}
```

**Headers:**
```
Authorization: Bearer <LLM_API_KEY>
Content-Type: application/json
```

**Notes:**
- Use `aiohttp.ClientSession` with `timeout=aiohttp.ClientTimeout(total=60)`
- Measure latency using `time.monotonic()` around the request
- Extract reply from `data["choices"][0]["message"]["content"].strip()`

---

### `bot.py`

The Telethon userbot. This is the core of the application.

**Key behaviours:**

1. **Listen for incoming private messages only** (`event.is_private`)
2. **Filter out:**
   - Messages from the account owner (`sender.id == YOUR_USER_ID`)
   - Bot accounts (`sender.bot is True`)
   - Non-text messages (`not event.raw_text`)
   - Contacts (`sender.contact is True`) — this is the core scammer filter
3. **In-flight guard:** Use a `set[int]` of user IDs currently being processed to prevent overlapping async handlers for the same user
4. **On valid non-contact message:**
   - Call `upsert_scammer` and `save_message(..., role="user")`
   - Fetch history via `get_history`
   - Call `get_reply` from `llm.py`
   - Save reply via `save_message(..., role="assistant", model=LLM_MODEL, latency_ms=...)`
   - Wait `random.randint(REPLY_DELAY_MIN, REPLY_DELAY_MAX)` seconds
   - Show typing indicator for `min(len(reply) / TYPING_SPEED_CPS, MAX_TYPING_SECS)` seconds using `client.action(event.chat_id, 'typing')`
   - Send the reply with `event.reply(reply)`
5. **Logging:** Print each incoming message and outgoing reply to stdout with user info, truncated to 120 chars. Print delays and LLM latency.
6. **Error handling:** Wrap the handler body in try/except, log errors, always discard from in-flight set in a `finally` block.

**TelegramClient setup:**
- Session name: `'scambaiter_session'`
- Call `client.start()` (will prompt for phone/code on first run, then saves session)

---

### `main.py`

Minimal entrypoint:

```python
from bot import run

if __name__ == "__main__":
    run()
```

`bot.py` should expose a `run()` function that calls `init_db()`, starts the client, prints a startup message, and calls `client.run_until_disconnected()`.

---

### `scambaiter.service` (generate this file, don't execute it)

```ini
[Unit]
Description=Telegram Scambaiter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/scambaiter
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=15
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## Setup Instructions (include as `SETUP.md`)

### 1. Get Telegram API credentials
Go to [my.telegram.org](https://my.telegram.org), log in, create an app, and copy your `api_id` and `api_hash` into `config.py`.

### 2. Get your own Telegram user ID
You can get this by messaging `@userinfobot` on Telegram. Put the ID in `YOUR_USER_ID` in `config.py`.

### 3. Configure LLM
Set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `config.py` to point at your remote server.

### 4. Install and authenticate
```bash
cd ~/scambaiter
pip install -r requirements.txt
python main.py   # First run: prompts for phone number + Telegram auth code
                 # Creates scambaiter_session.session — back this file up!
```

### 5. Install as a service
```bash
sudo cp scambaiter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scambaiter
sudo journalctl -u scambaiter -f   # Watch live logs
```

---

## Future Dashboard Notes

The SQLite schema is intentionally dashboard-ready. Useful queries for future reference:

```sql
-- Total unique scammers engaged
SELECT COUNT(*) FROM scammers;

-- Most active scammers
SELECT display_name, username, message_count, last_seen
FROM scammers ORDER BY message_count DESC;

-- Full conversation with a specific user
SELECT role, content, timestamp, latency_ms
FROM messages WHERE user_id = ? ORDER BY timestamp ASC;

-- Message volume over time
SELECT DATE(timestamp) as day, COUNT(*) as msgs
FROM messages GROUP BY day ORDER BY day DESC;

-- Average LLM latency
SELECT AVG(latency_ms) FROM messages WHERE role = 'assistant';

-- Time wasted estimate (message count × avg reply delay)
SELECT COUNT(*) * 120 / 60 as estimated_minutes_wasted
FROM messages WHERE role = 'assistant';
```

The schema needs no changes to support a dashboard — just point a frontend (Flask, FastAPI, Datasette, etc.) at `scambaiter.db`.

---

## Constraints & Notes for Claude Code

- **Do not use the Telegram Bot API.** This must use Telethon as a userbot (acting as a real user account).
- **Do not add dependencies** beyond `telethon` and `aiohttp`. No ORM, no dotenv, no additional frameworks.
- **Do not use asyncio for the database.** Use plain synchronous `sqlite3`. The DB calls are fast enough that they don't need to be async.
- **The session file** (`scambaiter_session.session`) must not be in `.gitignore` comments — remind the user to back it up in `SETUP.md`.
- **The contact check** (`sender.contact`) is the primary safety mechanism. If Telethon's `contact` attribute is unreliable on a given account type, add a fallback that fetches the full contact list at startup and caches it as a set of user IDs.
- **No `.env` file handling** — keep config in `config.py` for simplicity on a Pi.
- All files should include brief comments explaining what they do. No over-engineering.
