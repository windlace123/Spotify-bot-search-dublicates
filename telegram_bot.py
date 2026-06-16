from aiogram import Dispatcher, Bot, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import CommandStart
import asyncio
from dotenv import load_dotenv
import os
import httpx
from deep_translator import GoogleTranslator

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

text_in_handlers = [
    "Введите ссылку на плейлист Spotify, чтобы начать поиск дубликатов 🌐",
    "Неверная ссылка или плейлист пуст ❌", 
    "Подождите, идет обработка запроса... 💤", 
    "Дубликаты не найдены ❌", 
    "Найдены дубликаты ✅", 
    "Пожалуйста, отправьте корректную ссылку на Spotify ❌"
]

async def translate_text(text, lang):
    return await asyncio.to_thread(
        GoogleTranslator(source='auto', target=lang).translate, text
    )

async def client_httpx(url_playlist: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post("http://127.0.0.1:8000", json={"path_on_playlist": url_playlist})
        return response.json()

@dp.message(CommandStart())
async def start_command(message: Message):
    buttons = [
        [InlineKeyboardButton(text='[US] English', callback_data='en')],
        [InlineKeyboardButton(text='[RU] Русский', callback_data='ru')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Select language | Выберите язык", reply_markup=keyboard)

select_language = {}

@dp.callback_query(F.data.in_(['en', 'ru']))
async def callback_handler(callback: CallbackQuery):
    select_language[callback.from_user.id] = callback.data
    translated = await translate_text(text_in_handlers[0], callback.data)
    await callback.message.edit_text(translated)
    await callback.answer()

# Проверка на наличие "spotify.com" в тексте
@dp.message(F.text.contains("spotify.com"))
async def message_handler(message: Message):
    lang = select_language.get(message.from_user.id, 'en')
    
    wait_msg = await translate_text(text_in_handlers[2], lang)
    sent_status = await message.answer(wait_msg)

    try:
        data = await client_httpx(message.text)
        if "error" in data:
            raise Exception("API Error")

        lst_name = data.get("lst_name", [])
        lst_autors = data.get("lst_autors", [])
        
        seen = set()
        duplicates = []

        for a, n in zip(lst_autors, lst_name):
            pair = (a, n)
            if pair in seen:
                duplicates.append(f"{n} — {a}")
            else:
                seen.add(pair)
        
        # Сначала удаляем сообщение о загрузке
        await bot.delete_message(chat_id=message.chat.id, message_id=sent_status.message_id)

        if not duplicates:
            res_text = await translate_text(text_in_handlers[3], lang)
            await message.answer(res_text)
        else:
            header = await translate_text(text_in_handlers[4], lang)
            # Если дубликатов слишком много, разбиваем сообщение (лимит TG 4096 символов)
            full_list = "\n".join(duplicates)
            await message.answer(f"{header}\n\n{full_list}"[:4096])

    except Exception:
        await bot.delete_message(chat_id=message.chat.id, message_id=sent_status.message_id)
        error_text = await translate_text(text_in_handlers[1], lang)
        await message.answer(error_text)

@dp.message()
async def other_messages(message: Message):
    lang = select_language.get(message.from_user.id, 'en')
    error_text = await translate_text(text_in_handlers[5], lang)
    await message.answer(error_text)
    
async def main():
    print("Bot Online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())