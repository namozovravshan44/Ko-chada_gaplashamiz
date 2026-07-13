from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from config import SUPER_ADMIN_IDS

router = Router()


async def is_staff(user_id: int) -> bool:
    return user_id in SUPER_ADMIN_IDS or await db.is_operator(user_id)


@router.callback_query(F.data.startswith("approve_"))
async def approve_receipt(callback: CallbackQuery, bot: Bot):
    if not await is_staff(callback.from_user.id):
        await callback.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    receipt_id = int(callback.data.split("_")[1])
    receipt = await db.get_receipt(receipt_id)
    if not receipt:
        await callback.answer("Chek topilmadi.", show_alert=True)
        return

    _, user_id, status = receipt
    if status != "pending":
        await callback.answer("Bu chek allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.update_receipt_status(receipt_id, "approved", callback.from_user.id)
    await db.mark_purchased(user_id)

    await bot.send_message(
        user_id,
        "To'lovingiz tasdiqlandi! ✅\nKitobingiz uchun rahmat, materiallarni yubormoqdamiz 📚👇",
    )

    book_files = await db.get_book_files()
    if not book_files:
        await bot.send_message(
            user_id,
            "⚠️ Kitob fayllari hali tizimga yuklanmagan. Tez orada operator siz bilan bog'lanadi.",
        )
    else:
        for file_id, file_type, file_name in book_files:
            try:
                if file_type == "document":
                    await bot.send_document(user_id, file_id, caption=file_name)
                elif file_type == "audio":
                    await bot.send_audio(user_id, file_id, caption=file_name)
                elif file_type == "voice":
                    await bot.send_voice(user_id, file_id)
            except Exception:
                pass

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ TASDIQLANDI"
    )
    await callback.answer("Tasdiqlandi")


@router.callback_query(F.data.startswith("reject_"))
async def reject_receipt(callback: CallbackQuery, bot: Bot):
    if not await is_staff(callback.from_user.id):
        await callback.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    receipt_id = int(callback.data.split("_")[1])
    receipt = await db.get_receipt(receipt_id)
    if not receipt:
        await callback.answer("Chek topilmadi.", show_alert=True)
        return

    _, user_id, status = receipt
    if status != "pending":
        await callback.answer("Bu chek allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.update_receipt_status(receipt_id, "rejected", callback.from_user.id)

    await bot.send_message(
        user_id,
        "Kechirasiz, to'lov chekingizni tasdiqlay olmadik ❌\n"
        "Iltimos, to'lovni tekshirib, chekni qaytadan yuboring yoki menejerga yozing.",
    )
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ RAD ETILDI"
    )
    await callback.answer("Rad etildi")


@router.message(Command("leads"))
async def cmd_leads(message: Message):
    if not await is_staff(message.from_user.id):
        return
    stats = await db.get_stats()
    await message.answer(
        f"📊 Qisqacha statistika:\n\n"
        f"👥 Jami start bosganlar: {stats['total']}\n"
        f"📝 Lead qoldirganlar (bepul namuna so'raganlar): {stats['leads']}\n"
        f"💰 Xarid qilganlar: {stats['purchased']}\n"
        f"⏳ Ko'rib chiqilmagan cheklar: {stats['pending_receipts']}"
    )
