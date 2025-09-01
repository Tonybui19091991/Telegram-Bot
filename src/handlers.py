import os
from telegram import Update, InputFile, Bot
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from dotenv import load_dotenv
import asyncio
import aiohttp

# Load biến môi trường từ file .env
load_dotenv()

IMAGE_PATH = os.getenv("IMAGE_PATH", "kota.jpg")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = Bot(token=BOT_TOKEN)

import asyncio
import aiohttp

async def send_kota(Caption, Keyboard, imagePath):
    try:
        if imagePath and imagePath.startswith("http"):
            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(imagePath, allow_redirects=True) as resp:
                        if resp.headers.get("Content-Type", "").startswith("image/"):
                            await bot.send_photo(
                                chat_id=CHANNEL_USERNAME,
                                photo=imagePath,
                                caption=Caption,
                                parse_mode=ParseMode.HTML,
                                reply_markup=Keyboard,
                            )
                            return
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                print(f"Image URL check timeout or error: {e}")

        elif imagePath:  # file local
            try:
                with open(imagePath, "rb") as f:
                    await bot.send_photo(
                        chat_id=CHANNEL_USERNAME,
                        photo=InputFile(f, filename="kota.jpg"),
                        caption=Caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=Keyboard,
                    )
                    return
            except Exception as e:
                print(f"Local image send error: {e}")

    except Exception as e:
        print(f"send_kota error: {e}")

    # fallback nếu có lỗi hoặc không có ảnh
    # await bot.send_message(
    #     chat_id=CHANNEL_USERNAME,
    #     text=Caption,
    #     parse_mode=ParseMode.HTML,
    #     reply_markup=Keyboard,
    # )