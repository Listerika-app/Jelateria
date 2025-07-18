import os
import logging
import base64
from aiogram import Bot, Dispatcher, types, executor
from openai import OpenAI

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Определение типа игрушки по фото
async def classify_toy(photo_bytes):
    b64 = base64.b64encode(photo_bytes).decode("utf-8")
    image_data = f"data:image/jpeg;base64,{b64}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Определи, что изображено на фото. Ответь одним словом: кукла, машинка или мягкая игрушка."},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ]
            }
        ],
        max_tokens=10
    )

    result = response.choices[0].message.content.strip().lower()
    logging.info(f"[GPT определил]: {result}")
    return result

# Обработка входящего фото
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    file = await bot.get_file(message.photo[-1].file_id)
    photo = await bot.download_file(file.file_path)
    photo_bytes = photo.read()

    toy_type = await classify_toy(photo_bytes)

    if "мягкая" in toy_type:
        text, buttons = "Начинаем оживлять мягкую игрушку!", ["Танец", "Поцелуйчики"]
    elif "кукла" in toy_type:
        text, buttons = "Начинаем волшебство, оживляем куклу!", ["Привет", "Поцелуйчики"]
    elif "машинка" in toy_type:
        text, buttons = "Ну что, заводим мотор и поехали?", ["Едем", "Дрифт"]
    else:
        await message.reply("Не удалось определить игрушку 😢")
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(*[types.InlineKeyboardButton(text=b, callback_data=b) for b in buttons])
    await message.reply(text, reply_markup=kb)

# Оживление по кнопке
@dp.callback_query_handler()
async def process_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    user_id = callback_query.from_user.id

    await bot.send_message(user_id, f"🎬 Оживляем: {action}...")

    # Универсальные промпты для мягкой игрушки
    if action == "Танец":
        prompt = "Мягкая игрушка танцует с радостью, мультяшный стиль, яркий фон, детская атмосфера"
    elif action == "Поцелуйчики":
        prompt = "Мягкая игрушка посылает воздушный поцелуй, улыбается, милый мультяшный стиль, яркий фон"
    elif action == "Привет":
        prompt = "Кукла улыбается и машет рукой, мультяшный стиль"
    elif action == "Едем":
        prompt = "Игрушечная машинка едет по игрушечному городу, мультяшный стиль"
    elif action == "Дрифт":
        prompt = "Игрушечная машинка дрифтит с дымом из-под колёс, весёлый стиль"
    else:
        await bot.send_message(user_id, "Пока не умею оживлять это действие 🙈")
        return

    try:
        image = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
        image_url = image.data[0].url
        await bot.send_photo(user_id, image_url)
    except Exception as e:
        logging.error(f"Ошибка генерации изображения: {e}")
        await bot.send_message(user_id, "Не удалось оживить игрушку 😢")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
