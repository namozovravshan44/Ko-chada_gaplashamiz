import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

import database as db
from states import Broadcast, AdminContent, BookUpload
from config import SUPER_ADMIN_IDS

router = Router()


def is_super_admin(user_id: int) -> bool:
    return user_id in SUPER_ADMIN_IDS


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    stats = await db.get_stats()
    await message.answer(
        f"📊 To'liq statistika:\n\n"
        f"👥 Jami start bosganlar: {stats['total']}\n"
        f"📝 Lead qoldirganlar: {stats['leads']}\n"
        f"💰 Xarid qilganlar: {stats['purchased']}\n"
        f"⏳ Ko'rib chiqilmagan cheklar: {stats['pending_receipts']}"
    )


@router.message(Command("export"))
async def cmd_export(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    csv_buf = await db.export_users_csv()
    await message.answer_document(
        BufferedInputFile(csv_buf.read(), filename="users.csv"),
        caption="Barcha foydalanuvchilar ro'yxati",
    )


@router.message(Command("addoperator"))
async def cmd_add_operator(message: Message, command: CommandObject):
    if not is_super_admin(message.from_user.id):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Foydalanish: /addoperator <user_id>\nMasalan: /addoperator 123456789")
        return
    op_id = int(command.args.strip())
    await db.add_operator(op_id)
    await message.answer(f"✅ {op_id} operator sifatida qo'shildi.")


@router.message(Command("removeoperator"))
async def cmd_remove_operator(message: Message, command: CommandObject):
    if not is_super_admin(message.from_user.id):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Foydalanish: /removeoperator <user_id>")
        return
    op_id = int(command.args.strip())
    await db.remove_operator(op_id)
    await message.answer(f"❌ {op_id} operatorlar ro'yxatidan o'chirildi.")


@router.message(Command("operators"))
async def cmd_list_operators(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    ops = await db.list_operators()
    if not ops:
        await message.answer("Hozircha operatorlar yo'q.")
        return
    text = "👤 Operatorlar ro'yxati:\n\n" + "\n".join(f"- {op_id}" for op_id, _ in ops)
    await message.answer(text)


# ---------- Broadcast (barchaga xabar yuborish) ----------

@router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    await message.answer(
        "Barchaga yubormoqchi bo'lgan xabaringizni yuboring "
        "(matn, rasm yoki video bo'lishi mumkin). Bekor qilish uchun /cancel yozing."
    )
    await state.set_state(Broadcast.waiting_message)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(Broadcast.waiting_message)
async def cmd_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_super_admin(message.from_user.id):
        return
    await state.clear()
    user_ids = await db.get_all_user_ids()
    sent, failed = 0, 0

    status_msg = await message.answer(f"Yuborilmoqda... 0/{len(user_ids)}")

    for i, uid in enumerate(user_ids, start=1):
        try:
            await message.copy_to(uid)
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            await asyncio.sleep(1)  # Telegram limitlariga tushib qolmaslik uchun
            await status_msg.edit_text(f"Yuborilmoqda... {i}/{len(user_ids)}")

    await status_msg.edit_text(f"✅ Broadcast tugadi.\nYuborildi: {sent}\nXato: {failed}")


# ---------- /start kontentini yangilash ----------

@router.message(Command("setstart"))
async def cmd_setstart_start(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    await message.answer(
        "Yangi /start videoni caption (matn) bilan birga yuboring.\n"
        "Agar faqat matnni o'zgartirmoqchi bo'lsangiz, videosiz matn yuboring."
    )
    await state.set_state(AdminContent.waiting_new_start_video)


@router.message(AdminContent.waiting_new_start_video, F.video)
async def cmd_setstart_video(message: Message, state: FSMContext):
    await db.set_content("start", message.video.file_id, message.caption or "")
    await message.answer("✅ /start kontenti (video + matn) yangilandi.")
    await state.clear()


@router.message(AdminContent.waiting_new_start_video)
async def cmd_setstart_text(message: Message, state: FSMContext):
    existing = await db.get_content("start")
    video_id = existing[0] if existing else None
    await db.set_content("start", video_id, message.text or "")
    await message.answer("✅ /start matni yangilandi.")
    await state.clear()


# ---------- Kitob fayllari (PDF/audio) ni yuklash ----------

@router.message(Command("setbook"))
async def cmd_setbook_start(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    await db.clear_book_files()
    await message.answer(
        "📚 Kitob fayllarini yuboring: PDF (dokument sifatida) va audio fayllarni "
        "birma-bir yuboraverning.\n\n"
        "Barchasini yuborib bo'lgach, /donebook deb yozing."
    )
    await state.set_state(BookUpload.collecting)


@router.message(BookUpload.collecting, F.document)
async def cmd_setbook_doc(message: Message):
    name = message.document.file_name or "kitob.pdf"
    await db.add_book_file(message.document.file_id, "document", name)
    await message.answer(f"✅ Qo'shildi: {name}")


@router.message(BookUpload.collecting, F.audio)
async def cmd_setbook_audio(message: Message):
    name = message.audio.file_name or (message.audio.title or "audio.mp3")
    await db.add_book_file(message.audio.file_id, "audio", name)
    await message.answer(f"✅ Audio qo'shildi: {name}")


@router.message(BookUpload.collecting, F.voice)
async def cmd_setbook_voice(message: Message):
    await db.add_book_file(message.voice.file_id, "voice", "ovozli xabar")
    await message.answer("✅ Ovozli xabar qo'shildi")


@router.message(Command("donebook"))
async def cmd_setbook_done(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    files = await db.get_book_files()
    await state.clear()
    await message.answer(f"✅ Tugadi! Jami {len(files)} ta fayl saqlandi va endi to'lov tasdiqlanganda avtomatik yuboriladi.")


@router.message(Command("bookfiles"))
async def cmd_bookfiles(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    files = await db.get_book_files()
    if not files:
        await message.answer("Hozircha kitob fayllari yuklanmagan. /setbook orqali yuklang.")
        return
    text = "📚 Saqlangan kitob fayllari:\n\n" + "\n".join(
        f"- ({ftype}) {fname}" for _, ftype, fname in files
    )
    await message.answer(text)


@router.message(Command("help"))
@router.message(Command("adminhelp"))
async def cmd_admin_help(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    await message.answer(
        "👑 Super admin buyruqlari:\n\n"
        "/stats — statistika\n"
        "/export — foydalanuvchilar ro'yxatini CSV holida olish\n"
        "/broadcast — barchaga xabar yuborish\n"
        "/setstart — /start videosi va matnini yangilash\n"
        "/setbook — kitob PDF/audio fayllarini yuklash (tugatgach /donebook)\n"
        "/bookfiles — yuklangan kitob fayllari ro'yxati\n"
        "/addoperator <id> — operator qo'shish\n"
        "/removeoperator <id> — operatorni o'chirish\n"
        "/operators — operatorlar ro'yxati\n\n"
        "👤 Operator buyrug'i:\n"
        "/leads — qisqacha statistika"
    )
