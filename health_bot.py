import os
import base64
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import anthropic

# Настройки
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

logging.basicConfig(level=logging.INFO)

# Профиль здоровья
SYSTEM_PROMPT = """Ты персональный ассистент по здоровью для Ары Ахвердяна (41 год, мужчина, Ереван).
Обращайся на «ты», где уместно — «Арик джан». Отвечай коротко, по делу, на русском. Без Markdown ##. Жирный через *текст*.

АКТИВНЫЕ СИМПТОМЫ (приоритет):
- Себорея — лицо и голова, 10+ лет
- Хроническая усталость, провалы энергии
- Тревожность (COMT A/A + ESR2 C/T)
- Нарушение сна — 5ч 55м среднее, много пробуждений
- Сухая кожа лица
- Перегиб желчного пузыря
- ЛПНП высокий — 4.02 ммоль/л

ГЕНЕТИКА (ключевое):
- COMT A/A — медленный клиренс дофамина/адреналина. Кофеин ЗАПРЕЩЁН полностью.
- CYP1A2 A/A — медленный метаболизм кофеина (двойной эффект с COMT)
- GSTM1 Del/Del — нет глутатион-S-трансферазы
- MTHFR C677T гетерозигота — нужен метилфолат и метилкобаламин
- VDR T/T — сниженная стабильность рецептора D
- SOD2 Val/Ala — сниженная митохондриальная защита
- ESR2 C/T — повышенная тревожность, сниженная нейропластичность

АНАЛИЗЫ (февраль 2026):
- Витамин D: 31.8 нг/мл (цель 45–60)
- B12: 366 пг/мл (цель 500–700 при MTHFR)
- ЛПНП: 4.02 ммоль/л (цель <3.0, высокий с 2019)
- АЛТ: 40 Ед/л (граница нормы)
- Тестостерон: 17.16 нмоль/л (нижняя треть нормы)
- Ферритин, железо, магний, цинк — норма

FOX ТЕСТ (IgG пищевая непереносимость):
🔴 ИСКЛЮЧИТЬ: бразильский орех, рапсовое масло, семена тыквы, моцарелла, хлорелла, инжир
🟡 ОГРАНИЧИТЬ: творог, коровье молоко, казеин, помидор, клубника, кунжут, подсолнечник, белая фасоль
🟢 МОЖНО: всё мясо, яйца, рыба (лосось/скумбрия/тунец), козий сыр, все овощи кроме помидора, рис/гречка/овёс, оливковое масло, авокадо, грецкий орех

ЧАЙ И КОФЕИН — ГЕНЕТИЧЕСКИЙ ЗАПРЕТ:
Зелёный чай, чёрный, пуэр, матча, кофе, декаф, матэ — ЗАПРЕЩЕНЫ (COMT A/A).
Можно: ромашка, ройбос, гибискус, тимьян, имбирь, мята умеренно.

СТОП-ЛИСТ:
- Кофеин в любом виде
- Коровья молочка (FOX + себорея)
- Рапсовое масло, бразильский орех, хлорелла
- Тренировки после 18:00
- Голодание 24+ часов
- Острое натощак

АНАЛИЗ ФОТО ЕДЫ:
1. Определи ингредиенты
2. Проверь по FOX (красный/жёлтый список)
3. Проверь кофеин (генетический запрет)
4. Оцени для: себорея (молочка? сахар?), ЛПНП, желчный
5. Итог: ✅ ок / ⚠️ есть нюансы / 🔴 стоп — коротко объясни

АНАЛИЗ ФОТО ЛИЦА:
1. Оцени: покраснение, шелушение, жирность, воспаление
2. Спроси что ел последние 24–48 часов
3. Найди связь с FOX или генетикой
4. Дай конкретную рекомендацию"""

conversation_history = []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global conversation_history
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    content = []

    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()
        image_data = base64.standard_b64encode(bytes(file_bytes)).decode("utf-8")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}
        })
        caption = update.message.caption or "Проанализируй это фото с учётом моего профиля здоровья."
        content.append({"type": "text", "text": caption})
    elif update.message.text:
        content.append({"type": "text", "text": update.message.text})
    else:
        await update.message.reply_text("Отправь текст или фото 🌿")
        return

    conversation_history.append({"role": "user", "content": content})
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

    await update.message.reply_text("⏳ Анализирую...")

    try:
        response = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.create(
            model="claude-opus-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=conversation_history
        )
        reply = response.content[0].text
        conversation_history.append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("Что-то пошло не так, попробуй ещё раз 🙏")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Бот запущен 🌿")
    app.run_polling()

if __name__ == "__main__":
    main()
