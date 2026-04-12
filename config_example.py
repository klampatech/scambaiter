# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_API_ID   = 12345678                        # Integer. From my.telegram.org
TELEGRAM_API_HASH = "your_api_hash_here"            # String. From my.telegram.org
YOUR_USER_ID      = 123456789                       # Integer. Your own Telegram user ID
PHONE_NUMBER      = "+1234567890"                   # Your Telegram number (for session auth)

# ── LLM (OpenAI-compatible endpoint) ─────────────────────────────────────────
LLM_BASE_URL   = "http://your-llm-server:1234/v1"   # Base URL, no trailing slash
LLM_API_KEY    = "your-api-key"                     # Some servers require non-empty
LLM_MODEL      = "your/model-name"                  # Model identifier your server uses
LLM_MAX_TOKENS = 500
LLM_TEMPERATURE = 0.75

# ── Bot Behaviour ─────────────────────────────────────────────────────────────
REPLY_DELAY_MIN   = 40    # Seconds. Min wait before sending reply (seem human)
REPLY_DELAY_MAX   = 200   # Seconds. Max wait before sending reply
TYPING_SPEED_CPS  = 8     # Chars/second to calculate typing indicator duration
MAX_TYPING_SECS   = 12    # Cap on typing indicator duration regardless of length
MAX_HISTORY_MSGS  = 40    # How many past messages to include in LLM context
