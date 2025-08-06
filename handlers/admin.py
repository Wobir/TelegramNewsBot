from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from db import block_user, unblock_user, get_blocked_users, get_latest_ideas
from config import OWNER_ID


def register_admin_handlers(dp: Dispatcher, bot):

    @dp.message(Command("ban"))
    async def cmd_ban(message: Message):
        if message.from_user.id != OWNER_ID:
            return
        try:
            block_user(int(message.text.split()[1]))
            await message.reply("Пользователь заблокирован.")
        except:
            await message.reply("Используй: /ban <user_id>")

    @dp.message(Command("unban"))
    async def cmd_unban(message: Message):
        if message.from_user.id != OWNER_ID:
            return
        try:
            unblock_user(int(message.text.split()[1]))
            await message.reply("Пользователь разблокирован.")
        except:
            await message.reply("Используй: /unban <user_id>")

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
