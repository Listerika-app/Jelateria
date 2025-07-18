import os
import logging
import base64
import requests
import time
from aiogram import Bot, Dispatcher, types, executor
from openai import OpenAI

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Храним описания пользователей
user_descriptions = {}

# Генерируем описание игрушки
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
    user_descriptions[user_id] = description

    await message.reply(description)

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

# Обработка кнопок и видео Runway
@dp.callback_query_handler()
async def process_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    user_id = callback_query.from_user.id

    await bot.send_message(user_id, f"🎬 Оживляем: {action}...")

    description = user_descriptions.get(user_id, "мягкая игрушка")
    character = description.replace("Это", "").replace("мягкая игрушка", "").strip(".").strip() or "мягкая игрушка"
    style = "в 3D стиле, как в мультфильмах Disney, яркий фон"

    if action == "Танец":
        prompt = f"{character} танцует, {style}"
    elif action == "Поцелуйчики":
        prompt = f"{character} посылает воздушный поцелуй, улыбается, {style}"
    elif action == "Привет":
        prompt = f"{character} машет рукой и улыбается, {style}"
    elif action == "Едем":
        prompt = f"{character} едет по игрушечному городу, {style}"
    elif action == "Дрифт":
        prompt = f"{character} дрифтит с дымом из-под колёс, {style}"
    else:
        await bot.send_message(user_id, "Пока не умею оживлять это действие 🙈")
        return

    try:
        headers = {
            "Authorization": f"Bearer {RUNWAY_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "input": {
                "prompt": prompt,
                "num_frames": 80,
                "seed": 42
            }
        }

        response = requests.post(
            "https://api.runwayml.com/v1/generate/video/text-to-video",
            headers=headers,
            json=data
        )

        generation_id = response.json()["id"]
        video_url = None

        for _ in range(30):
            check = requests.get(
                f"https://api.runwayml.com/v1/generate/video/{generation_id}",
                headers=headers
            )
            status = check.json()
            if status.get("status") == "succeeded":
                video_url = status["video_url"]
                break
            time.sleep(5)

        if video_url:
            await bot.send_video(user_id, video_url)
        else:
            await bot.send_message(user_id, "⏳ Видео не удалось получить вовремя. Попробуй ещё раз.")

    except Exception as e:
        logging.error(f"Ошибка Runway: {e}")
        await bot.send_message(user_id, "❌ Не удалось сгенерировать видео.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
