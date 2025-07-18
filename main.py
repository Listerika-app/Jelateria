import os
import base64
import logging
from aiogram import Bot, Dispatcher, types, executor
from openai import OpenAI

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def classify_toy(photo_bytes):
    b64 = base64.b64encode(photo_bytes).decode("utf-8")
    image_data = f"data:image/jpeg;base64,{b64}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Что изображено на фото? Ответь одним словом: кукла, машинка или мягкая игрушка."},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ]
            }
        ],
        max_tokens=10
    )

    result = response.choices[0].message.content.strip().lower()
    logging.info(f"GPT ответил: {result}")
    return result

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

@dp.callback_query_handler()
async def process_cb(cq: types.CallbackQuery):
    action = cq.data
    await bot.send_message(cq.from_user.id, f"🎬 Оживляем игрушку... [{action}]")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
