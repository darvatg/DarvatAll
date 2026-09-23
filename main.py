import html
import json
import os

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]
# на Bothost папка /app/data сохраняется между обновлениями
DATA_DIR = "/app/data" if os.path.isdir("/app/data") else "."
DB_FILE = os.path.join(DATA_DIR, "members.json")
CHUNK = 10  # сколько упоминаний в одном сообщении


def load() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запоминаем каждого, кто пишет в чат (Telegram не отдаёт список участников)."""
    chat, user = update.effective_chat, update.effective_user
    if not chat or not user or chat.type == "private" or user.is_bot:
        return
    data = load()
    data.setdefault(str(chat.id), {})[str(user.id)] = user.first_name
    # заодно запоминаем новых участников
    if update.message and update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if not m.is_bot:
                data[str(chat.id)][str(m.id)] = m.first_name
    save(data)


async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("Команда работает только в группах.")
        return

    data = load()
    members = data.setdefault(str(chat.id), {})

    # админов можно получить напрямую
    for a in await context.bot.get_chat_administrators(chat.id):
        if not a.user.is_bot:
            members[str(a.user.id)] = a.user.first_name
    save(data)

    text = " ".join(context.args)
    prefix = f"{html.escape(text)}\n" if text else ""

    mentions = [
        f'<a href="tg://user?id={uid}">{html.escape(name)}</a>'
        for uid, name in members.items()
    ]
    for i in range(0, len(mentions), CHUNK):
        part = " ".join(mentions[i : i + CHUNK])
        await update.effective_chat.send_message(
            (prefix if i == 0 else "") + part, parse_mode=ParseMode.HTML
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, remember), group=-1)
    app.add_handler(CommandHandler(["all", "everyone"], tag_all))
    app.run_polling()


if __name__ == "__main__":
    main()
