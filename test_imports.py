"""Quick sanity check on all three modified modules."""
import persona, llm, bot

print("persona.py OK — SYSTEM_PROMPT length:", len(persona.SYSTEM_PROMPT))
print("llm.py OK — PICTURE_RE present:", hasattr(llm, 'PICTURE_RE'))
print("bot.py: wants_picture in dir:", 'wants_picture' in dir(bot))
print("bot.py: send_picture in dir:", 'send_picture' in dir(bot))
print("bot.py: truncate in dir:", 'truncate' in dir(bot))
print("All imports OK")
