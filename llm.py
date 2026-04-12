"""Async LLM client for OpenAI-compatible APIs."""

import re
import time
from typing import Any

import aiohttp

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
from persona import SYSTEM_PROMPT

# Matches [PICTURE: chester] or [PICTURE: pat] at end of response (with optional leading whitespace)
PICTURE_RE = re.compile(r"\s*\[PICTURE:\s*(chester|pat)\s*\]\s*$", re.IGNORECASE)


async def get_reply(history: list[dict[str, Any]], incoming: str) -> tuple[str, str | None, int]:
    """
    Calls the LLM with system prompt + conversation history + new message.
    Returns (reply_text, picture_subject_or_None, latency_ms).
    picture_subject is 'chester', 'pat', or None — depending on whether the LLM
    appended a [PICTURE: ...] tag.
    Raises on HTTP error or timeout.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": incoming})

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        start = time.monotonic()
        async with session.post(f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers) as resp:
            latency_ms = int((time.monotonic() - start) * 1000)
            resp.raise_for_status()
            data = await resp.json()

    raw = data["choices"][0]["message"]["content"].strip()

    # Extract and strip picture tag if present
    match = PICTURE_RE.search(raw)
    if match:
        picture_subject = match.group(1).lower()
        reply = PICTURE_RE.sub("", raw).strip()
        return reply, picture_subject, latency_ms
    else:
        return raw, None, latency_ms
