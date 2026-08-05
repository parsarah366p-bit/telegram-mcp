import asyncio
import os
import sys
import io
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from ai_engine import AIEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "1BJWap1wBu8UVcUKfLQ-OHYoNv38blOOuz6atwTkJZ8k2djH71VCwi0pqL3fojoi4Y66-2UO06s1ov1bcHKazh35xVcakvhX9vqe3nWE60O83x2sdGSv_WsDdsxmTqX_K2zImBMyloWHYmW4X7OYZ2XN7ysntMGDw6l4orFGyGduF_xIKC_T8odDXNWf01BIypfyt4tkGvZlDj7VdX_ii1fwMzA6brj5Lpsyzcu6ITt2uCgTdXIfPBcK4MN-RpkA6w91qNik7L-WFW9dHkbzI9R-f3vRXjYT6C3hHWA9ILFgbf0oVlf61uk9-E-vSatgBFl74q0ksCAvuw349EMby_E-CJ_NkTTc=")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-cdt-eyJpZCI6IjU4ODU4ODI3NSIsInUiOiIiLCJuIjoiZGVmYXVsdCIsImoiOiJkZWZhdWx0IiwiayI6ImFwaSJ9.325QlolKUdnhBihiYPHVpou2W85k6pRuI4fEhyvo46s")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://conduit.ozdoev.net/v1")

# Initialize AI Engine with Gemini Key Pool
ai_engine = AIEngine(knowledge_base_path="knowledge_base.json")

# Initialize Telethon Client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_client_dm(event):
    sender = await event.get_sender()
    
    # Filter out bots or invalid senders
    if getattr(sender, "bot", False):
        return
        
    sender_id = event.sender_id
    sender_name = getattr(sender, "first_name", "") or "Client"
    username = f"@{sender.username}" if getattr(sender, "username", None) else f"ID {sender_id}"
    message_text = event.raw_text.strip()
    
    if not message_text:
        return
        
    logging.info(f"Received DM from {sender_name} ({username}): {message_text}")
    
    # Simulate a brief typing indicator for natural interaction
    async with client.action(event.chat_id, "typing"):
        await asyncio.sleep(1.5)
        
        # Generate AI response
        ai_result = ai_engine.generate_response(sender_id, sender_name, message_text)
        reply = ai_result["reply"]
        needs_escalation = ai_result["needs_escalation"]
        reason = ai_result["reason"]
        
        # Send auto-reply to client
        await event.reply(reply)
        logging.info(f"Replied to {username}: {reply}")
        
        # Handle Escalation alert to owner (Saved Messages)
        if needs_escalation:
            alert_text = (
                f"🚨 **HUMAN ESCALATION ALERT**\n\n"
                f"👤 **Client**: {sender_name} ({username})\n"
                f"💬 **Last Message**: `{message_text}`\n"
                f"⚠️ **Reason**: {reason}\n"
                f"🤖 **Bot Reply Sent**: `{reply}`"
            )
            await client.send_message("me", alert_text)
            logging.info(f"Escalation alert sent to Saved Messages for {username}")

async def main():
    print("=" * 60)
    print("🤖 Autonomous 24/7 AI Client Handler Bot is starting...")
    print("=" * 60)
    
    await client.start()
    me = await client.get_me()
    print(f"✅ Successfully connected to Telegram as {me.first_name} (@{me.username})")
    print("🟢 Listening for incoming client DMs 24/7. Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
