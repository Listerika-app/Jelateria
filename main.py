import os
import logging
from aiogram import Bot, Dispatcher, types, executor
import openai

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def classify_toy(photo_bytes_b64):
    response = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "user", "content": "Определи одним словом: кукла, машинка или мягкая игрушка."},
            {"role": "user", "content": photo_bytes_b64}
        ],
        max_tokens=10
    )
    return response.choices[0].message["content"].strip().lower()

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    f = await bot.get_file(message.photo[-1].file_id)
    data = await bot.download_file(f.file_path)
    import base64
    b64 = base64.b64encode(data.read()).decode('utf-8')
    toy_type = await classify_toy(b64)

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

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
