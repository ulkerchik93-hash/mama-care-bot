import os
import threading

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return "Mama Care bot is running!"


def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ Начать оценку",
                callback_data="start_assessment"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👩‍🍼 Добро пожаловать в Mama Care!\n\n"
        "Это предварительный скрининг симптомов после родов.\n\n"
        "Анкета помогает оценить наличие симптомов "
        "недержания мочи и определить, нужна ли "
        "дополнительная консультация специалиста.\n\n"
        "⚠️ Результат не является медицинским диагнозом.",
        reply_markup=reply_markup
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_assessment":
        await query.edit_message_text(
            "Отлично! 🌷\n\n"
            "Начинаем оценку.\n\n"
            "Первый вопрос:\n\n"
            "Сколько вам лет?"
        )


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))

    threading.Thread(
        target=run_web_server,
        daemon=True
    ).start()

    application.run_polling()


if __name__ == "__main__":
    main()
