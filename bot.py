import os
import threading

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
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
    context.user_data.clear()

    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ Начать оценку",
                callback_data="start_assessment"
            )
        ]
    ]

    await update.message.reply_text(
        "👩‍🍼 Добро пожаловать в Mama Care!\n\n"
        "Это предварительный скрининг симптомов после родов.\n\n"
        "Анкета помогает оценить наличие симптомов "
        "недержания мочи и определить, нужна ли "
        "дополнительная консультация специалиста.\n\n"
        "⚠️ Результат не является медицинским диагнозом.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_assessment":
        context.user_data["step"] = "age"

        await query.edit_message_text(
            "Отлично! 🌷\n\n"
            "Начинаем оценку.\n\n"
            "Первый вопрос:\n\n"
            "Сколько вам лет?\n\n"
            "Введите возраст числом, например: 33"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("step")

    if step == "age":
        if not text.isdigit():
            await update.message.reply_text(
                "Пожалуйста, введите возраст числом.\n"
                "Например: 33"
            )
            return

        age = int(text)

        if age < 18 or age > 60:
            await update.message.reply_text(
                "Пожалуйста, укажите возраст от 18 до 60 лет."
            )
            return

        context.user_data["age"] = age
        context.user_data["step"] = "delivery_year"

        await update.message.reply_text(
            f"Спасибо! 🌷\n\n"
            f"Возраст: {age} лет.\n\n"
            "Второй вопрос:\n\n"
            "В каком году вы родили ребёнка?\n\n"
            "Введите год, например: 2025"
        )
        return

    if step == "delivery_year":
        if not text.isdigit():
            await update.message.reply_text(
                "Пожалуйста, введите год числом.\n"
                "Например: 2025"
            )
            return

        year = int(text)

        if year < 2000 or year > 2026:
            await update.message.reply_text(
                "Пожалуйста, укажите год от 2000 до 2026."
            )
            return

        context.user_data["delivery_year"] = year
        context.user_data["step"] = "completed_test"

        await update.message.reply_text(
            "Спасибо! 🌷\n\n"
            "Первые данные сохранены.\n\n"
            f"Возраст: {context.user_data['age']} лет\n"
            f"Год родов: {year}\n\n"
            "Тестовый этап анкеты завершён."
        )
        return

    await update.message.reply_text(
        "Чтобы начать оценку, нажмите /start."
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в Environment Variables."
        )

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    threading.Thread(
        target=run_web_server,
        daemon=True
    ).start()

    application.run_polling()


if __name__ == "__main__":
    main()
