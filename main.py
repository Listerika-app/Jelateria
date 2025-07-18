import os
import logging
import openai
import base64
from aiogram import Bot, Dispatcher, types, executor

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def classify_toy(photo_bytes):
    b64 = base64.b64encode(photo_bytes).decode('utf-8')
    image_data = f"data:image/jpeg;base64,{b64}"

    response = openai.ChatCompletion.create(
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

    result = response.choices[0].message["content"].strip().lower()
    logging.info(f"Определено: {result}")
    return result

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    file = await bot.get_file(message.photo[-1].file_id)
    photo = await bot.download_file(file.file_path)
    photo_bytes = photo.read()

    toy_type = await classify_toy(photo_bytes)

    if "мягкая" in toy_type:
        text = "Начинаем оживлять мягкую игрушку!"
        buttons = ["Танец", "Поцелуйчики"]
    elif "кукла" in toy_type:
        text = "Начинаем волшебство, оживляем куклу!"
        buttons = ["Привет", "Поцелуйчики"]
    elif "машинка" in toy_type:
        text = "Ну что, заводим мотор и поехали?"
        buttons = ["Едем", "Дрифт"]
    else:
        await message.reply("Не удалось определить игрушку 😢")
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(*[types.InlineKeyboardButton(text=b, callback_data=b) for b in buttons])
    await message.reply(text, reply_markup=kb)

@dp.callback_query_handler()
async def process_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    await bot.send_message(callback_query.from_user.id, f"🎬 Оживляем игрушку... [{action}]")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
