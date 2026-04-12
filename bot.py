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

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте переменную окружения BOT_TOKEN")

CHAT_ID = -1003723055728  # ID чата админов (без #, просто число)

bot = telebot.TeleBot(BOT_TOKEN)

# ID администраторов
ADMINS = [6206017016, 1176412025]

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
message_to_user = {}  # {message_id: user_id}
user_choice = {}      # {user_id: mode}
user_last_text = {}   # {user_id: {'text': str, 'mode': str, 'user_name': str, 'username': str}}
user_media_temp = {}  # {user_id: [list of messages]}
user_media_timer = {} # {user_id: timer}
user_text_timer = {}  # {user_id: timer}

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('bans.db', check_same_thread=False)
cursor = conn.cursor()
db_lock = threading.Lock()  # Блокировка для безопасной работы с БД

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

def add_ban(user_id, user_name, username, reason, banned_by, banned_by_name):
    with db_lock:
        cursor.execute('''
            INSERT OR REPLACE INTO bans 
            (user_id, user_name, username, reason, banned_by, banned_by_name, banned_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, username, reason, banned_by, banned_by_name, datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()

def remove_ban(user_id):
    with db_lock:
        cursor.execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def is_banned(user_id):
    cursor.execute('SELECT 1 FROM bans WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

def get_ban_info(user_id):
    cursor.execute('SELECT user_name, username, reason, banned_by_name, banned_at FROM bans WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def get_all_bans():
    cursor.execute('SELECT user_id, user_name, username, reason, banned_by_name, banned_at FROM bans ORDER BY banned_at DESC')
    return cursor.fetchall()

# ========== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ USER_ID ИЗ СООБЩЕНИЯ ==========
def get_user_id_from_message(msg):
    """Пытается найти user_id в сообщении (поддерживает анонимные сообщения)"""
    if msg.message_id in message_to_user:
        return message_to_user[msg.message_id]
    
    if msg.text or msg.caption:
        text = msg.text or msg.caption
        # ИСПРАВЛЕНО: поддержка HTML-тега <code>
        match = re.search(r"🆔 ID: (?:<code>)?(\d+)(?:</code>)?", text)
        if match:
            return int(match.group(1))
    return None

# ========== КОМАНДА /START ==========
START_PHOTO_URL = "https://i.postimg.cc/BQJ8bXP1/photo-2026-04-09-18-55-14.jpg"  # ваша прямая ссылка

@bot.message_handler(commands=['start'])
def start(message):
    hello_text = """
﹌﹌﹌﹌ . . '''ᅠ ᅠ♱  ᅠ   𝅄  ﹌﹌﹌  . 𓏲

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

    # Отправляем фото по прямой ссылке
    try:
        bot.send_photo(
            message.chat.id, 
            START_PHOTO_URL,
            caption=hello_text, 
            reply_markup=markup, 
            parse_mode='HTML'
        )
    except Exception as e:
        # Если фото не загрузилось, отправляем только текст
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

def ask_send_mode(user_id):
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
    
    # Проверка на бан
    if is_banned(user_id):
        ban_info = get_ban_info(user_id)
        reason = ban_info[2] if ban_info else "не указана"
        bot.reply_to(message, f"🚫 ʙы зᴀбᴀнᴇны...", parse_mode='HTML')
        return
    
    # Проверяем, выбрал ли пользователь режим
    if user_id not in user_choice:
        ask_send_mode(user_id)
        return
    
    # Сохраняем текст для возможного альбома
    user_last_text[user_id] = {
        'text': message.text,
        'mode': user_choice[user_id],
        'user_name': message.from_user.first_name,
        'username': message.from_user.username
    }
    
    # Убираем выбор режима
    del user_choice[user_id]
    
    # Устанавливаем таймер (5 секунд)
    timer = threading.Timer(5.0, send_text_if_no_media, args=[user_id])
    user_text_timer[user_id] = timer
    timer.start()

def send_text_if_no_media(user_id):
    # Очищаем таймер
    if user_id in user_text_timer:
        del user_text_timer[user_id]
    
    if user_id not in user_last_text:
        return
    
    data = user_last_text[user_id]
    del user_last_text[user_id]
    
    mode = data['mode']
    user_name = data['user_name']
    username = data['username']
    
    # Создаём кнопку профиля
    markup = None
    if mode == 'public' and username:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 Профиль", url=f"https://t.me/{username}"))
    
    # Формируем текст отправителя
    if mode == 'public':
        sender_text = f"📩 <b>Отправитель:</b> {user_name}\n🆔 ID: {user_id}"
    else:
        sender_text = "👤 <b>Отправитель:</b> Аноним\n🆔 ID: скрыт"
    
    # Отправляем текст в чат админов
    sent_msg = bot.send_message(
        CHAT_ID,
        f"{sender_text}\n📝 <b>Сообщение:</b>\n{data['text']}",
        parse_mode='HTML',
        reply_markup=markup
    )
    
    if sent_msg:
        message_to_user[sent_msg.message_id] = user_id
    
    # Подтверждение пользователю
    try:
        mode_text = "ᴨубᴧично" if mode == 'public' else "ᴀнониʍно"
        bot.send_message(
            user_id,
            f"⤿ ᴄообщᴇниᴇ оᴛᴨᴩᴀʙᴧᴇно {mode_text}!\n\nᴋоᴦдᴀ ᴀдʍиниᴄᴛᴩᴀᴛоᴩ оᴛʙᴇᴛиᴛ, ʙы ᴨоᴧучиᴛᴇ уʙᴇдоʍᴧᴇниᴇ."
        )
    except Exception as e:
        print(f"Ошибка отправки подтверждения: {e}")

# ========== ОБРАБОТКА МЕДИА ==========
@bot.message_handler(content_types=['photo', 'video', 'audio', 'document', 'voice', 'sticker'], func=lambda message: message.chat.type == 'private')
def handle_media(message):
    user_id = message.from_user.id
    
    # Отменяем таймер текста
    if user_id in user_text_timer:
        user_text_timer[user_id].cancel()
        del user_text_timer[user_id]
    
    if is_banned(user_id):
        ban_info = get_ban_info(user_id)
        reason = ban_info[2] if ban_info else "не указана"
        bot.reply_to(message, f"🚫 Вы забанены...", parse_mode='HTML')
        return
    
    if user_id not in user_choice and user_id not in user_last_text:
        ask_send_mode(user_id)
        return
    
    # Сбрасываем старый таймер медиа
    if user_id in user_media_timer:
        user_media_timer[user_id].cancel()
    
    # Добавляем медиа в хранилище
    if user_id not in user_media_temp:
        user_media_temp[user_id] = []
    user_media_temp[user_id].append(message)
    
    # Устанавливаем новый таймер на 1.5 секунды
    timer = threading.Timer(1.5, process_collected_media, args=[user_id])
    user_media_timer[user_id] = timer
    timer.start()

def process_collected_media(user_id):
    if user_id not in user_media_temp:
        return
    
    messages = user_media_temp[user_id]
    del user_media_temp[user_id]
    if user_id in user_media_timer:
        del user_media_timer[user_id]
    
    if len(messages) == 1:
        process_single_media(messages[0], user_id)
    else:
        process_multiple_as_album(messages, user_id)

def process_multiple_as_album(messages, user_id):
    """Обрабатывает несколько медиа как альбом"""
    if user_id in user_choice:
        mode = user_choice[user_id]
        del user_choice[user_id]
    elif user_id in user_last_text:
        mode = user_last_text[user_id]['mode']
    else:
        mode = 'public'
    
    user_name = messages[0].from_user.first_name
    username = messages[0].from_user.username
    
    # Получаем сохранённый текст (подпись)
    caption_text = ""
    if user_id in user_last_text:
        caption_text = user_last_text[user_id]['text']
        if 'user_name' in user_last_text[user_id]:
            user_name = user_last_text[user_id]['user_name']
        if 'username' in user_last_text[user_id]:
            username = user_last_text[user_id]['username']
        del user_last_text[user_id]
    
    # Создаём кнопку профиля
    markup = None
    if mode == 'public' and username:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 Профиль", url=f"https://t.me/{username}"))
    
    if mode == 'public':
        sender_text = f"📩 <b>Отправитель:</b> {user_name}\n🆔 ID: {user_id}"
    else:
        sender_text = "👤 <b>Отправитель:</b> Аноним\n🆔 ID: скрыт"
    
    # Формируем информационный текст
    info_text = f"{sender_text}\n📎 <b>Альбом ({len(messages)} файлов)</b>"
    if caption_text:
        info_text += f"\n\n📝 <b>Текст:</b> {caption_text}"
    
    # Собираем медиагруппу
    media_group = []
    for msg in messages:
        if msg.photo:
            media_group.append(types.InputMediaPhoto(msg.photo[-1].file_id))
        elif msg.video:
            media_group.append(types.InputMediaVideo(msg.video.file_id))
        elif msg.audio:
            media_group.append(types.InputMediaAudio(msg.audio.file_id))
        elif msg.document:
            media_group.append(types.InputMediaDocument(msg.document.file_id))
    
    if media_group:
        try:
            # Отправляем альбом
            sent_messages = bot.send_media_group(CHAT_ID, media_group)
            
            # Запоминаем все сообщения из альбома
            for msg in sent_messages:
                message_to_user[msg.message_id] = user_id
            
            # Отправляем информационное сообщение
            info_msg = bot.send_message(CHAT_ID, info_text, parse_mode='HTML', reply_markup=markup)
            if info_msg:
                message_to_user[info_msg.message_id] = user_id
                
        except Exception as e:
            print(f"Ошибка отправки альбома: {e}")
            # Если не удалось отправить альбомом, отправляем по одному
            for msg in messages:
                process_single_media(msg, user_id)
    
    # Подтверждение пользователю
    try:
        mode_text = "ᴨубᴧично" if mode == 'public' else "ᴀнониʍно"
        bot.send_message(
            user_id, 
            f"⤿ Альбом из {len(media_group)} файлов отправлен {mode_text}!\n\nКогда администратор ответит, вы получите уведомление."
        )
    except Exception as e:
        print(f"Ошибка отправки подтверждения: {e}")

def process_single_media(message, user_id):
    """Обрабатывает одиночное медиа (не из альбома)"""
    # Берём режим
    if user_id in user_choice:
        mode = user_choice[user_id]
        del user_choice[user_id]
    elif user_id in user_last_text:
        mode = user_last_text[user_id]['mode']
    else:
        mode = 'public'
    
    user_name = message.from_user.first_name
    username = message.from_user.username
    
    # Получаем сохранённый текст
    caption_text = ""
    if user_id in user_last_text:
        caption_text = user_last_text[user_id]['text']
        if 'user_name' in user_last_text[user_id]:
            user_name = user_last_text[user_id]['user_name']
        if 'username' in user_last_text[user_id]:
            username = user_last_text[user_id]['username']
        del user_last_text[user_id]
    
    # Создаём кнопку профиля
    markup = None
    if mode == 'public' and username:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 Профиль", url=f"https://t.me/{username}"))
    
    # Формируем текст отправителя
    if mode == 'public':
        sender_text = f"📩 <b>Отправитель:</b> {user_name}\n🆔 ID: {user_id}"
    else:
        sender_text = "👤 <b>Отправитель:</b> Аноним\n🆔 ID: скрыт"
    
    # Определяем тип медиа
    media_type = ""
    if message.photo:
        media_type = "Фото"
    elif message.video:
        media_type = "Видео"
    elif message.audio:
        media_type = "Аудио"
    elif message.document:
        media_type = f"Документ: {message.document.file_name}" if message.document.file_name else "Документ"
    elif message.voice:
        media_type = "Голосовое"
    elif message.sticker:
        media_type = "Стикер"
    
    full_caption = f"{sender_text}\n📎 <b>{media_type}</b>"
    if caption_text:
        full_caption += f"\n\n📝 <b>Текст:</b> {caption_text}"
    
    sent_msg = None
    
    # Отправляем в зависимости от типа
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
    
    # Запоминаем связку для ответа
    if sent_msg:
        message_to_user[sent_msg.message_id] = user_id
    
    # Подтверждение пользователю
    try:
        mode_text = "ᴨубᴧично" if mode == 'public' else "ᴀнониʍно"
        bot.send_message(
            user_id, 
            f"⤿ ᴄообщᴇниᴇ оᴛᴨᴩᴀʙᴧᴇно {mode_text}!\n\nᴋоᴦдᴀ ᴀдʍиниᴄᴛᴩᴀᴛоᴩ оᴛʙᴇᴛиᴛ, ʙы ᴨоᴧучиᴛᴇ уʙᴇдоʍᴧᴇниᴇ."
        )
    except Exception as e:
        print(f"Ошибка отправки подтверждения пользователю {user_id}: {e}")

# ========== ОБРАБОТЧИК ВЫБОРА РЕЖИМА ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def handle_mode_choice(call):
    parts = call.data.split('_')
    mode = parts[1]
    user_id = int(parts[2])
    
    if mode == 'cancel':
        bot.edit_message_text(
            "ᴛᴇᴨᴇᴩь ʙы ᴄнᴏʙᴀ ʍᴏжᴇᴛᴇ ᴏᴛᴨᴩᴀʙᴧяᴛь ᴄᴏᴏбщᴇния.\n\n❌ ᴏᴛᴨᴩᴀʙᴋᴀ ᴄᴏᴏбщᴇния ᴏᴛʍᴇнᴇнᴀ.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    
    user_choice[user_id] = mode
    
    bot.edit_message_text(
        f"╋ ━ ᴩᴇжиʍ <b>{'ᴨубᴧичной' if mode == 'public' else 'ᴀнониʍной'}</b> оᴛᴨᴩᴀʙᴋи ʙыбᴩᴀн.\n\n𓂃🖊 ᴛᴇᴨᴇᴩь нᴀᴨиɯиᴛᴇ ʙᴀɯᴇ ᴄообщᴇниᴇ:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

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

# ========== КОМАНДА /BANLIST ==========
@bot.message_handler(commands=['banlist'])
def banlist(message):
    if message.chat.id != CHAT_ID:
        return
    
    bans = get_all_bans()
    
    if not bans:
        bot.reply_to(message, "📋 <b>Нет забаненных пользователей</b>", parse_mode='HTML')
        return
    
    markup = types.InlineKeyboardMarkup()
    for ban in bans[:10]:
        user_id, user_name, username, reason, banned_by, banned_at = ban
        markup.add(types.InlineKeyboardButton(f"👤 {user_name[:20]}", callback_data=f"baninfo_{user_id}"))
    
    if len(bans) > 10:
        markup.add(types.InlineKeyboardButton("📄 Показать всех", callback_data="banlist_all"))
    
    bot.reply_to(message, 
        f"📋 <b>Забаненные пользователи</b>\n\nВсего: {len(bans)}\nНажмите на имя для подробной информации",
        parse_mode='HTML',
        reply_markup=markup)

# ========== КОМАНДА /INFO ==========
@bot.message_handler(commands=['info'])
def info(message):
    if message.chat.type == 'private':
        bot.reply_to(message, f"🆔 Ваш ID: {message.from_user.id}")
    else:
        bot.reply_to(message, f"🆔 ID этого чата: {message.chat.id}")

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
            # ИСПРАВЛЕНО: поддержка HTML-тега <code>
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

# ========== ОБРАБОТЧИКИ ДЛЯ КНОПОК БАНЛИСТА ==========
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
def banlist_all(call):
    # Проверка прав
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔ Нет прав", show_alert=True)
        return
    
    bans = get_all_bans()
    
    if not bans:
        bot.edit_message_text("📋 Нет забаненных пользователей", call.message.chat.id, call.message.message_id)
        return
    
    text = "<b>📋 ПОЛНЫЙ СПИСОК ЗАБАНЕННЫХ</b>\n\n"
    for ban in bans:
        user_id, user_name, username, reason, banned_by, banned_at = ban
        text += f"👤 <b>{user_name}</b>\n"
        text += f"🆔 ID: {user_id}\n"
        if username:
            text += f"📢 @{username}\n"
        text += f"📝 {reason[:50]}\n"
        text += f"⏰ {banned_at}\n"
        text += f"━━━━━━━━━━━━━━━\n"
        
        if len(text) > 3500:
            text += "\n... и другие"
            break
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

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
    bot.remove_webhook()
    bot.infinity_polling()
