import os
import threading
import urllib.request
import uuid
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

SHEETS_URL = "https://script.google.com/macros/s/AKfycbyeHeSge0G6V2PSUBh4Ln8rlbCTOy4oGhq0n_0Xx8W4wZBgCR1zMr7vt9T7xvXKZ8N2/exec"

web_app = Flask(__name__)

@web_app.get("/")
def home():
    return "Mama Care bot is running!"


def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port)
    

def keyboard(options):
    """Создаёт кнопки по одной в строке."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=data)]
        for text, data in options
    ])


def save_to_sheets(data):
    """Отправляет результаты анкеты в Google Sheets."""
    try:
        import json

        body = json.dumps(data).encode("utf-8")

        request = urllib.request.Request(
            SHEETS_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()

        print("Данные успешно сохранены в Google Sheets")

    except Exception as error:
        print(f"Ошибка сохранения в Google Sheets: {error}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    start_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            "▶️ Начать оценку",
            callback_data="start_assessment"
        )]]
    )

    await update.message.reply_text(
        "👩‍🍼 Добро пожаловать в Mama Care!\n\n"
        "Это короткий предварительный скрининг состояния "
        "тазового дна после родов.\n\n"
        "Анкета поможет оценить наличие симптомов "
        "недержания мочи и определить, нужна ли "
        "дополнительная консультация специалиста.\n\n"
        "⏱ Заполнение займёт всего несколько минут.\n\n"
        "⚠️ Результат не является медицинским диагнозом.",
        reply_markup=start_keyboard
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # НАЧАЛО АНКЕТЫ
    if data == "start_assessment":
        context.user_data.clear()
        context.user_data["step"] = "age"

        await query.edit_message_text(
            "🌷 Начинаем оценку.\n\n"
            "1️⃣ Сколько Вам лет?\n\n"
            "Введите возраст числом, например: 33"
        )
        return

    # КОЛИЧЕСТВО РОДОВ
    if data.startswith("births_"):
        value = data.replace("births_", "")
        context.user_data["births"] = value

        context.user_data["step"] = "delivery_method"

        await query.edit_message_text(
            "4️⃣ Как проходили Ваши последние роды?",
            reply_markup=keyboard([
                ("Естественные роды", "delivery_vaginal"),
                ("Кесарево сечение", "delivery_cesarean"),
                ("Вакуум / щипцы", "delivery_instrumental"),
            ])
        )
        return

    # СПОСОБ РОДОВ
    if data.startswith("delivery_"):
        context.user_data["delivery_method"] = data

        context.user_data["step"] = "birth_weight"

        await query.edit_message_text(
            "5️⃣ Какой вес был у ребёнка при рождении?\n\n"
            "Введите вес в граммах, например: 3500"
        )
        return

    # ТРАВМА / ЭПИЗИОТОМИЯ
    if data.startswith("trauma_"):
        context.user_data["trauma"] = data

        context.user_data["step"] = "leakage"

        await query.edit_message_text(
            "7️⃣ Бывает ли у Вас непроизвольное "
            "выделение мочи?",
            reply_markup=keyboard([
                ("Никогда", "leak_never"),
                ("Редко", "leak_rare"),
                ("Иногда", "leak_sometimes"),
                ("Часто", "leak_often"),
            ])
        )
        return

    # НЕДЕРЖАНИЕ МОЧИ
    if data.startswith("leak_"):
        context.user_data["leakage"] = data

          # ЕСЛИ НИКОГДА — СРАЗУ РЕЗУЛЬТАТ
        if data == "leak_never":
            context.user_data["completed"] = True
            
            save_to_sheets({
                "id": f"MC-{uuid.uuid4().hex[:8].upper()}",
                "age": context.user_data.get("age", ""),
                "delivery_year": context.user_data.get("delivery_year", ""),
                "births": context.user_data.get("births", ""),
                "delivery_method": context.user_data.get("delivery_method", ""),
                "birth_weight": context.user_data.get("birth_weight", ""),
                "trauma": context.user_data.get("trauma", ""),
                "leakage": context.user_data.get("leakage", ""),
                "leak_situation": "",
                "symptom_onset": "",
                "impact": "",
                "treatment": "",
                "treatment_effect": "",
                "risk": "🟢 НИЗКИЙ"
            })

            await query.edit_message_text(
                "🌷 Спасибо! Оценка завершена.\n\n"
                "По Вашим ответам на данный момент "
                "симптомы недержания мочи не выявлены.\n\n"
                "🟢 Результат скрининга: НИЗКИЙ РИСК.\n\n"
                "Рекомендуется продолжать профилактику "
                "нарушений тазового дна.\n\n"
                "Если в дальнейшем появится непроизвольное "
                "выделение мочи при кашле, чихании, "
                "физической нагрузке или сильном позыве, "
                "рекомендуется повторить оценку и "
                "обратиться к специалисту.\n\n"
                "⚠️ Результат является предварительным "
                "скринингом и не заменяет консультацию врача.\n\n"
                "Чтобы пройти оценку заново, нажмите /start."
            )
            return

        context.user_data["step"] = "leak_situation"

        await query.edit_message_text(
            "8️⃣ В каких ситуациях чаще всего происходит "
            "подтекание мочи?",
            reply_markup=keyboard([
                (
                    "При кашле, чихании, смехе",
                    "situation_cough"
                ),
                (
                    "При физической нагрузке",
                    "situation_activity"
                ),
                (
                    "При сильном внезапном позыве",
                    "situation_urgency"
                ),
                (
                    "В разных ситуациях",
                    "situation_mixed"
                ),
            ])
        )
        return

    # СИТУАЦИЯ ПОДТЕКАНИЯ
    if data.startswith("situation_"):
        context.user_data["leak_situation"] = data

        context.user_data["step"] = "symptom_onset"

        await query.edit_message_text(
            "9️⃣ Когда впервые появились симптомы?",
            reply_markup=keyboard([
                (
                    "Сразу после родов",
                    "onset_immediate"
                ),
                (
                    "В течение первого месяца",
                    "onset_month"
                ),
                (
                    "Через 1–6 месяцев",
                    "onset_1_6"
                ),
                (
                    "Более чем через 6 месяцев",
                    "onset_after_6"
                ),
                (
                    "Были ещё до беременности",
                    "onset_before"
                ),
            ])
        )
        return

    # КОГДА ПОЯВИЛИСЬ СИМПТОМЫ
    if data.startswith("onset_"):
        context.user_data["symptom_onset"] = data

        context.user_data["step"] = "impact"

        await query.edit_message_text(
            "🔟 Насколько эти симптомы мешают Вам "
            "в повседневной жизни?",
            reply_markup=keyboard([
                ("Практически не мешают", "impact_none"),
                ("Немного мешают", "impact_mild"),
                ("Заметно мешают", "impact_moderate"),
                ("Сильно мешают", "impact_severe"),
            ])
        )
        return

    # ВЛИЯНИЕ НА ЖИЗНЬ
    if data.startswith("impact_"):
        context.user_data["impact"] = data

        context.user_data["step"] = "treatment"

        await query.edit_message_text(
            "1️⃣1️⃣ Проводилось ли лечение или выполняли ли "
            "Вы упражнения для мышц тазового дна "
            "(упражнения Кегеля)?",
            reply_markup=keyboard([
                ("Нет", "treatment_no"),
                (
                    "Да, упражнения Кегеля",
                    "treatment_kegel"
                ),
                (
                    "Да, проходила другое лечение",
                    "treatment_other"
                ),
            ])
        )
        return

    # ЛЕЧЕНИЕ
    if data.startswith("treatment_"):
        context.user_data["treatment"] = data

        # ЕСЛИ ЛЕЧЕНИЯ НЕ БЫЛО — РЕЗУЛЬТАТ
        if data == "treatment_no":
            await show_result(query, context)
            return

        context.user_data["step"] = "treatment_effect"

        await query.edit_message_text(
            "1️⃣2️⃣ Был ли эффект от лечения или упражнений?",
            reply_markup=keyboard([
                ("Да, стало значительно лучше", "effect_good"),
                ("Стало немного лучше", "effect_partial"),
                ("Эффекта не было", "effect_none"),
                ("Стало хуже", "effect_worse"),
            ])
        )
        return

    # ЭФФЕКТ ЛЕЧЕНИЯ
    if data.startswith("effect_"):
        context.user_data["treatment_effect"] = data
        await show_result(query, context)
        return


async def show_result(query, context):
    """Простая предварительная оценка риска."""

    score = 0

    leakage = context.user_data.get("leakage", "")
    impact = context.user_data.get("impact", "")
    situation = context.user_data.get("leak_situation", "")
    trauma = context.user_data.get("trauma", "")
    weight = context.user_data.get("birth_weight", 0)
    effect = context.user_data.get("treatment_effect", "")

    if leakage == "leak_rare":
        score += 1
    elif leakage == "leak_sometimes":
        score += 2
    elif leakage == "leak_often":
        score += 3

    if impact == "impact_mild":
        score += 1
    elif impact == "impact_moderate":
        score += 2
    elif impact == "impact_severe":
        score += 3

    if situation in [
        "situation_cough",
        "situation_activity",
        "situation_mixed"
    ]:
        score += 1

    if trauma in [
        "trauma_tear",
        "trauma_episiotomy",
        "trauma_both"
    ]:
        score += 1

    if isinstance(weight, int) and weight >= 4000:
        score += 1

    if effect in ["effect_none", "effect_worse"]:
        score += 1

    if score <= 3:
        risk = "🟢 НИЗКИЙ"
        recommendation = (
            "На данный момент выраженный риск по результатам "
            "скрининга не выявлен. Наблюдайте за симптомами "
            "и уделяйте внимание здоровью тазового дна."
        )

    elif score <= 6:
        risk = "🟡 СРЕДНИЙ"
        recommendation = (
            "Рекомендуется плановая консультация специалиста "
            "для более подробной оценки состояния тазового дна."
        )

    else:
        risk = "🔴 ВЫСОКИЙ"
        recommendation = (
            "Рекомендуется обратиться к специалисту для "
            "очной оценки и дополнительного обследования."
        )
    
    context.user_data["risk_score"] = score
    context.user_data["completed"] = True

    save_to_sheets({
        "id": f"MC-{uuid.uuid4().hex[:8].upper()}",
        "age": context.user_data.get("age", ""),
        "delivery_year": context.user_data.get("delivery_year", ""),
        "births": context.user_data.get("births", ""),
        "delivery_method": context.user_data.get("delivery_method", ""),
        "birth_weight": context.user_data.get("birth_weight", ""),
        "trauma": context.user_data.get("trauma", ""),
        "leakage": context.user_data.get("leakage", ""),
        "leak_situation": context.user_data.get("leak_situation", ""),
        "symptom_onset": context.user_data.get("symptom_onset", ""),
        "impact": context.user_data.get("impact", ""),
        "treatment": context.user_data.get("treatment", ""),
        "treatment_effect": context.user_data.get("treatment_effect", ""),
        "risk": risk
    })

    await query.edit_message_text(
        "🌷 Спасибо! Анкета завершена.\n\n"
        f"Результат предварительного скрининга: {risk} РИСК.\n\n"
        f"{recommendation}\n\n"
        "⚠️ Mama Care не устанавливает диагноз. "
        "Результат является предварительной оценкой "
        "и не заменяет консультацию врача.\n\n"
        "Чтобы пройти оценку заново, нажмите /start."
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()
    step = context.user_data.get("step")

    # ВОЗРАСТ
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
            "2️⃣ В каком году были Ваши последние роды?\n\n"
            "Введите год, например: 2025"
        )
        return

    # ГОД РОДОВ
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
        context.user_data["step"] = "births"

        await update.message.reply_text(
            "3️⃣ Сколько всего у Вас было родов?",
            reply_markup=keyboard([
                ("1", "births_1"),
                ("2", "births_2"),
                ("3", "births_3"),
                ("4 и более", "births_4plus"),
            ])
        )
        return

    # ВЕС РЕБЁНКА
    if step == "birth_weight":
        if not text.isdigit():
            await update.message.reply_text(
                "Пожалуйста, укажите вес ребёнка цифрами "
                "в граммах.\nНапример: 3500"
            )
            return

        weight = int(text)

        if weight < 500 or weight > 6000:
            await update.message.reply_text(
                "Пожалуйста, проверьте вес и введите его "
                "в граммах, например: 3500."
            )
            return

        context.user_data["birth_weight"] = weight
        context.user_data["step"] = "trauma"

        await update.message.reply_text(
            "6️⃣ Во время последних родов были ли у Вас "
            "травмы промежности или выполнялась "
            "эпизиотомия (разрез)?",
            reply_markup=keyboard([
                ("Нет", "trauma_no"),
                ("Был разрыв", "trauma_tear"),
                (
                    "Была эпизиотомия (разрез)",
                    "trauma_episiotomy"
                ),
                (
                    "И разрыв, и эпизиотомия",
                    "trauma_both"
                ),
                (
                    "Не знаю / не помню",
                    "trauma_unknown"
                ),
            ])
        )
        return

    await update.message.reply_text(
        "Чтобы начать новую оценку, нажмите /start."
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в Environment Variables."
        )

    application = Application.builder().token(TOKEN).build()

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(button_click)
    )

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
