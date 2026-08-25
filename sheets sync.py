"""
Ruspeak sayti orqali kelgan lidlarni alohida Google Sheet'ga yozib turadi.
Agar RUSPEAK_SHEET_URL sozlanmagan bo'lsa — jim o'tkazib yuboriladi (bot ishlashda davom etadi).
Sheet ulanishida vaqtinchalik muammo bo'lsa ham, bu HECH QACHON botning asosiy
ishlashiga (mijozga xabar yuborishga) xalaqit bermaydi — barcha xatolar yutiladi.
"""

import logging
import aiohttp

from config import RUSPEAK_SHEET_URL

TIMEOUT = aiohttp.ClientTimeout(total=8)


async def _post(payload: dict):
    if not RUSPEAK_SHEET_URL:
        return
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(RUSPEAK_SHEET_URL, json=payload) as resp:
                await resp.text()
    except Exception as e:
        logging.warning(f"Ruspeak Sheet sinxronizatsiyasi muvaffaqiyatsiz: {e}")


async def sync_upsert_lead(token: str, username: str, user_id: int, first_name: str, linked_at: str):
    await _post({
        "action": "upsert_lead",
        "token": token,
        "username": username,
        "user_id": user_id,
        "first_name": first_name,
        "linked_at": linked_at,
        "purchased": False,
        "purchased_at": "",
    })


async def sync_mark_purchased(user_id: int, purchased_at: str):
    await _post({
        "action": "mark_purchased",
        "user_id": user_id,
        "purchased_at": purchased_at,
    })
