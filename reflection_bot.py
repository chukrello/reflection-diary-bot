import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import requests
from datetime import date

BOT_TOKEN = os.getenv("BOT_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

app = FastAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_texts = {}

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Отправьте текст, спрошу тип (health/food/work)")

@dp.message(Command("ping"))
async def ping(message: Message):
    await message.answer("🏓 Pong!\n🟢 Бот работает\n⏰ " + date.today().isoformat())

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
    
    response = requests.post('https://api.notion.com/v1/pages', 
        headers={'Authorization': f'Bearer {NOTION_TOKEN}', 
                'Notion-Version': '2022-06-28', 
                'Content-Type': 'application/json'},
        json={
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": text}}]},
                "Select": {"select": {"name": typ}}
                # "Дата" удалена
            }
        })
    
    status = "✅" if response.status_code == 200 else f"❌ {response.status_code}"
    await callback.message.edit_text(f"{status} Сохранено в Notion!\n🏷️ {typ}")
    del user_texts[user_id]

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook()
    print("🚀 Бот запущен в polling режиме!")
    asyncio.create_task(dp.start_polling(bot))

@app.get("/")
@app.head("/", include_in_schema=False)
async def root():
    return {"status": "online", "bot": "reflection-diary"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
