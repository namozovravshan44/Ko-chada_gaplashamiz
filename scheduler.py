"""
Fon rejimida (background) vaqti-vaqti bilan ishlaydigan vazifalar:
  3.  24 soatlik follow-up eslatma (sotib olishni bosib, to'lamaganlarga)
  13. 72 soatlik qo'shimcha chegirma taklifi (savatni tashlab ketganlarga)
  12. Xariddan 3 kun o'tgach — sharh so'rash
  5.  Kunlik avtomatik hisobot (adminga)

Bot webhook rejimida ishlagani uchun (aiohttp), bu — asyncio background task
sifatida main.py'ning on_startup'ida ishga tushiriladi.
"""

import asyncio
import logging
from datetime import datetime

import database as db
from config import APPROVAL_CHAT_ID

CHECK_INTERVAL_SECONDS = 15 * 60  # har 15 daqiqada bir tekshiradi
DAILY_REPORT_HOUR_UTC = 17  # taxminan soat 22:00 (UZB, UTC+5) atrofida


async def _check_24h_reminders(bot):
    user_ids = await db.get_users_needing_24h_reminder()
    for uid in user_ids:
        try:
            lang = await db.get_user_language(uid)
            text = (
                "Здравствуйте! Вы начали покупку книги, но ещё не отправили чек 🙂\n"
                "Если возникли вопросы — просто напишите нам здесь."
                if lang == "ru"
                else "Assalomu alaykum! Siz kitobni sotib olishni boshlagan edingiz, "
                "lekin hali chek yubormagansiz 🙂\nSavolingiz bo'lsa, shu yerga yozing."
            )
            await bot.send_message(uid, text)
            await db.mark_reminder_sent(uid)
        except Exception as e:
            logging.warning(f"24h eslatma yuborilmadi ({uid}): {e}")
            await db.mark_reminder_sent(uid)  # qayta-qayta urinib, cheksiz xato bermasligi uchun


async def _check_discount_offers(bot):
    user_ids = await db.get_users_needing_discount_offer()
    for uid in user_ids:
        try:
            lang = await db.get_user_language(uid)
            text = (
                "🎁 Специально для вас: если оформите заказ в течение 24 часов — "
                "дополнительная скидка! Напишите нам, чтобы узнать подробности."
                if lang == "ru"
                else "🎁 Aynan siz uchun: agar keyingi 24 soat ichida buyurtma bersangiz — "
                "qo'shimcha chegirma beramiz! Batafsil ma'lumot uchun shu yerga yozing."
            )
            await bot.send_message(uid, text)
            await db.mark_discount_offer_sent(uid)
        except Exception as e:
            logging.warning(f"Chegirma taklifi yuborilmadi ({uid}): {e}")
            await db.mark_discount_offer_sent(uid)


async def _check_review_requests(bot):
    user_ids = await db.get_users_needing_review_request()
    for uid in user_ids:
        try:
            lang = await db.get_user_language(uid)
            text = (
                "Как вам книга? 🙂 Будем благодарны, если поделитесь впечатлением здесь — "
                "это очень поможет нам!"
                if lang == "ru"
                else "Kitob qanday tuyildi? 🙂 Fikringizni shu yerga yozib qoldirsangiz, "
                "biz uchun juda muhim bo'lardi!"
            )
            await bot.send_message(uid, text)
            await db.mark_review_requested(uid)
        except Exception as e:
            logging.warning(f"Sharh so'rovi yuborilmadi ({uid}): {e}")
            await db.mark_review_requested(uid)


async def _check_daily_report(bot):
    if not APPROVAL_CHAT_ID:
        return
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    if now.hour < DAILY_REPORT_HOUR_UTC:
        return
    last_sent = await db.get_last_report_date()
    if last_sent == today_str:
        return  # bugun allaqachon yuborilgan

    stats = await db.get_stats()
    ab = await db.get_ab_test_stats()
    text = (
        f"📅 Kunlik hisobot ({today_str})\n\n"
        f"👥 Jami: {stats['total']}\n"
        f"📝 Lidlar: {stats['leads']}\n"
        f"💰 Xaridlar: {stats['purchased']}\n"
        f"📈 Konversiya: {stats['conversion']}%\n"
        f"🕓 Bugun start bosganlar: {stats['today']}\n\n"
        f"🔀 A/B test:\n"
        f"  A — {ab['A']['total']} ta, konversiya {ab['A']['conversion']}%\n"
        f"  B — {ab['B']['total']} ta, konversiya {ab['B']['conversion']}%"
    )
    try:
        await bot.send_message(APPROVAL_CHAT_ID, text)
        await db.set_last_report_date(today_str)
    except Exception as e:
        logging.warning(f"Kunlik hisobot yuborilmadi: {e}")


async def run_scheduler(bot):
    logging.info("🕓 Fon rejimidagi vazifalar (scheduler) ishga tushdi")
    while True:
        try:
            await _check_24h_reminders(bot)
            await _check_discount_offers(bot)
            await _check_review_requests(bot)
            await _check_daily_report(bot)
        except Exception as e:
            logging.error(f"Scheduler xatosi: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
