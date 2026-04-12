"""Telethon userbot for auto-replying to Telegram scammers."""

import asyncio
import random
from pathlib import Path

from telethon import TelegramClient, events

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    YOUR_USER_ID,
    LLM_MODEL,
    REPLY_DELAY_MIN,
    REPLY_DELAY_MAX,
    TYPING_SPEED_CPS,
    MAX_TYPING_SECS,
    MAX_HISTORY_MSGS,
    PHONE_NUMBER,
)
from database import init_db, upsert_scammer, save_message, get_history
from llm import get_reply


IMAGES_DIR = Path(__file__).parent / "images"


# In-flight guard: tracks user IDs currently being processed
in_flight: set[int] = set()


def truncate(text: str, length: int = 120) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


async def send_picture(
    client: TelegramClient, chat_id: int, subject: str, user_id: int
) -> None:
    """
    Pick a random image for the given subject, send it to the chat,
    and record it in the database.

    Args:
        client: TelegramClient instance
        chat_id: Target chat ID
        subject: 'chester' or 'pat'
        user_id: Scammer user ID for DB logging
    """
    folder = IMAGES_DIR / subject
    images = sorted(folder.glob("*.jpg")) or sorted(folder.glob("*.png"))
    if not images:
        print(f"[WARN] No images found in {folder}")
        return
    path = random.choice(images)
    await client.send_file(chat_id, path)
    print(f"[IMG] Sent {path.name} to {chat_id}")

    # Log picture send to database so conversation history is complete
    save_message(user_id, "assistant", f"[sent {subject} picture]")


@events.register(events.NewMessage(incoming=True))
async def handle_message(event: events.NewMessage.Event) -> None:
    """Handle incoming private messages from non-contacts."""
    # Only process private messages
    if not event.is_private:
        return

    sender = await event.get_sender()

    # Filter out: own messages, bots, non-text, contacts
    if sender.id == YOUR_USER_ID:
        return
    if sender.bot:
        return
    if not event.raw_text:
        return
    if sender.contact:
        return

    # In-flight guard: skip if already processing this user
    if sender.id in in_flight:
        return
    in_flight.add(sender.id)

    try:
        # Get sender info
        username = getattr(sender, "username", None)
        display_name = getattr(sender, "first_name", None)
        if hasattr(sender, "last_name") and sender.last_name:
            display_name = f"{display_name} {sender.last_name}"

        # Log incoming message
        print(f"[IN] User {sender.id} ({display_name or username}): {truncate(event.raw_text)}")

        # Save scammer and user message to database
        upsert_scammer(sender.id, username, display_name)
        save_message(sender.id, "user", event.raw_text)

        # Fetch conversation history
        history = get_history(sender.id, MAX_HISTORY_MSGS)

        # Get LLM reply (includes picture decision via [PICTURE: subject] tag)
        reply, picture_subject, latency_ms = await get_reply(history, event.raw_text)

        # Save assistant reply to database (only the text part — no picture tag)
        save_message(sender.id, "assistant", reply, LLM_MODEL, latency_ms)

        # Log outgoing reply
        print(f"[OUT] User {sender.id}: {truncate(reply)}")
        print(f"    LLM latency: {latency_ms}ms")

        # Wait random delay before replying
        delay = random.randint(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
        print(f"    Waiting {delay}s before reply...")
        await asyncio.sleep(delay)

        # Send text reply — but only if there's actual text content
        # (if reply is empty after picture tag was stripped, skip sending a blank message)
        client = event.client
        if reply.strip():
            typing_duration = min(len(reply) / TYPING_SPEED_CPS, MAX_TYPING_SECS)
            async with client.action(event.chat_id, "typing"):
                await asyncio.sleep(typing_duration)
            await event.reply(reply)
            print(f"    Reply sent!")
        else:
            print(f"    (no text to send)")

        # Send picture if LLM requested one — this also logs to DB
        if picture_subject:
            print(f"    LLM requested {picture_subject} picture — sending...")
            await send_picture(client, event.chat_id, picture_subject, sender.id)

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
    finally:
        in_flight.discard(sender.id)


def _auth_code_callback() -> str:
    """Read verification code from a file. Used during initial session auth."""
    code_file = Path(__file__).parent / ".auth_code"
    if code_file.exists():
        code = code_file.read_text().strip()
        code_file.unlink()
        print(f"[AUTH] Read code from .auth_code file")
        return code
    raise RuntimeError("No .auth_code file found — place the Telegram verification code there")


async def run() -> None:
    """Initialize database, start Telegram client, and run until disconnected."""
    # Initialize database
    init_db()

    # Create and start client
    client = TelegramClient("scambaiter_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)
    client.add_event_handler(handle_message)

    print("Scambaiter started! Waiting for messages...")

    await client.start(phone=PHONE_NUMBER, code_callback=_auth_code_callback)
    await client.run_until_disconnected()
