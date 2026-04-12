"""Entrypoint for the scambaiter."""

import asyncio

from bot import run

if __name__ == "__main__":
    asyncio.run(run())
