import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    BOT_TOKEN,
    WEBHOOK_PATH,
    WEBHOOK_URL,
    WEBAPP_HOST,
    WEBAPP_PORT,
)
from database import init_db
from handlers import admin, operator, user

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi! Environment variables'ga qo'shing.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Tartib muhim: admin va operator buyruqlari birinchi tekshiriladi
dp.include_router(admin.router)
dp.include_router(operator.router)
dp.include_router(user.router)


async def on_startup(app: web.Application):
    await init_db()
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"✅ Webhook o'rnatildi: {WEBHOOK_URL}")
    else:
        logging.warning(
            "⚠️ WEBHOOK_HOST topilmadi! Webhook o'rnatilmadi — bot xabarlarni qabul qilmaydi."
        )


async def on_shutdown(app: web.Application):
    # Diqqat: bu yerda bot.delete_webhook() chaqirilmaydi!
    # Render bepul tarifida xizmat uxlab qolganda shu funksiya chaqiriladi;
    # agar webhook shu yerda o'chirilsa, Telegram botga xabar yuborishni to'xtatadi
    # va xizmat boshqa hech qachon o'zi uyg'onmaydi.
    await bot.session.close()


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="Bot ishlayapti ✅")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health_check)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=WEBAPP_HOST, port=WEBAPP_PORT)
