import logging
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from db import db
from config import OWNER_ID

logger = logging.getLogger(__name__)

def register_admin_handlers(dp: Dispatcher, bot):
    @dp.message(Command("ban"))
    async def cmd_ban(message: Message):
        try:
            if message.from_user.id != OWNER_ID:
                return
            
            try:
                user_id = int(message.text.split()[1])
                if db.block_user(user_id):
                    await message.reply("Пользователь заблокирован.")
                else:
                    await message.reply("Ошибка блокировки пользователя.")
            except (IndexError, ValueError):
                await message.reply("Используй: /ban <user_id>")
            except Exception as e:
                logger.error(f"Ошибка блокировки: {e}")
                await message.reply("Ошибка блокировки пользователя.")
        except Exception as e:
            logger.error(f"Ошибка в команде /ban: {e}")

    @dp.message(Command("unban"))
    async def cmd_unban(message: Message):
        try:
            if message.from_user.id != OWNER_ID:
                return
            
            try:
                user_id = int(message.text.split()[1])
                if db.unblock_user(user_id):
                    await message.reply("Пользователь разблокирован.")
                else:
                    await message.reply("Ошибка разблокировки пользователя.")
            except (IndexError, ValueError):
                await message.reply("Используй: /unban <user_id>")
            except Exception as e:
                logger.error(f"Ошибка разблокировки: {e}")
                await message.reply("Ошибка разблокировки пользователя.")
        except Exception as e:
            logger.error(f"Ошибка в команде /unban: {e}")

    @dp.message(Command("banned"))
    async def cmd_banned(message: Message):
        try:
            if message.from_user.id != OWNER_ID:
                return

            rows = db.get_blocked_users()
            if not rows:
                await message.reply("Список заблокированных пользователей пуст.")
                return

            text = "<b>Заблокированные пользователи:</b>\n\n"
            for (user_id,) in rows:
                text += f"- <a href='tg://user?id={user_id}'>{user_id}</a>\n"

            await message.reply(text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка в команде /banned: {e}")
            await message.reply("Ошибка получения списка заблокированных.")

    @dp.message(Command("ideas"))
    async def cmd_ideas(message: Message):
        try:
            if message.from_user.id != OWNER_ID:
                return

            rows = db.get_latest_ideas()
            if not rows:
                await message.reply("В базе идей пока пусто.")
                return

            text = "<b>Последние сохранённые идеи:</b>\n\n"
            for id_, user_id, username, msg, ts in rows:
                uname = username or "без ника"
                snippet = (msg[:50] + "...") if len(msg) > 50 else msg
                text += f"#{id_} [{uname}](tg://user?id={user_id}) ({ts}):\n{snippet}\n\n"

            await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Ошибка в команде /ideas: {e}")
            await message.reply("Ошибка получения идей.")