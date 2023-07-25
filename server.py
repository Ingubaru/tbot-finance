import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, executor, types

logging.basicConfig(level=logging.INFO)

TELEGRAM_API_TOKEN = "6639006428:AAE2J93jOqBFwa5F21No3_rX76NOGdkWe_o"

bot = Bot(token=TELEGRAM_API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и помощь по боту"""
    await message.answer(f'Hello, {message.from_user.full_name}')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)