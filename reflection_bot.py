import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.webhook import aiohttp_server
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import requests
from datetime import date

BOT_TOKEN = os.getenv("BOT_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
WEBHOOK_URL = "https://reflection-diary-bot.onrender.com/webhook"

user_texts = {}

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Отправьте текст, спрошу тип (health/food/work)")

@dp.message()
async def ask_type(message: Message):
    user_texts[message.from_user.id] = message.text
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="health 🏥", callback_data="health")],
        [InlineKeyboardButton(text="food 🍎", callback_data="food")],
        [InlineKeyboardButton(text="work 💼", callback_data="work")]
    ])
    await message.answer("Выберите тип:", reply_markup=kb)

@dp.callback_query(F.data.in_(['health', 'food', 'work']))
async def save_notion(callback: CallbackQuery):
    user_id = callback.from_user.id
    text = user_texts.get(user_id, "нет текста")
    typ = callback.data
    today = date.today().isoformat()
    
    response = requests.post('https://api.notion.com/v1/pages', 
        headers={'Authorization': f'Bearer {NOTION_TOKEN}', 
                'Notion-Version': '2022-06-28', 
                'Content-Type': 'application/json'},
        json={
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": text}}]},
                "Тип": {"select": {"name": typ}},
                "Дата": {"date": {"start": today}}
            }
        })
    
    status = "✅" if response.status_code == 200 else f"❌ {response.status_code}"
    await callback.message.edit_text(f"{status} Сохранено в Notion!\n📝 {text}\n🏷️ {typ}")
    del user_texts[user_id]

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    print("🛑 Webhook удалён")

async def main():
    logging.basicConfig(level=logging.INFO)
    app = aiohttp_server.Application()
    request_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    request_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    await app.startup()
    print("🚀 Сервер запущен!")
    await app.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
