import asyncio
import sqlite3
import yaml
from time import time
from datetime import datetime
from collections import defaultdict
from config import API_TOKEN, CHANNEL_ID, OWNER_ID, MEDIA_TIMEOUT
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo
)

from aiogram.client.default import DefaultBotProperties

from asyncio import create_task, sleep

from db import (
    is_blocked, block_user, unblock_user,
    get_blocked_users, save_idea, get_latest_ideas
)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# === State ===
ideas_cache = {}
user_last_media = defaultdict(dict)
media_groups = defaultdict(list)
media_group_tasks = {}

# === Helpers ===
async def send_to_channel(content_type, file_id, text, mention=None):
    caption = f"Сообщение от {mention or 'Анонимно'}:\n{text}"
    send_map = {
        "text": bot.send_message,
        "photo": bot.send_photo,
        "video": bot.send_video,
        "audio": bot.send_audio,
        "voice": bot.send_voice,
        "document": bot.send_document,
        "animation": bot.send_animation
    }

    if content_type == "text":
        await bot.send_message(CHANNEL_ID, caption)
    elif content_type in send_map:
        await send_map[content_type](CHANNEL_ID, file_id, caption=caption if file_id else None)
    else:
        await bot.send_message(CHANNEL_ID, caption)


async def process_submission(message, user_id, username, text, content_type, file_id):
    msg_id = message.message_id
    ideas_cache[msg_id] = {
        "user_id": user_id, "username": username, "text": text,
        "content_type": content_type, "file_id": file_id
    }
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{msg_id}")],
        [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{msg_id}")],
        [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{msg_id}")],
        [InlineKeyboardButton(text="👤 Анонимно в канал", callback_data=f"anonymous:{msg_id}")]
    ])
    mention = f"<b>Сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"

    if content_type == "text" or not file_id:
        await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
    elif content_type == "album":
        await bot.send_media_group(OWNER_ID, media=file_id)
        await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
    else:
        send_map = {
            "photo": bot.send_photo, "video": bot.send_video,
            "audio": bot.send_audio, "voice": bot.send_voice,
            "document": bot.send_document, "animation": bot.send_animation
        }
        await send_map.get(content_type, bot.send_message)(OWNER_ID, file_id, caption=mention, reply_markup=keyboard)

    await message.reply("Спасибо! Сообщение отправлено на модерацию.")

async def handle_album_later(message, group_id, user_id, username):
    await sleep(2)
    media_list = media_groups.pop(group_id, [])
    media_group_tasks.pop(group_id, None)
    if not media_list:
        return

    caption = media_list[0].get("caption") or ""
    input_media = [
        InputMediaPhoto(media=m["file_id"], caption=caption if i == 0 else None, parse_mode="HTML")
        if m["type"] == "photo"
        else InputMediaVideo(media=m["file_id"], caption=caption if i == 0 else None, parse_mode="HTML")
        for i, m in enumerate(media_list)
    ]
    message_id = message.message_id
    ideas_cache[message_id] = {
        "user_id": user_id, "username": username,
        "text": caption, "content_type": "album", "file_id": input_media
    }
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{message_id}")],
        [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{message_id}")],
        [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{message_id}")],
        [InlineKeyboardButton(text="👤 Анонимно в канал", callback_data=f"anonymous:{message_id}")]
    ])
    await bot.send_media_group(OWNER_ID, media=input_media)
    await bot.send_message(OWNER_ID, f"<b>Альбом от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{caption}", reply_markup=keyboard)
    await message.reply("Спасибо! Альбом отправлен на модерацию.")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = ("Привет! Сюда ты можешь кидать всякий шлак и возможно сам Wobir его запостит в свой тгк\n"
        "Привет! Отправляй текст или медиа в бот — они попадут на модерацию.\n"
        "Чтобы отправить анонимно, используй команду /anon + сообщение или медиа.\n"
        "Владелец решит, публиковать ли твоё сообщение."
        "Пожалуйста, не нарушай правила и уважай других."
    )
    await message.reply(text)
    
@dp.message(Command("anon"))
async def cmd_anon(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    now = time()

    if is_blocked(user_id):
        await message.reply("Вы заблокированы.")
        return

    text = (message.caption or message.text or "").strip()
    ctype = message.content_type

    file_id = None
    extractors = {
        "photo": lambda m: m.photo[-1].file_id,
        "video": lambda m: m.video.file_id,
        "audio": lambda m: m.audio.file_id,
        "voice": lambda m: m.voice.file_id,
        "document": lambda m: m.document.file_id,
        "animation": lambda m: m.animation.file_id
    }

    if ctype in extractors:
        file_id = extractors[ctype](message)
        # Сохраняем в кеш с флагом анонимности
        msg_id = message.message_id
        ideas_cache[msg_id] = {
            "user_id": user_id,
            "username": username,
            "text": text,
            "content_type": ctype,
            "file_id": file_id,
            "anonymous": True
        }
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{msg_id}")],
            [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{msg_id}")],
            [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{msg_id}")]
        ])

        mention = f"<b>Анонимное сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"
        await bot.send_photo(OWNER_ID, file_id, caption=mention, reply_markup=keyboard)
        await message.reply("Спасибо! Ваше анонимное сообщение отправлено на модерацию.")
        return

    if ctype == "text":
        msg_id = message.message_id
        ideas_cache[msg_id] = {
            "user_id": user_id,
            "username": username,
            "text": text,
            "content_type": "text",
            "file_id": None,
            "anonymous": True
        }
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{msg_id}")],
            [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{msg_id}")],
            [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{msg_id}")]
        ])

        mention = f"<b>Анонимное сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"
        await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
        await message.reply("Спасибо! Ваше анонимное сообщение отправлено на модерацию.")
        return

    await message.reply("Пожалуйста, отправьте текст или медиа вместе с командой /anon для анонимной отправки.")

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    if message.chat.type != "private":
        return await message.reply("Команда работает только в личке.")

    await message.reply("Начинаю очистку чата...")
    for msg_id in range(message.message_id, message.message_id - 100, -1):
        try:
            await bot.delete_message(message.chat.id, msg_id)
            await asyncio.sleep(0.05)  # небольшой интервал, чтобы избежать flood
        except:
            continue

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        block_user(int(message.text.split()[1]))
        await message.reply("Пользователь заблокирован.")
    except:
        await message.reply("Используй: /ban <user_id>")
        
@dp.message(Command("ideas"))
async def cmd_ideas(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    rows = get_latest_ideas()
    if not rows:
        await message.reply("В базе идей пока пусто.")
        return

    text = "<b>Последние сохранённые идеи:</b>\n\n"
    for id_, user_id, username, msg, ts in rows:
        uname = username or "без ника"
        snippet = (msg[:50] + "...") if len(msg) > 50 else msg
        text += f"#{id_} [{uname}](tg://user?id={user_id}) ({ts}):\n{snippet}\n\n"

    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
    
@dp.message(Command("banned"))
async def cmd_banned(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    rows = get_blocked_users()
    if not rows:
        await message.reply("Список заблокированных пользователей пуст.")
        return

    text = "<b>Заблокированные пользователи:</b>\n\n"
    for (user_id,) in rows:
        text += f"- <a href='tg://user?id={user_id}'>{user_id}</a>\n"

    await message.reply(text, parse_mode="HTML")
    
@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        unblock_user(int(message.text.split()[1]))
        await message.reply("Пользователь разблокирован.")
    except:
        await message.reply("Используй: /unban <user_id>")

@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    now = time()
    text = (message.caption or message.text or "").strip()
    ctype = message.content_type

    if is_blocked(user_id):
        await message.reply("Вы заблокированы.")
        return

    if message.media_group_id:
        gid = message.media_group_id
        media_entry = {"file_id": None, "type": ctype, "caption": text if not media_groups[gid] else None}
        if ctype == "photo":
            media_entry["file_id"] = message.photo[-1].file_id
        elif ctype == "video":
            media_entry["file_id"] = message.video.file_id
        else:
            return await message.reply("Поддерживаются только фото и видео в альбомах.")

        media_groups[gid].append(media_entry)
        if gid not in media_group_tasks:
            media_group_tasks[gid] = create_task(handle_album_later(message, gid, user_id, username))
        return

    file_id = None
    extractors = {
        "photo": lambda m: m.photo[-1].file_id,
        "video": lambda m: m.video.file_id,
        "audio": lambda m: m.audio.file_id,
        "voice": lambda m: m.voice.file_id,
        "document": lambda m: m.document.file_id,
        "animation": lambda m: m.animation.file_id
    }

    if ctype in extractors:
        file_id = extractors[ctype](message)
        user_last_media[user_id] = {"file_id": file_id, "type": ctype, "time": now, "text": text}
        if text:
            await process_submission(message, user_id, username, text, ctype, file_id)
            user_last_media.pop(user_id, None)
        else:
            await message.reply("Теперь отправь подпись или текст к медиа.")
        return

    if ctype == "text":
        last = user_last_media.get(user_id)
        if last and now - last["time"] < MEDIA_TIMEOUT:
            await process_submission(message, user_id, username, text, last["type"], last["file_id"])
            user_last_media.pop(user_id, None)
        else:
            await process_submission(message, user_id, username, text, "text", None)
        return

    await message.reply("Пожалуйста, отправьте текст или медиа.")

@dp.callback_query()
async def callback(callback_query: CallbackQuery):
    if callback_query.from_user.id != OWNER_ID:
        return await callback_query.answer("Нет доступа", show_alert=True)

    try:
        action, msg_id = callback_query.data.split(":")
        msg_id = int(msg_id)
        data = ideas_cache[msg_id]
    except:
        return await callback_query.answer("Ошибка или устаревшие данные", show_alert=True)

    uid = data["user_id"]
    uname = data["username"]
    text = data["text"]
    ctype = data["content_type"]
    file_id = data["file_id"]
    anonymous = data.get("anonymous", False)

    mention = f"<a href='tg://user?id={uid}'>@{uname or 'пользователь'}</a>"

    if action == "approve":
        if anonymous:
            anon_caption = f"Сообщение от Анонимно:\n{text}"
            if ctype == "album":
                await bot.send_media_group(CHANNEL_ID, media=file_id)
                await bot.send_message(CHANNEL_ID, anon_caption)
            elif ctype == "text":
                await bot.send_message(CHANNEL_ID, anon_caption)
            else:
                send_map = {
                    "photo": bot.send_photo, "video": bot.send_video,
                    "audio": bot.send_audio, "voice": bot.send_voice,
                    "document": bot.send_document, "animation": bot.send_animation
                }
                await send_map.get(ctype, bot.send_message)(CHANNEL_ID, file_id, caption=anon_caption if file_id else None)
        else:
            if ctype == "album":
                await bot.send_media_group(CHANNEL_ID, media=file_id)
                await bot.send_message(CHANNEL_ID, f"Сообщение от {mention}:\n{text}")
            else:
                await send_to_channel(ctype, file_id, text, mention)
        await callback_query.message.edit_reply_markup()
        return await callback_query.answer("Опубликовано ✅")

    elif action == "idea":
        save_idea(uid, uname, text, datetime.now().isoformat())
        await callback_query.message.edit_reply_markup()
        return await callback_query.answer("Сохранено в базу 💡")


    elif action == "reject":
        await callback_query.message.edit_reply_markup()
        return await callback_query.answer("Отклонено 🚫")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
