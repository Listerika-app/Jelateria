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

# Для хранения описаний на пользователя
user_descriptions = {}

# GPT: описывает игрушку по изображению
async def describe_toy(photo_bytes):
    b64 = base64.b64encode(photo_bytes).decode("utf-8")
    image_data = f"data:image/jpeg;base64,{b64}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Опиши, что изображено на фото. Если это игрушка, укажи какая именно: кукла, машинка или мягкая игрушка. Опиши персонажа. Используй одно-два предложения."},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ]
            }
        ],
        max_tokens=50
    )

    description = response.choices[0].message.content.strip()
    logging.info(f"[Описание игрушки]: {description}")
    return description

# Обработка фото
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    file = await bot.get_file(message.photo[-1].file_id)
    photo = await bot.download_file(file.file_path)
    photo_bytes = photo.read()

    description = await describe_toy(photo_bytes)
    user_descriptions[user_id] = description  # Сохраняем описание

    await message.reply(description)

    # Определение типа и кнопок
    if "мягкая" in description.lower():
        text, buttons = "Начинаем оживлять мягкую игрушку!", ["Танец", "Поцелуйчики"]
    elif "кукла" in description.lower():
        text, buttons = "Начинаем волшебство, оживляем куклу!", ["Привет", "Поцелуйчики"]
    elif "машин" in description.lower():
        text, buttons = "Ну что, заводим мотор и поехали?", ["Едем", "Дрифт"]
    else:
        await message.reply("Не удалось точно определить тип игрушки 😢")
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(*[types.InlineKeyboardButton(text=b, callback_data=b) for b in buttons])
    await message.reply(text, reply_markup=kb)

# Обработка кнопок
@dp.callback_query_handler()
async def process_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    user_id = callback_query.from_user.id

    await bot.send_message(user_id, f"🎬 Оживляем: {action}...")

    # Получаем описание игрушки
    description = user_descriptions.get(user_id, "мягкая игрушка")

    # Определяем персонажа (например, "котик")
    # Выделим первое подходящее существительное из описания
    character = description.replace("Это", "").replace("мягкая игрушка", "").strip().strip(".") or "мягкая игрушка"

    # Формируем промпт
    if action == "Танец":
        prompt = f"{character} танцует в мультяшном стиле, яркий фон, детская атмосфера"
    elif action == "Поцелуйчики":
        prompt = f"{character} посылает воздушный поцелуй, улыбается, мультяшный стиль, яркий фон"
    elif action == "Привет":
        prompt = f"{character} улыбается и машет рукой, дружелюбный стиль"
    elif action == "Едем":
        prompt = f"{character} едет по игрушечному городу, радостная атмосфера, мультяшный стиль"
    elif action == "Дрифт":
        prompt = f"{character} дрифтит с дымом из-под колёс, стильное движение, как в мультике"
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
