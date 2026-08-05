import asyncio
import os
import sys
import io
import logging
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from ai_engine import AIEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "1BJWap1wBu8UVcUKfLQ-OHYoNv38blOOuz6atwTkJZ8k2djH71VCwi0pqL3fojoi4Y66-2UO06s1ov1bcHKazh35xVcakvhX9vqe3nWE60O83x2sdGSv_WsDdsxmTqX_K2zImBMyloWHYmW4X7OYZ2XN7ysntMGDw6l4orFGyGduF_xIKC_T8odDXNWf01BIypfyt4tkGvZlDj7VdX_ii1fwMzA6brj5Lpsyzcu6ITt2uCgTdXIfPBcK4MN-RpkA6w91qNik7L-WFW9dHkbzI9R-f3vRXjYT6C3hHWA9ILFgbf0oVlf61uk9-E-vSatgBFl74q0ksCAvuw349EMby_E-CJ_NkTTc=")

ADMIN_USERNAME = "lirph"
ADMIN_USER_ID = 588588275

# Initialize AI Engine
ai_engine = AIEngine(knowledge_base_path="knowledge_base.json")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Analytics & Admin Metrics
stats = {
    "start_time": datetime.now(),
    "total_messages": 0,
    "escalations_count": 0,
    "recent_escalations": []
}

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_client_dm(event):
    sender = await event.get_sender()
    
    if getattr(sender, "bot", False):
        return
        
    sender_id = event.sender_id
    username = (getattr(sender, "username", "") or "").lower()
    sender_name = getattr(sender, "first_name", "") or "User"
    message_text = event.raw_text.strip()
    
    if not message_text:
        return
        
    # ==========================================
    # 👑 ADMIN HANDLER FOR @lirph
    # ==========================================
    if sender_id == ADMIN_USER_ID or username == ADMIN_USERNAME:
        logging.info(f"Admin @{ADMIN_USERNAME} command received: '{message_text}'")
        
        # Build Admin Status Report
        uptime = datetime.now() - stats["start_time"]
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        
        active_chats = len(ai_engine.conversations)
        num_keys = len(ai_engine.gemini_keys)
        
        report_text = (
            f"👑 **ADMIN CONTROL PANEL (@{ADMIN_USERNAME})**\n\n"
            f"🟢 **Bot Status**: Active 24/7 (Gemini AI Key Pool)\n"
            f"⏱ **Uptime**: `{uptime_str}`\n"
            f"🔑 **Active Gemini Keys Pool**: `{num_keys} Keys`\n"
            f"💬 **Active Client Conversations**: `{active_chats}`\n"
            f"📩 **Total Client Messages Handled**: `{stats['total_messages']}`\n"
            f"🚨 **Total Human Escalations Triggered**: `{stats['escalations_count']}`\n\n"
        )
        
        if stats["recent_escalations"]:
            report_text += "📌 **Recent Client Escalations**:\n"
            for esc in stats["recent_escalations"][-5:]:
                report_text += f"- **{esc['name']}** ({esc['username']}): `{esc['text']}` (Reason: {esc['reason']})\n"
        else:
            report_text += "✨ No pending client escalation alerts.\n"
            
        report_text += "\n💡 *Send any message anytime to get live updates and reports.*"
        
        await event.reply(report_text)
        return

    # ==========================================
    # 🤖 CLIENT DM HANDLER (Gemini AI Engine)
    # ==========================================
    stats["total_messages"] += 1
    logging.info(f"Received Client DM from {sender_name} (@{username}): {message_text}")
    
    async with client.action(event.chat_id, "typing"):
        await asyncio.sleep(1.5)
        
        ai_result = ai_engine.generate_response(sender_id, sender_name, message_text)
        reply = ai_result["reply"]
        needs_escalation = ai_result["needs_escalation"]
        reason = ai_result["reason"]
        
        # Reply to client
        await event.reply(reply)
        logging.info(f"Replied to client @{username}: {reply}")
        
        # Trigger Escalation Alert directly to Admin @lirph
        if needs_escalation:
            stats["escalations_count"] += 1
            stats["recent_escalations"].append({
                "name": sender_name,
                "username": f"@{username}" if username else f"ID {sender_id}",
                "text": message_text,
                "reason": reason,
                "time": datetime.now().strftime("%H:%M:%S")
            })
            
            alert_text = (
                f"🚨 **HUMAN ESCALATION ALERT FOR ADMIN @{ADMIN_USERNAME}**\n\n"
                f"👤 **Client Name**: {sender_name}\n"
                f"🔗 **Username**: @{username}\n"
                f"💬 **Client Message**: `{message_text}`\n"
                f"⚠️ **Trigger Reason**: {reason}\n"
                f"🤖 **Bot AI Reply Sent**: `{reply}`"
            )
            
            try:
                admin_entity = await client.get_entity(ADMIN_USERNAME)
                await client.send_message(admin_entity, alert_text)
                logging.info(f"Escalation alert sent directly to Admin @{ADMIN_USERNAME}")
            except Exception as e:
                logging.error(f"Failed sending alert to Admin @{ADMIN_USERNAME}: {e}")
                await client.send_message("me", alert_text)

async def main():
    print("=" * 60)
    print(f"🤖 Autonomous 24/7 AI Client Handler Bot (Admin: @{ADMIN_USERNAME})")
    print("=" * 60)
    
    await client.start()
    me = await client.get_me()
    print(f"✅ Successfully connected to Telegram as {me.first_name} (@{me.username})")
    print(f"🟢 Listening for incoming client DMs. Admin alerts configured for @{ADMIN_USERNAME}.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
