import telebot
from telebot import types
import sqlite3
from datetime import datetime
import re
import os
import time
import threading 
from flask import Flask
from threading import Thread
import gc
import psutil

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте переменную окружения BOT_TOKEN")

CHAT_ID = -1003723055728  # ID чата админов

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)

# ID администраторов
ADMINS = [6206017016, 1176412025]

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
message_to_user = {}  # {message_id: user_id}
user_pending_content = {}  # {user_id: {'type': 'text'/'media'/'album', 'data': ...}}

# Для пагинации банлиста
banlist_current_page = {}  # {chat_id: page_number}
BANS_PER_PAGE = 5  # Количество профилей на странице

# ========== БАЗА ДАННЫХ НА ДИСКЕ RENDER ==========
# Путь к постоянному диску Render
DATA_DIR = '/opt/render/project/src/data'
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'bans.db')

# Используем отдельное соединение для каждого потока
db_connections = {}
db_lock = threading.Lock()

def get_db_connection():
    """Получает соединение с БД для текущего потока"""
    thread_id = threading.get_ident()
    if thread_id not in db_connections:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        db_connections[thread_id] = conn
    return db_connections[thread_id]

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            username TEXT,
            reason TEXT,
            banned_by INTEGER,
            banned_by_name TEXT,
            banned_at TEXT
        )
    ''')
    conn.commit()

init_db()

def add_ban(user_id, user_name, username, reason, banned_by, banned_by_name):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO bans 
            (user_id, user_name, username, reason, banned_by, banned_by_name, banned_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, username, reason, banned_by, banned_by_name, datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()

def remove_ban(user_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def is_banned(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM bans WHERE user_id = ?', (user_id,))
    result = cursor.fetchone() is not None
    return result

def get_ban_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_name, username, reason, banned_by_name, banned_at FROM bans WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def get_all_bans():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, user_name, username, reason, banned_by_name, banned_at FROM bans ORDER BY banned_at DESC')
    return cursor.fetchall()

# ========== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ USER_ID ИЗ СООБЩЕНИЯ ==========
def get_user_id_from_message(msg):
    if msg.message_id in message_to_user:
        return message_to_user[msg.message_id]
    
    if msg.text or msg.caption:
        text = msg.text or msg.caption
        match = re.search(r"🆔 ID: (?:<code>)?(\d+)(?:</code>)?", text)
        if match:
            return int(match.group(1))
    return None

# ========== КОМАНДА /START ==========
START_PHOTO_URL = "https://i.postimg.cc/BQJ8bXP1/photo-2026-04-09-18-55-14.jpg"

@bot.message_handler(commands=['start'])
def start(message):
    hello_text = """
﹌﹌﹌﹌ . . '''ᅠ ᅠ♱  ᅠ   𝅄  ﹌﹌﹌  . 𓏲

          ╰┈  𝑾𝑬𝑳⊹ ࣪ ˖ 𝑪𝑶𝑴𝑬 

𝑻𝒐𝒊, 𝒄𝒐𝒎𝒎𝒆 𝒖𝒏 𝒄𝒐𝒖𝒕𝒆𝒂𝒖,
𝑻𝒖 𝒆𝒔 𝒆𝒏𝒕𝒓é𝒆 𝒅𝒂𝒏𝒔 𝒎𝒐𝒏 𝒄œ𝒖𝒓.
𝑻𝒆𝒔 𝒅é𝒎𝒐𝒏𝒔 𝒕𝒐𝒖𝒓𝒏𝒆𝒏𝒕 𝒅𝒂𝒏𝒔 𝒎𝒐𝒏 𝒆𝒔𝒑𝒓𝒊𝒕,
𝑬𝒕 𝒇𝒐𝒏𝒕 𝒅𝒆 𝒎𝒂 𝒕𝒓𝒊𝒔𝒕𝒆𝒔𝒔𝒆 𝒕𝒐𝒏 𝒍𝒊𝒕.

𝑱𝒆 𝒔𝒖𝒊𝒔 𝒑𝒓𝒊𝒔𝒐𝒏𝒏𝒊𝒆𝒓, 𝒇𝒂𝒊𝒃𝒍𝒆 𝒆𝒕 𝒑𝒆𝒓𝒅𝒖,
𝑪𝒐𝒎𝒎𝒆 𝒖𝒏 𝒋𝒐𝒖𝒆𝒖𝒓 𝒐𝒖 𝒖𝒏 𝒊𝒗𝒓𝒐𝒈𝒏𝒆.
𝑴𝒂𝒖𝒅𝒊𝒕𝒆 𝒔𝒐𝒊𝒔 𝒕𝒂 𝒔𝒐𝒖𝒓𝒊𝒓𝒆,
𝑻𝒐𝒊, 𝒎𝒂 𝒅𝒆𝒔𝒕𝒊𝒏é𝒆 𝒄𝒓𝒖𝒆𝒍𝒍𝒆

ᴧюбиᴛᴇ, бᴇᴩᴇᴦиᴛᴇ, ʙᴇдиᴛᴇ ᴄᴇбя ᴨᴩиᴧично. . .
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('ɯᴀбᴧон ᴀнᴋᴇᴛы', callback_data='anketa_text'))
    markup.add(types.InlineKeyboardButton('ᴀнᴋᴇᴛницᴀ', url='https://t.me/+wKdYUS_mahgwZjdi'))
    markup.add(types.InlineKeyboardButton('инɸᴏ ᴋᴀнᴀᴧ', url='https://t.me/+uZkT_EWW0tcwZjcy'))

    try:
        bot.send_photo(
            message.chat.id, 
            START_PHOTO_URL,
            caption=hello_text, 
            reply_markup=markup, 
            parse_mode='HTML'
        )
    except Exception as e:
        bot.send_message(
            message.chat.id, 
            hello_text, 
            reply_markup=markup, 
            parse_mode='HTML'
        )
        print(f"Ошибка загрузки фото: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'anketa_text')
def handle_query(call):
    send_anketa(call.message)
    bot.answer_callback_query(call.id)

def send_anketa(message):
    anketa_text = """
 ✦ ━━━━ ✦ ━━━━ ✦
 🕯 <b>𝔠𝔥𝔞𝔯𝔞𝔠𝔱𝔢𝔯 𝔭𝔯𝔬𝔣𝔦𝔩𝔢 𝔱𝔢𝔪𝔭𝔩𝔞𝔱𝔢</b> 🕯
 Ⅰ. Иʍя / Вᴏɜᴩᴀᴄᴛ 
 —
 Ⅱ. Рᴀᴄᴀ 
 —
    〔Ⅱ.Ⅰ〕 Обᴩᴀщᴇниᴇ (дᴧя ʙᴀʍᴨиᴩᴏʙ)
 Кᴇʍ и ᴋᴏᴦдᴀ быᴧ ᴏбᴩᴀщён:
    〔Ⅱ.Ⅱ〕 Аᴧᴧᴇᴩᴦии (дᴧя ʙᴀʍᴨиᴩᴏʙ, ʍиниʍуʍ 4)
    〔Ⅱ.Ⅲ〕 Сᴨᴏᴄᴏбнᴏᴄᴛи (дᴧя ʙᴀʍᴨиᴩᴏʙ, ʍᴀᴋᴄиʍᴀᴧьнᴏ 2)
 —
 Ⅲ. Сᴏциᴀᴧьный ᴄᴛᴀᴛуᴄ (дᴧя ʙᴄᴇх)
 —
 Дᴏᴧжнᴏᴄᴛь / Рᴏд дᴇяᴛᴇᴧьнᴏᴄᴛи
 —
 Ⅴ. Биᴏᴦᴩᴀɸия 
 (ʍиниʍᴀᴧьнᴏᴇ ᴋᴏᴧичᴇᴄᴛʙᴏ ᴄиʍʙᴏᴧᴏʙ — 1000.)
 —
 ⅤⅠ. Оᴛнᴏɯᴇниᴇ ʙᴀɯᴇᴦᴏ ᴨᴇᴩᴄᴏнᴀжᴀ ᴋ ᴧюдяʍ/ᴏхᴏᴛниᴋᴀʍ/ʙᴀʍᴨиᴩᴀʍ.
 —
 • <b>Бᴩᴏнь нᴀ ᴨᴇᴩᴄᴏнᴀжᴀ ᴄᴛᴀʙиᴛᴄя ᴛᴏᴧьᴋᴏ ᴨᴏᴄᴧᴇ ᴨᴏдᴛʙᴇᴩждᴇния ʙᴏɜᴩᴀᴄᴛᴀ.</b>
 • Пᴇᴩᴇд ᴨᴏдᴀчᴇй ᴀнᴋᴇᴛы <b>убᴇдиᴛᴇᴄь</b>, чᴛᴏ ᴏнᴀ <u>ᴄᴏᴏᴛʙᴇᴛᴄᴛʙуᴇᴛ ᴛᴩᴇбᴏʙᴀнияʍ</u>, уᴋᴀɜᴀнныʍ <b>ʙ ᴨᴩᴀʙиᴧᴀх</b>.
 """
    bot.send_message(message.chat.id, anketa_text, parse_mode='HTML')

def ask_send_mode(user_id, content_data):
    """Спрашивает режим и сохраняет контент для отправки после выбора"""
    user_pending_content[user_id] = content_data
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌍 ᴨубᴧично", callback_data=f"mode_public_{user_id}"),
        types.InlineKeyboardButton("👤 ᴀнониʍно", callback_data=f"mode_anonymous_{user_id}"),
        types.InlineKeyboardButton("❌ оᴛʍᴇнᴀ", callback_data=f"mode_cancel_{user_id}")
    )
    bot.send_message(
        user_id,
        "📨 <b>ᴋᴀᴋ оᴛᴨᴩᴀʙиᴛь ᴄообщᴇниᴇ ᴀдʍиниᴄᴛᴩᴀᴛоᴩᴀʍ?</b>\n\n"
        "• <b>ᴨубᴧично</b> — ᴀдʍиниᴄᴛᴩᴀᴛоᴩ уʙидиᴛ ʙᴀɯᴇ иʍя\n"
        "• <b>ᴀнониʍно</b> — ᴀдʍиниᴄᴛᴩᴀᴛоᴩ нᴇ узнᴀᴇᴛ, ᴋᴛо нᴀᴨиᴄᴀᴧ\n"
        "• <b>оᴛʍᴇнᴀ</b> — оᴛᴨᴩᴀʙиᴛь ᴄообщᴇниᴇ ᴨозжᴇ\n"
        "<i>ᴀнᴏниʍнᴏ ᴏᴛᴨᴩᴀʙᴧᴇнныᴇ ᴀнᴋᴇᴛы нᴇ будуᴛ ᴩᴀᴄᴄʍᴏᴛᴩᴇны</i>",
        parse_mode='HTML',
        reply_markup=markup
    )

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type == 'private')
def handle_text_message(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        ban_info = get_ban_info(user_id)
        reason = ban_info[2] if ban_info else "не указана"
        bot.reply_to(message, f"🚫 ʙы зᴀбᴀнᴇны\n\nʙы нᴇ ʍожᴇᴛᴇ оᴛᴨᴩᴀʙᴧяᴛь ᴄообщᴇния ᴀдʍиниᴄᴛᴩᴀᴛоᴩᴀʍ.\n\nᴨᴩичинᴀ: {reason}", parse_mode='HTML')
        return

    # ========== ПОЛНЫЙ ЗАПРЕТ КОМАНД ==========
    if message.text.startswith('/'):
        bot.reply_to(
            message,
            "❌ <b>Отправка команд запрещена</b>\n\n"
            "Пожалуйста, напишите обычное сообщение без '/'",
            parse_mode='HTML'
        )
        return
        
    # Сохраняем текст и спрашиваем режим
    content_data = {
        'type': 'text',
        'text': message.text,
        'user_name': message.from_user.first_name,
        'username': message.from_user.username,
        'user_id': user_id
    }
    ask_send_mode(user_id, content_data)

# ========== ОБРАБОТКА МЕДИА (включая альбомы) ==========
# Словарь для сбора альбомов с блокировкой
album_collector = {}
album_lock = threading.Lock()

@bot.message_handler(content_types=['photo', 'video', 'audio', 'document', 'voice', 'sticker', 'video_note'], func=lambda message: message.chat.type == 'private')
def handle_media(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        ban_info = get_ban_info(user_id)
        reason = ban_info[2] if ban_info else "не указана"
        bot.reply_to(message, f"🚫 ʙы зᴀбᴀнᴇны\n\nʙы нᴇ ʍожᴇᴛᴇ оᴛᴨᴩᴀʙᴧяᴛь ᴄообщᴇния ᴀдʍиниᴄᴛᴩᴀᴛоᴩᴀʍ.\n\nᴨᴩичинᴀ: {reason}", parse_mode='HTML')
        return
    
    # Определяем, часть ли это альбома
    if message.media_group_id:
        # Это альбом — собираем части
        with album_lock:
            if user_id not in album_collector:
                album_collector[user_id] = {'messages': [], 'timer': None, 'caption': None, 'media_group_id': message.media_group_id}
            
            collector = album_collector[user_id]
            
            # Проверяем, что это тот же альбом
            if collector['media_group_id'] != message.media_group_id:
                # Это новый альбом, отправляем старый
                if collector['timer']:
                    collector['timer'].cancel()
                finish_album_collection(user_id)
                # Создаём новый коллектор
                album_collector[user_id] = {'messages': [message], 'timer': None, 'caption': message.caption, 'media_group_id': message.media_group_id}
                collector = album_collector[user_id]
            else:
                collector['messages'].append(message)
                # Сохраняем подпись, если есть
                if message.caption and not collector['caption']:
                    collector['caption'] = message.caption
            
            # Сбрасываем таймер
            if collector['timer']:
                collector['timer'].cancel()
            
            # Устанавливаем новый таймер на 2 секунды для надёжности
            timer = threading.Timer(2.0, finish_album_collection, args=[user_id])
            collector['timer'] = timer
            timer.start()
    else:
        # Одиночное медиа — сразу спрашиваем режим
        content_data = {
            'type': 'single_media',
            'message': message,
            'user_name': message.from_user.first_name,
            'username': message.from_user.username,
            'user_id': user_id
        }
        ask_send_mode(user_id, content_data)

def finish_album_collection(user_id):
    """Вызывается когда альбом собран"""
    with album_lock:
        if user_id not in album_collector:
            return
        
        collector = album_collector[user_id]
        messages = collector['messages'].copy()
        caption = collector['caption']
        
        # Очищаем коллектор
        if collector['timer']:
            collector['timer'].cancel()
        del album_collector[user_id]
    
    if not messages:
        return
    
    # Сохраняем альбом и спрашиваем режим
    content_data = {
        'type': 'album',
        'messages': messages,
        'caption': caption,
        'user_name': messages[0].from_user.first_name,
        'username': messages[0].from_user.username,
        'user_id': user_id
    }
    ask_send_mode(user_id, content_data)

# ========== ОБРАБОТЧИК ВЫБОРА РЕЖИМА ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def handle_mode_choice(call):
    parts = call.data.split('_')
    mode = parts[1]
    user_id = int(parts[2])
    
    if mode == 'cancel':
        if user_id in user_pending_content:
            del user_pending_content[user_id]
        with album_lock:
            if user_id in album_collector:
                collector = album_collector[user_id]
                if collector['timer']:
                    collector['timer'].cancel()
                del album_collector[user_id]
        bot.edit_message_text(
            "ᴛᴇᴨᴇᴩь ʙы ᴄнᴏʙᴀ ʍᴏжᴇᴛᴇ ᴏᴛᴨᴩᴀʙᴧяᴛь ᴄᴏᴏбщᴇния.\n\n❌ ᴏᴛᴨᴩᴀʙᴋᴀ ᴄᴏᴏбщᴇния ᴏᴛʍᴇнᴇнᴀ.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    
    if user_id not in user_pending_content:
        bot.edit_message_text(
            "❌ Срок действия запроса истёк. Отправьте сообщение заново.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    
    content_data = user_pending_content[user_id]
    del user_pending_content[user_id]
    
    bot.edit_message_text(
        f"╋ ━ ᴩᴇжиʍ <b>{'ᴨубᴧичной' if mode == 'public' else 'ᴀнониʍной'}</b> оᴛᴨᴩᴀʙᴋи ʙыбᴩᴀн.\n\n⏳ ᴏᴛᴨᴩᴀʙᴧяю ʙᴀɯᴇ ᴄообщᴇниᴇ...",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    
    try:
        if content_data['type'] == 'text':
            send_text_to_admins(content_data, mode)
        elif content_data['type'] == 'single_media':
            send_single_media_to_admins(content_data, mode)
        elif content_data['type'] == 'album':
            send_album_to_admins(content_data, mode)
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при отправке. Попробуйте ещё раз.")
    
    bot.answer_callback_query(call.id)

def send_text_to_admins(data, mode):
    user_id = data['user_id']
    user_name = data['user_name']
    username = data['username']
    text = data['text']
    
    markup = None
    if mode == 'public' and username:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 Профиль", url=f"https://t.me/{username}"))
    
    if mode == 'public':
        sender_text = f"📩 <b>Отправитель:</b> {user_name}\n🆔 ID: <code>{user_id}</code>"
    else:
        sender_text = "👤 <b>Отправитель:</b> Аноним\n🆔 ID: скрыт"
    
    sent_msg = bot.send_message(
        CHAT_ID,
        f"{sender_text}\n📝 <b>Сообщение:</b>\n{text}",
        parse_mode='HTML',
        reply_markup=markup
    )
    
    if sent_msg:
        message_to_user[sent_msg.message_id] = user_id
    
    try:
        mode_text = "ᴨубᴧично" if mode == 'public' else "ᴀнониʍно"
        bot.send_message(
            user_id,
            f"⤿ ᴄообщᴇниᴇ оᴛᴨᴩᴀʙᴧᴇно {mode_text}!\n\nᴋоᴦдᴀ ᴀдʍиниᴄᴛᴩᴀᴛоᴩ оᴛʙᴇᴛиᴛ, ʙы ᴨоᴧучиᴛᴇ уʙᴇдоʍᴧᴇниᴇ."
        )
    except Exception as e:
        print(f"Ошибка отправки подтверждения: {e}")

def send_single_media_to_admins(data, mode):
    user_id = data['user_id']
    user_name = data['user_name']
    username = data['username']
    message = data['message']
    caption = message.caption if message.caption else ""
    
    markup = None
    if mode == 'public' and username:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 Профиль", url=f"https://t.me/{username}"))
    
    if mode == 'public':
        sender_text = f"📩 <b>Отправитель:</b> {user_name}\n🆔 ID: <code>{user_id}</code>"
    else:
        sender_text = "👤 <b>Отправитель:</b> Аноним\n🆔 ID: скрыт"
    
    media_type = ""
    if message.photo:
        media_type = "Фото"
    elif message.video:
        media_type = "Видео"
    elif message.video_note:
        media_type = "Видеокружок"
    elif message.audio:
        media_type = "Аудио"
    elif message.document:
        media_type = f"Документ: {message.document.file_name}" if message.document.file_name else "Документ"
    elif message.voice:
        media_type = "Голосовое"
    elif message.sticker:
        media_type = "Стикер"
    
    full_caption = f"{sender_text}\n📎 <b>{media_type}</b>"
    if caption:
        full_caption += f"\n\n📝 <b>Подпись:</b> {caption}"
    
    sent_msg = None
    
    try:
        if message.photo:
            sent_msg = bot.send_photo(
                CHAT_ID,
                message.photo[-1].file_id,
                caption=full_caption[:1024],
                parse_mode='HTML',
                reply_markup=markup
            )
        elif message.video:
            sent_msg = bot.send_video(
                CHAT_ID,
                message.video.file_id,
                caption=full_caption[:1024],
                parse_mode='HTML',
                reply_markup=markup
            )
        elif message.video_note:
            sent_msg = bot.send_video_note(
                CHAT_ID,
                message.video_note.file_id,
                reply_markup=markup
            )
            if sent_msg:
                message_to_user[sent_msg.message_id] = user_id
            bot.send_message(CHAT_ID, full_caption, parse_mode='HTML')
        elif message.audio:
            sent_msg = bot.send_audio(
                CHAT_ID,
                message.audio.file_id,
                caption=full_caption[:1024],
                parse_mode='HTML',
                reply_markup=markup
            )
        elif message.document:
            sent_msg = bot.send_document(
                CHAT_ID,
                message.document.file_id,
                caption=full_caption[:1024],
                parse_mode='HTML',
                reply_markup=markup
            )
        elif message.voice:
            sent_msg = bot.send_voice(
                CHAT_ID,
                message.voice.file_id,
                caption=full_caption[:1024],
                parse_mode='HTML',
                reply_markup=markup
            )
        elif message.sticker:
            sent_msg = bot.send_sticker(CHAT_ID, message.sticker.file_id, reply_markup=markup)
            bot.send_message(CHAT_ID, full_caption, parse_mode='HTML')
        
        if sent_msg and message.content_type != 'video_note':
            message_to_user[sent_msg.message_id] = user_id
    except Exception as e:
        print(f"Ошибка отправки медиа: {e}")
        raise
    
    try:
        mode_text = "ᴨубᴧично" if mode == 'public' else "ᴀнониʍно"
        bot.send_message(
            user_id, 
            f"⤿ ᴄообщᴇниᴇ оᴛᴨᴩᴀʙᴧᴇно {mode_text}!\n\nᴋоᴦдᴀ ᴀдʍиниᴄᴛᴩᴀᴛоᴩ оᴛʙᴇᴛиᴛ, ʙы ᴨоᴧучиᴛᴇ уʙᴇдоʍᴧᴇниᴇ."
        )
    except Exception as e:
        print(f"Ошибка отправки подтверждения: {e}")

def send_album_to_admins(data, mode):
    user_id = data['user_id']
    user_name = data['user_name']
    username = data['username']
    messages = data['messages']
    caption = data.get('caption', '')
    
    print(f"Отправка альбома: {len(messages)} файлов, подпись: {caption}")
    
    markup = None
    if mode == 'public' and username:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 Профиль", url=f"https://t.me/{username}"))
    
    if mode == 'public':
        sender_text = f"📩 <b>Отправитель:</b> {user_name}\n🆔 ID: <code>{user_id}</code>"
    else:
        sender_text = "👤 <b>Отправитель:</b> Аноним\n🆔 ID: скрыт"
    
    info_text = f"{sender_text}\n📎 <b>Альбом ({len(messages)} файлов)</b>"
    if caption:
        info_text += f"\n\n📝 <b>Подпись:</b> {caption}"
    
    media_group = []
    
    for i, msg in enumerate(messages):
        try:
            msg_caption = caption if (i == 0 and caption) else None
            
            if msg.photo:
                media_group.append(types.InputMediaPhoto(msg.photo[-1].file_id, caption=msg_caption, parse_mode='HTML'))
            elif msg.video:
                media_group.append(types.InputMediaVideo(msg.video.file_id, caption=msg_caption, parse_mode='HTML'))
            elif msg.audio:
                media_group.append(types.InputMediaAudio(msg.audio.file_id, caption=msg_caption, parse_mode='HTML'))
            elif msg.document:
                media_group.append(types.InputMediaDocument(msg.document.file_id, caption=msg_caption, parse_mode='HTML'))
        except Exception as e:
            print(f"Ошибка обработки элемента альбома {i}: {e}")
    
    if media_group:
        try:
            print(f"Отправка media_group из {len(media_group)} элементов")
            sent_messages = bot.send_media_group(CHAT_ID, media_group)
            print(f"Отправлено {len(sent_messages)} сообщений")
            
            for msg in sent_messages:
                message_to_user[msg.message_id] = user_id
            
            info_msg = bot.send_message(CHAT_ID, info_text, parse_mode='HTML', reply_markup=markup)
            if info_msg:
                message_to_user[info_msg.message_id] = user_id
                
        except Exception as e:
            print(f"Ошибка отправки альбома: {e}")
            bot.send_message(user_id, "⚠️ Не удалось отправить альбомом, отправляю по одному...")
            for msg in messages:
                try:
                    temp_data = {
                        'type': 'single_media',
                        'message': msg,
                        'user_name': user_name,
                        'username': username,
                        'user_id': user_id
                    }
                    send_single_media_to_admins(temp_data, mode)
                    time.sleep(0.5)
                except Exception as e2:
                    print(f"Ошибка отправки отдельного медиа: {e2}")
            return
    
    try:
        mode_text = "ᴨубᴧично" if mode == 'public' else "ᴀнониʍно"
        bot.send_message(
            user_id, 
            f"⤿ ᴀᴧьбᴏʍ иɜ {len(messages)} ɸᴀйᴧᴏʙ ᴏᴛᴨᴩᴀʙᴧᴇн {mode_text}!\n\nᴋоᴦдᴀ ᴀдʍиниᴄᴛᴩᴀᴛоᴩ оᴛʙᴇᴛиᴛ, ʙы ᴨоᴧучиᴛᴇ уʙᴇдоʍᴧᴇниᴇ."
        )
    except Exception as e:
        print(f"Ошибка отправки подтверждения: {e}")

# ========== КОМАНДА /BAN ==========
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.chat.id != CHAT_ID:
        return
    
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔ У вас нет прав для этой команды")
        return
    
    user_id = None
    reason = "Не указана"
    user_name = None
    username = None
    
    if message.reply_to_message:
        user_id = get_user_id_from_message(message.reply_to_message)
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            reason = parts[1]
    
    if not user_id and len(message.text.split()) > 1:
        parts = message.text.split(maxsplit=2)
        try:
            user_id = int(parts[1])
            if len(parts) > 2:
                reason = parts[2]
        except ValueError:
            pass
    
    if not user_id:
        bot.reply_to(message, 
            "❌ <b>Не удалось найти пользователя</b>\n\n"
            "Использование:\n"
            "• Ответьте на сообщение пользователя и напишите: <code>/ban причина</code>\n"
            "• Или: <code>/ban 123456 причина</code>",
            parse_mode='HTML')
        return
    
    try:
        chat = bot.get_chat(user_id)
        user_name = chat.first_name
        username = chat.username
    except:
        user_name = f"User_{user_id}"
    
    add_ban(user_id, user_name, username, reason, message.from_user.id, message.from_user.first_name)
    
    ban_text = f"✅ <b>Пользователь забанен</b>\n\n"
    ban_text += f"👤 Имя: {user_name}\n"
    ban_text += f"🆔 ID: <code>{user_id}</code>\n"
    if username:
        ban_text += f"📢 Username: @{username}\n"
    ban_text += f"📝 Причина: {reason}\n"
    ban_text += f"👮 Админ: {message.from_user.first_name}"
    
    bot.reply_to(message, ban_text, parse_mode='HTML')
    
    try:
        bot.send_message(user_id, 
            f"🚫 <b>ʙы быᴧи зᴀбᴀнᴇны</b>\n\n"
            f"📝 ᴨᴩичинᴀ: {reason}\n",
            parse_mode='HTML')
    except:
        pass

# ========== КОМАНДА /UNBAN ==========
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.chat.id != CHAT_ID:
        return
    
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔ У вас нет прав")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Использование: /unban <user_id>")
        return
    
    try:
        user_id = int(parts[1])
        ban_info = get_ban_info(user_id)
        
        if remove_ban(user_id):
            unban_text = f"✅ <b>Пользователь разбанен</b>\n\n"
            if ban_info:
                unban_text += f"👤 Имя: {ban_info[0]}\n"
                unban_text += f"🆔 ID: <code>{user_id}</code>\n"
                if ban_info[1]:
                    unban_text += f"📢 Username: @{ban_info[1]}\n"
                unban_text += f"📝 Причина бана: {ban_info[2]}"
            
            bot.reply_to(message, unban_text, parse_mode='HTML')
            
            try:
                bot.send_message(user_id, "✅ <b>ʙы быᴧи ᴩᴀзбᴀнᴇны</b>\n\nᴛᴇᴨᴇᴩь ʙы ᴄноʙᴀ ʍожᴇᴛᴇ оᴛᴨᴩᴀʙᴧяᴛь ᴄообщᴇния ᴀдʍиниᴄᴛᴩᴀᴛоᴩᴀʍ.", parse_mode='HTML')
            except:
                pass
        else:
            bot.reply_to(message, f"❌ Пользователь {user_id} не в бане")
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID")

# ========== КОМАНДА /CLEARBANS ==========
@bot.message_handler(commands=['clearbans'])
def clearbans_command(message):
    if message.chat.id != CHAT_ID:
        return
    
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔ У вас нет прав")
        return
    
    bans = get_all_bans()
    
    if not bans:
        bot.reply_to(message, "📋 <b>Банлист уже пуст</b>", parse_mode='HTML')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Да, очистить", callback_data="clearbans_confirm"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="clearbans_cancel")
    )
    
    bot.reply_to(
        message,
        f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        f"Вы собираетесь удалить <b>ВСЕХ</b> забаненных пользователей.\n"
        f"Всего банов: <b>{len(bans)}</b>\n\n"
        f"Это действие <b>НЕВОЗМОЖНО ОТМЕНИТЬ</b>.\n\n"
        f"Вы уверены?",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('clearbans_'))
def clearbans_callback(call):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔ У вас нет прав", show_alert=True)
        return
    
    action = call.data.replace('clearbans_', '')
    
    if action == 'cancel':
        bot.edit_message_text(
            "❌ Очистка банлиста отменена.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id, "Отменено")
        return
    
    if action == 'confirm':
        bans = get_all_bans()
        total_bans = len(bans)
        
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM bans')
            conn.commit()
        
        bot.edit_message_text(
            f"✅ <b>Банлист очищен!</b>\n\n"
            f"Удалено пользователей: <b>{total_bans}</b>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id, f"✅ Удалено {total_bans} банов", show_alert=True)

# ========== ПАГИНАЦИЯ ДЛЯ БАНЛИСТА ==========

def show_banlist_page(chat_id, page, reply_to=None):
    """Показывает страницу банлиста"""
    bans = get_all_bans()
    total_pages = (len(bans) + BANS_PER_PAGE - 1) // BANS_PER_PAGE if bans else 1
    
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1
    
    banlist_current_page[chat_id] = page
    
    start = page * BANS_PER_PAGE
    end = min(start + BANS_PER_PAGE, len(bans))
    
    text = f"📋 <b>ЗАБАНЕННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n"
    text += f"Всего: {len(bans)} | Страница {page + 1}/{total_pages}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, ban in enumerate(bans[start:end], start=start + 1):
        user_id, user_name, username, reason, banned_by, banned_at = ban
        text += f"<b>{i}. {user_name}</b>\n"
        text += f"   🆔 <code>{user_id}</code>\n"
        if username:
            text += f"   📢 @{username}\n"
        else:
            text += f"   📢 <i>нет username</i>\n"
        text += f"   📝 {reason[:40]}\n"
        text += f"   ⏰ {banned_at}\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for ban in bans[start:end]:
        user_id, user_name, username, reason, banned_by, banned_at = ban
        if username:
            markup.add(types.InlineKeyboardButton(
                f"👤 {user_name}",
                url=f"https://t.me/{username}"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                f"👤 {user_name} (инфо)",
                callback_data=f"baninfo_{user_id}"
            ))
    
    markup.add(types.InlineKeyboardButton("━━━ НАВИГАЦИЯ ━━━", callback_data="banpage_info"))
    
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⏮", callback_data=f"banpage_0"))
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("◀️", callback_data=f"banpage_{page-1}"))
    
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="banpage_info"))
    
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("▶️", callback_data=f"banpage_{page+1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("⏭", callback_data=f"banpage_{total_pages-1}"))
    
    markup.add(*nav_buttons)
    
    row2 = []
    if total_pages > 5:
        row2.append(types.InlineKeyboardButton("🔍 К странице", callback_data="banpage_goto"))
    row2.append(types.InlineKeyboardButton("📋 Компактный список", callback_data="banlist_all"))
    markup.add(*row2)
    
    markup.add(types.InlineKeyboardButton("🔎 Поиск по ID", callback_data="banpage_byid"))
    
    if reply_to:
        bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup, reply_to_message_id=reply_to)
    else:
        bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(commands=['banlist'])
def banlist(message):
    if message.chat.id != CHAT_ID:
        return
    
    bans = get_all_bans()
    
    if not bans:
        bot.reply_to(message, "📋 <b>Нет забаненных пользователей</b>", parse_mode='HTML')
        return
    
    show_banlist_page(message.chat.id, 0, message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('banpage_'))
def handle_banpage(call):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔ Нет прав", show_alert=True)
        return
    
    action = call.data.replace('banpage_', '')
    
    if action == 'info':
        bot.answer_callback_query(call.id, "Текущая страница", show_alert=False)
        return
    
    if action == 'goto':
        msg = bot.send_message(
            call.message.chat.id,
            "🔍 <b>Введите номер страницы:</b>\n\n"
            "Отправьте команду:\n"
            "<code>/banpage 3</code>",
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if action == 'byid':
        msg = bot.send_message(
            call.message.chat.id,
            "🔎 <b>Введите ID пользователя для просмотра бана:</b>\n\n"
            "Отправьте команду:\n"
            "<code>/baninfo 123456789</code>",
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    try:
        page = int(action)
        show_banlist_page(call.message.chat.id, page)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
    except ValueError:
        bot.answer_callback_query(call.id, "❌ Ошибка навигации", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('baninfo_'))
def baninfo(call):
    user_id = int(call.data.split('_')[1])
    ban_info = get_ban_info(user_id)
    
    if not ban_info:
        bot.answer_callback_query(call.id, "Пользователь больше не в бане")
        return
    
    user_name, username, reason, banned_by_name, banned_at = ban_info
    
    text = f"<b>👤 ИНФОРМАЦИЯ О БАНЕ</b>\n\n"
    text += f"<b>Пользователь:</b> {user_name}\n"
    text += f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
    if username:
        text += f"<b>📢 Username:</b> @{username}\n"
    text += f"<b>📝 Причина:</b> {reason}\n"
    text += f"<b>👮 Забанил:</b> {banned_by_name}\n"
    text += f"<b>⏰ Дата:</b> {banned_at}\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔓 Разбанить", callback_data=f"unban_{user_id}"))
    markup.add(types.InlineKeyboardButton("📋 К банлисту", callback_data="banpage_0"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('unban_'))
def unban_from_button(call):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔ У вас нет прав", show_alert=True)
        return
    
    user_id = int(call.data.split('_')[1])
    ban_info = get_ban_info(user_id)
    
    if remove_ban(user_id):
        bot.answer_callback_query(call.id, "✅ Пользователь разбанен")
        bot.edit_message_text(
            f"✅ <b>Пользователь разбанен</b>\n\n👤 {ban_info[0] if ban_info else 'Пользователь'}\n🆔 ID: <code>{user_id}</code>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        try:
            bot.send_message(user_id, "✅ <b>ʙы быᴧи ᴩᴀзбᴀнᴇны</b>\n\nᴛᴇᴨᴇᴩь ʙы ᴄноʙᴀ ʍожᴇᴛᴇ оᴛᴨᴩᴀʙᴧяᴛь ᴄообщᴇния ᴀдʍиниᴄᴛᴩᴀᴛоᴩᴀʍ.", parse_mode='HTML')
        except:
            pass
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка при разбане")

@bot.callback_query_handler(func=lambda call: call.data == "banlist_all")
def banlist_all_compact(call):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔ Нет прав", show_alert=True)
        return
    
    bans = get_all_bans()
    
    if not bans:
        bot.edit_message_text("📋 Нет забаненных пользователей", call.message.chat.id, call.message.message_id)
        return
    
    text = f"<b>📋 ВСЕ ЗАБАНЕННЫЕ ({len(bans)})</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "<code>"
    
    for ban in bans:
        user_id, user_name, username, reason, banned_by, banned_at = ban
        text += f"{user_id:12} | {user_name[:20]:20} | {reason[:30]}\n"
        
        if len(text) > 3800:
            text += "...</code>\n\n<i>(список обрезан из-за ограничений Telegram)</i>"
            break
    else:
        text += "</code>"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад к страницам", callback_data="banpage_0"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['banpage'])
def banpage_command(message):
    if message.chat.id != CHAT_ID:
        return
    
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔ У вас нет прав")
        return
    
    parts = message.text.split()
    
    if len(parts) < 2:
        bans = get_all_bans()
        total_pages = (len(bans) + BANS_PER_PAGE - 1) // BANS_PER_PAGE if bans else 1
        bot.reply_to(
            message,
            f"📋 <b>Использование:</b>\n"
            f"<code>/banpage &lt;номер&gt;</code>\n\n"
            f"Всего страниц: {total_pages}\n"
            f"Текущая страница: {banlist_current_page.get(message.chat.id, 0) + 1}",
            parse_mode='HTML'
        )
        return
    
    try:
        page_num = int(parts[1]) - 1
        
        bans = get_all_bans()
        total_pages = (len(bans) + BANS_PER_PAGE - 1) // BANS_PER_PAGE if bans else 1
        
        if page_num < 0 or page_num >= total_pages:
            bot.reply_to(
                message,
                f"❌ Неверный номер страницы.\n"
                f"Доступны страницы: 1 - {total_pages}",
                parse_mode='HTML'
            )
            return
        
        show_banlist_page(message.chat.id, page_num, message.message_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Введите число. Пример: <code>/banpage 3</code>", parse_mode='HTML')

@bot.message_handler(commands=['baninfo'])
def baninfo_command(message):
    if message.chat.id != CHAT_ID:
        return
    
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔ У вас нет прав")
        return
    
    parts = message.text.split()
    
    if len(parts) < 2:
        bot.reply_to(
            message,
            "📋 <b>Использование:</b>\n"
            "<code>/baninfo &lt;user_id&gt;</code>\n\n"
            "Пример: <code>/baninfo 123456789</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(parts[1])
        ban_info = get_ban_info(user_id)
        
        if not ban_info:
            bot.reply_to(message, f"❌ Пользователь {user_id} не найден в банлисте", parse_mode='HTML')
            return
        
        user_name, username, reason, banned_by_name, banned_at = ban_info
        
        text = f"<b>🔍 ИНФОРМАЦИЯ О БАНЕ</b>\n\n"
        text += f"<b>👤 Пользователь:</b> {user_name}\n"
        text += f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
        if username:
            text += f"<b>📢 Username:</b> @{username}\n"
        text += f"<b>📝 Причина:</b> {reason}\n"
        text += f"<b>👮 Забанил:</b> {banned_by_name}\n"
        text += f"<b>⏰ Дата:</b> {banned_at}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔓 Разбанить", callback_data=f"unban_{user_id}"))
        markup.add(types.InlineKeyboardButton("📋 К банлисту", callback_data="banpage_0"))
        
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=markup)
        
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID. Введите число.", parse_mode='HTML')

# ========== КОМАНДА /INFO ==========
@bot.message_handler(commands=['info'])
def info(message):
    if message.chat.type == 'private':
        bot.reply_to(message, f"🆔 Ваш ID: {message.from_user.id}")
    else:
        bot.reply_to(message, f"🆔 ID этого чата: {message.chat.id}")

# ========== КОМАНДА /MEMORY ==========
@bot.message_handler(commands=['memory'])
def memory_info(message):
    if message.chat.id != CHAT_ID or message.from_user.id not in ADMINS:
        return
    
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    
    db_exists = os.path.exists(DB_PATH)
    db_size = os.path.getsize(DB_PATH) if db_exists else 0
    
    text = f"📊 <b>Память бота</b>\n"
    text += f"RSS: {mem_info.rss / 1024 / 1024:.1f} MB\n"
    text += f"Кэш сообщений: {len(message_to_user)}\n"
    text += f"Ожидание режима: {len(user_pending_content)}\n"
    text += f"Сбор альбомов: {len(album_collector)}\n"
    text += f"БД bans.db: {db_size / 1024:.1f} KB ({'✅' if db_exists else '❌'})"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🧹 Очистить память", callback_data="clear_memory"))
    
    bot.reply_to(message, text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "clear_memory")
def clear_memory_callback(call):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔ Нет прав")
        return
    
    before_message = len(message_to_user)
    before_pending = len(user_pending_content)
    before_album = len(album_collector)
    
    message_to_user.clear()
    user_pending_content.clear()
    
    with album_lock:
        for collector in album_collector.values():
            if collector.get('timer'):
                collector['timer'].cancel()
        album_collector.clear()
    
    for thread_id, conn in list(db_connections.items()):
        try:
            conn.close()
        except:
            pass
    db_connections.clear()
    
    gc.collect()
    
    bot.answer_callback_query(call.id, "✅ Память очищена")
    bot.edit_message_text(
        call.message.text + f"\n\n✅ <b>Память очищена!</b>\n• Кэш сообщений: {before_message} → 0\n• Ожидание: {before_pending} → 0\n• Альбомы: {before_album} → 0",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )

# ========== БЛОКИРОВКА НЕИЗВЕСТНЫХ КОМАНД В АДМИН-ЧАТЕ ==========
@bot.message_handler(func=lambda m: m.chat.id == CHAT_ID and m.text and m.text.startswith('/'))
def block_unknown_commands(message):
    """Блокирует неизвестные команды в админ-чате"""
    
    known_commands = [
        '/start', '/info',
        '/ban', '/unban', '/banlist', '/banpage', '/baninfo', '/clearbans',
        '/memory'
    ]
    
    command = message.text.split()[0].lower()
    if '@' in command:
        command = command.split('@')[0]
    
    if command not in known_commands:
        bot.reply_to(
            message,
            f"❌ <b>Неизвестная команда:</b> <code>{command}</code>\n\n"
            f"<b>Доступные команды:</b>\n"
            f"• /ban — забанить\n"
            f"• /unban — разбанить\n"
            f"• /banlist — список банов\n"
            f"• /banpage 3 — страница банлиста\n"
            f"• /baninfo ID — инфо о бане\n"
            f"• /clearbans — очистить банлист\n"
            f"• /memory — память бота\n"
            f"• /info — ID чата",
            parse_mode='HTML'
        )
        return

# ========== ОТВЕТ АДМИНИСТРАТОРА ==========
@bot.message_handler(func=lambda m: m.chat.id == CHAT_ID and m.reply_to_message)
def reply_to_user_by_quoting(message):
    try:
        original_msg_id = message.reply_to_message.message_id
        
        if original_msg_id in message_to_user:
            user_id = message_to_user[original_msg_id]
            
            bot.send_message(
                user_id,
                f"✉️ <b>оᴛʙᴇᴛ оᴛ ᴀдʍиниᴄᴛᴩᴀᴛоᴩᴀ:</b>\n\n{message.text}",
                parse_mode='HTML'
            )
            bot.reply_to(message, f"✅ Ответ отправлен пользователю")
        else:
            text = message.reply_to_message.text or message.reply_to_message.caption or ""
            match = re.search(r"🆔 ID: (?:<code>)?(\d+)(?:</code>)?", text)
            if match:
                user_id = int(match.group(1))
                bot.send_message(
                    user_id,
                    f"✉️ <b>Ответ администратора:</b>\n\n{message.text}",
                    parse_mode='HTML'
                )
                bot.reply_to(message, f"✅ Ответ отправлен пользователю")
            else:
                bot.reply_to(message, "❌ Не удалось найти ID пользователя")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("✅ Бот запущен!")
    print(f"📢 Чат админов: {CHAT_ID}")
    print(f"💾 База данных: {DB_PATH}")
    bot.remove_webhook()
    bot.infinity_polling()
