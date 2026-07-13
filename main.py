import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import admin, operator, user

logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida topilmadi!")

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Tartib muhim: admin va operator buyruqlari birinchi tekshiriladi
    dp.include_router(admin.router)
    dp.include_router(operator.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
