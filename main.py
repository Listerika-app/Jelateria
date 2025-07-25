import os
import logging
import base64
import requests
import time
from aiogram import Bot, Dispatcher, types, executor
from openai import OpenAI
from aiogram.types import ChatActions

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_descriptions = {}
user_images = {}
user_actions = {}  # сохраняем выбранное действие и стиль

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

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    file = await bot.get_file(message.photo[-1].file_id)
    photo = await bot.download_file(file.file_path)
    photo_bytes = photo.read()

    description = await describe_toy(photo_bytes)
    user_descriptions[user_id] = description

    image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    user_images[user_id] = image_url

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
    kb.add(*[types.InlineKeyboardButton(text=b, callback_data=f"action:{b}") for b in buttons])
    await message.reply(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("action:"))
async def handle_action(callback_query: types.CallbackQuery):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    user_actions[user_id] = {"action": action}

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(text="🎬 Мультфильм", callback_data="style:3d"),
        types.InlineKeyboardButton(text="📚 Комикс", callback_data="style:2d")
    )
    await bot.send_message(user_id, "Выбери стиль видео:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("style:"))
async def select_model(callback_query: types.CallbackQuery):
    style_choice = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    user_actions.setdefault(user_id, {})
    user_actions[user_id]["style"] = style_choice

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(text="🚀 Gen-4 Turbo", callback_data="model:gen-4-turbo"),
        types.InlineKeyboardButton(text="⚡ Gen-3 Alpha Turbo", callback_data="model:gen-3-alpha-turbo")
    )
    await bot.send_message(user_id, "Выбери модель генерации видео:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("model:"))
async def generate_video(callback_query: types.CallbackQuery):
    model_choice = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    user_data = user_actions.get(user_id, {})
    style_choice = user_data.get("style", "3d")
    action = user_data.get("action", "танцует")
    description = user_descriptions.get(user_id, "мягкая игрушка")
    image_url = user_images.get(user_id)

    character = description.replace("Это", "").replace("мягкая игрушка", "").strip(".").strip() or "мягкая игрушка"
    style = "в 3D стиле, как в мультфильмах Disney, яркий фон" if style_choice == "3d" else "в 2D стиле, как в мультфильмах Disney, яркий фон"
    prompt = f"Та же игрушка {action.lower()}, {style}"

    await bot.send_chat_action(user_id, ChatActions.UPLOAD_VIDEO)
    await bot.send_message(user_id, f"🎬 Генерируем видео: {action} + {style.split(',')[0]} на модели {model_choice}...")

    try:
        image_bytes = requests.get(image_url).content
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

        headers = {
            "Authorization": f"Bearer {RUNWAY_API_KEY}",
            "Content-Type": "application/json",
            "Runway-API-Version": "2024-05-01"
        }

        data = {
            "input": {
                "image": image_data_url,
                "prompt": prompt,
                "motion": "default",
                "num_frames": 80,
                "seed": 42
            }
        }

        response = requests.post(f"https://api.runwayml.com/v1/inference/{model_choice}", headers=headers, json=data)
        if response.status_code != 200 or "urls" not in response.json():
            logging.error(f"Ошибка запроса Runway: {response.text}")
            await bot.send_message(user_id, "❌ Runway не принял запрос. Попробуй позже.")
            return

        status_url = response.json()["urls"]["get"]
        video_url = None
        wait_message = await bot.send_message(user_id, "⏳ Генерируем видео")
        progress = ["⏳ Генерируем видео.", "⏳ Генерируем видео..", "⏳ Генерируем видео..."]

        for i in range(30):
            check = requests.get(status_url, headers=headers)
            status = check.json()
            if status.get("status") == "succeeded":
                video_url = status.get("output", {}).get("video")
                break
            dots = progress[i % 3]
            await bot.edit_message_text(chat_id=user_id, message_id=wait_message.message_id, text=dots)
            time.sleep(5)

        await bot.delete_message(chat_id=user_id, message_id=wait_message.message_id)

        if video_url:
            await bot.send_message(user_id, "🎉 Видео готово!")
            await bot.send_video(user_id, video_url)
        else:
            await bot.send_message(user_id, "⏳ Видео не удалось получить вовремя. Попробуй ещё раз.")

    except Exception as e:
        logging.error(f"Ошибка Runway: {e}")
        await bot.send_message(user_id, "❌ Не удалось сгенерировать видео.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
