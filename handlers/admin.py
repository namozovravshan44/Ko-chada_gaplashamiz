import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import Broadcast, AdminContent, BookUpload, SampleUpload, RuspeakUpload, SettingEdit, BroadcastPanel
from config import SUPER_ADMIN_IDS, SETTINGS_META

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


# ---------- Bepul namuna fayllarini yuklash ----------

@router.message(Command("setsample"))
async def cmd_setsample_start(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    await db.clear_sample_files()
    await message.answer(
        "🎁 Bepul namuna fayllarini yuboring (PDF, audio, video, rasm yoki oddiy matn).\n\n"
        "🔗 Tugma-havola qo'shish uchun shu formatda yozing (bosilganda avtomatik o'sha havolaga o'tadi):\n"
        "Tugma: Kanalga o'tish | https://t.me/kanal\n"
        "(bu tugma o'zidan oldin yuborilgan fayl/matnga biriktiriladi)\n\n"
        "Barchasini yuborib bo'lgach, /donesample deb yozing."
    )
    await state.set_state(SampleUpload.collecting)


@router.message(SampleUpload.collecting, F.document)
async def cmd_setsample_doc(message: Message):
    name = message.document.file_name or "namuna.pdf"
    await db.add_sample_file(message.document.file_id, "document", name)
    await message.answer(f"✅ Qo'shildi: {name}")


@router.message(SampleUpload.collecting, F.audio)
async def cmd_setsample_audio(message: Message):
    name = message.audio.file_name or (message.audio.title or "namuna_audio.mp3")
    await db.add_sample_file(message.audio.file_id, "audio", name)
    await message.answer(f"✅ Audio qo'shildi: {name}")


@router.message(SampleUpload.collecting, F.voice)
async def cmd_setsample_voice(message: Message):
    await db.add_sample_file(message.voice.file_id, "voice", "ovozli xabar")
    await message.answer("✅ Ovozli xabar qo'shildi")


@router.message(SampleUpload.collecting, F.video)
async def cmd_setsample_video(message: Message):
    name = "namuna_video.mp4"
    await db.add_sample_file(message.video.file_id, "video", name)
    await message.answer(f"✅ Video qo'shildi: {name}")


@router.message(SampleUpload.collecting, F.photo)
async def cmd_setsample_photo(message: Message):
    photo = message.photo[-1]
    caption = message.caption or ""
    await db.add_sample_file(photo.file_id, "photo", caption)
    await message.answer("✅ Rasm qo'shildi" + (" (izoh bilan)" if caption else ""))


import re

BUTTON_PATTERN = re.compile(r'^\s*tugma\s*:\s*(.+?)\s*\|\s*(https?://\S+)\s*$', re.IGNORECASE)


def parse_button(text: str):
    """'Tugma: Matn | https://havola.com' formatini aniqlaydi. Mos kelmasa None qaytaradi."""
    m = BUTTON_PATTERN.match(text)
    if not m:
        return None
    label, url = m.group(1).strip(), m.group(2).strip()
    return label, url


@router.message(SampleUpload.collecting, F.text & ~F.text.startswith("/"))
async def cmd_setsample_text(message: Message):
    btn = parse_button(message.text)
    if btn:
        label, url = btn
        await db.add_sample_file(url, "button", label)
        await message.answer(f"🔗 Tugma qo'shildi: \"{label}\" → {url}\n\n(bu tugma o'zidan oldingi kontentga biriktiriladi)")
        return
    await db.add_sample_file(message.text, "text", "")
    await message.answer("✅ Matn qo'shildi")


@router.message(Command("donesample"))
async def cmd_setsample_done(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    files = await db.get_sample_files()
    await state.clear()
    await message.answer(f"✅ Tugadi! Jami {len(files)} ta namuna fayli saqlandi.")


@router.message(Command("samplefiles"))
async def cmd_samplefiles(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    files = await db.get_sample_files()
    if not files:
        await message.answer("Hozircha namuna fayllari yuklanmagan. /setsample orqali yuklang.")
        return
    text = "🎁 Saqlangan namuna fayllari:\n\n" + "\n".join(
        f"- ({ftype}) {fname}" for _, ftype, fname in files
    )
    await message.answer(text)


# ---------- Ruspeak bonus fayllarini yuklash ----------

@router.message(Command("setruspeak"))
async def cmd_setruspeak_start(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    await db.clear_ruspeak_files()
    await message.answer(
        "🎵 Ruspeak bonus dars fayllarini yuboring (audio, video, rasm, PDF yoki oddiy matn).\n\n"
        "🔗 Tugma-havola qo'shish uchun shu formatda yozing (bosilganda avtomatik o'sha havolaga o'tadi):\n"
        "Tugma: Saytga o'tish | https://ruspeak.uz\n"
        "(bu tugma o'zidan oldin yuborilgan fayl/matnga biriktiriladi)\n\n"
        "Bular Ruspeak saytidan ro'yxatdan o'tib botga kirgan mijozlarga /start bosishi bilanoq "
        "avtomatik yuboriladi.\n\n"
        "Barchasini yuborib bo'lgach, /doneruspeak deb yozing."
    )
    await state.set_state(RuspeakUpload.collecting)


@router.message(RuspeakUpload.collecting, F.document)
async def cmd_setruspeak_doc(message: Message):
    name = message.document.file_name or "ruspeak_dars.pdf"
    await db.add_ruspeak_file(message.document.file_id, "document", name)
    await message.answer(f"✅ Qo'shildi: {name}")


@router.message(RuspeakUpload.collecting, F.audio)
async def cmd_setruspeak_audio(message: Message):
    name = message.audio.file_name or (message.audio.title or "ruspeak_dars.mp3")
    await db.add_ruspeak_file(message.audio.file_id, "audio", name)
    await message.answer(f"✅ Audio qo'shildi: {name}")


@router.message(RuspeakUpload.collecting, F.voice)
async def cmd_setruspeak_voice(message: Message):
    await db.add_ruspeak_file(message.voice.file_id, "voice", "ovozli xabar")
    await message.answer("✅ Ovozli xabar qo'shildi")


@router.message(RuspeakUpload.collecting, F.video)
async def cmd_setruspeak_video(message: Message):
    name = "ruspeak_dars.mp4"
    await db.add_ruspeak_file(message.video.file_id, "video", name)
    await message.answer(f"✅ Video qo'shildi: {name}")


@router.message(RuspeakUpload.collecting, F.photo)
async def cmd_setruspeak_photo(message: Message):
    photo = message.photo[-1]  # eng katta o'lchamdagi versiyasi
    caption = message.caption or ""
    await db.add_ruspeak_file(photo.file_id, "photo", caption)
    await message.answer("✅ Rasm qo'shildi" + (f" (izoh bilan)" if caption else ""))


@router.message(RuspeakUpload.collecting, F.text & ~F.text.startswith("/"))
async def cmd_setruspeak_text(message: Message):
    btn = parse_button(message.text)
    if btn:
        label, url = btn
        await db.add_ruspeak_file(url, "button", label)
        await message.answer(f"🔗 Tugma qo'shildi: \"{label}\" → {url}\n\n(bu tugma o'zidan oldingi kontentga biriktiriladi)")
        return
    await db.add_ruspeak_file(message.text, "text", "")
    await message.answer("✅ Matn qo'shildi")


@router.message(Command("doneruspeak"))
async def cmd_setruspeak_done(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    files = await db.get_ruspeak_files()
    await state.clear()
    await message.answer(f"✅ Tugadi! Jami {len(files)} ta Ruspeak bonus fayli saqlandi.")


@router.message(Command("ruspeakfiles"))
async def cmd_ruspeakfiles(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    files = await db.get_ruspeak_files()
    if not files:
        await message.answer("Hozircha Ruspeak bonus fayllari yuklanmagan. /setruspeak orqali yuklang.")
        return
    text = "🎵 Saqlangan Ruspeak bonus fayllari:\n\n" + "\n".join(
        f"- ({ftype}) {fname}" for _, ftype, fname in files
    )
    await message.answer(text)


# ---------- Umumiy sozlamalar: narx, matnlar, karta va h.k. ----------

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    saved = await db.get_all_settings()
    lines = ["⚙️ Botdagi o'zgartirish mumkin bo'lgan sozlamalar:\n"]
    for key, (label, default) in SETTINGS_META.items():
        current = saved.get(key, default)
        lines.append(f"🔑 `{key}` — {label}\n   Hozirgi qiymat: {current}\n")
    lines.append(
        "\nO'zgartirish uchun:\n"
        "/set <key> <yangi qiymat>\n\n"
        "Masalan:\n"
        "/set book_discount_price 45 000 so'm"
    )
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("set"))
async def cmd_set(message: Message, command: CommandObject):
    if not is_super_admin(message.from_user.id):
        return
    args = (command.args or "").strip()
    if not args or " " not in args:
        await message.answer(
            "Foydalanish: /set <key> <yangi qiymat>\n"
            "Mavjud kalitlarni ko'rish uchun /settings yozing."
        )
        return

    key, value = args.split(" ", 1)
    key = key.strip()
    value = value.strip()

    if key not in SETTINGS_META:
        await message.answer(
            f"❌ Noma'lum kalit: `{key}`\n\nMavjud kalitlarni ko'rish uchun /settings yozing.",
            parse_mode="Markdown",
        )
        return

    await db.set_setting(key, value)
    label = SETTINGS_META[key][0]
    await message.answer(f"✅ Yangilandi: {label}\n\nYangi qiymat: {value}")


# ---------- Username'i yo'q mijozlar bilan ishlash ----------

@router.message(Command("msg"))
async def cmd_msg_user(message: Message, command: CommandObject, bot: Bot):
    if not is_super_admin(message.from_user.id):
        return
    args = (command.args or "").strip()
    if not args or " " not in args:
        await message.answer("Foydalanish: /msg <user_id> <xabar matni>\n\nMasalan: /msg 999888777 Assalomu alaykum, sizga yordam bera olamanmi?")
        return

    user_id_str, text = args.split(" ", 1)
    try:
        user_id = int(user_id_str.strip())
    except ValueError:
        await message.answer("❌ user_id raqam bo'lishi kerak.")
        return

    try:
        await bot.send_message(user_id, text.strip())
        await message.answer("✅ Xabar yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Yubora olmadim: {e}\n\n(Mijoz botni bloklagan yoki hali /start bosmagan bo'lishi mumkin)")


@router.message(Command("lead"))
async def cmd_lead_lookup(message: Message, command: CommandObject):
    if not is_super_admin(message.from_user.id):
        return
    token = (command.args or "").strip()
    if not token:
        await message.answer("Foydalanish: /lead <token>\n\nMasalan: /lead Wmt49oy1uiekzcj")
        return

    lead = await db.get_ruspeak_lead(token)
    if not lead:
        await message.answer("❌ Bunday token bilan lid topilmadi.")
        return

    tok, user_id, username, first_name, linked_at = lead
    await message.answer(
        f"🔗 Token: {tok}\n"
        f"👤 Ism: {first_name or '-'}\n"
        f"📛 Username: @{username or 'yoq'}\n"
        f"🆔 User ID: {user_id}\n"
        f"🕓 Ulangan vaqt: {linked_at}\n\n"
        f"Bog'lanish uchun: /msg {user_id} <xabar>"
    )


@router.message(Command("help"))
@router.message(Command("adminhelp"))
async def cmd_admin_help(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    await message.answer(
        "👑 Super admin buyruqlari:\n\n"
        "🎛 /panel — barcha funksiyalarni TUGMALAR orqali boshqarish (tavsiya etiladi!)\n\n"
        "Quyidagilar — /panel ichida ham mavjud, xohlasangiz alohida ham yozishingiz mumkin:\n"
        "/stats — statistika\n"
        "/export — foydalanuvchilar ro'yxatini CSV holida olish\n"
        "/broadcast — barchaga xabar yuborish\n"
        "/setstart — /start videosi va matnini yangilash\n"
        "/setbook — kitob PDF/audio fayllarini yuklash (tugatgach /donebook)\n"
        "/bookfiles — yuklangan kitob fayllari ro'yxati\n"
        "/setsample — bepul namuna fayllarini yuklash (tugatgach /donesample)\n"
        "/samplefiles — yuklangan namuna fayllari ro'yxati\n"
        "/setruspeak — Ruspeak bonus dars fayllarini yuklash (tugatgach /doneruspeak)\n"
        "/ruspeakfiles — yuklangan Ruspeak bonus fayllari ro'yxati\n"
        "/settings — narx, matn va boshqa sozlamalar ro'yxati\n"
        "/set <key> <qiymat> — sozlamani o'zgartirish (masalan: /set book_discount_price 45 000 so'm)\n"
        "/lead <token> — token orqali Ruspeak lidi ma'lumotini ko'rish\n"
        "/msg <user_id> <xabar> — mijozga botdan to'g'ridan-to'g'ri xabar yuborish (username bo'lmasa ham ishlaydi)\n"
        "/addoperator <id> — operator qo'shish\n"
        "/removeoperator <id> — operatorni o'chirish\n"
        "/operators — operatorlar ro'yxati\n\n"
        "👤 Operator buyrug'i:\n"
        "/leads — qisqacha statistika"
    )


# ══════════════════════════════════════════════════════════════════
#  INLINE PANEL — botdan chiqmay, tugmalar orqali boshqarish
# ══════════════════════════════════════════════════════════════════

async def _stats_text() -> str:
    s = await db.get_stats()
    ab = await db.get_ab_test_stats()
    return (
        f"📊 Statistika\n\n"
        f"👥 Jami start bosganlar: {s['total']}\n"
        f"📝 Lead qoldirganlar: {s['leads']}\n"
        f"💰 Xarid qilganlar: {s['purchased']}\n"
        f"📈 Konversiya: {s['conversion']}%\n"
        f"⏳ Ko'rib chiqilmagan cheklar: {s['pending_receipts']}\n\n"
        f"🕓 Bugun: {s['today']}\n"
        f"📅 So'nggi 7 kun: {s['week']}\n"
        f"🗓 So'nggi 30 kun: {s['month']}\n\n"
        f"🔀 A/B test (sotuv matni):\n"
        f"  Variant A — {ab['A']['total']} ta, konversiya {ab['A']['conversion']}%\n"
        f"  Variant B — {ab['B']['total']} ta, konversiya {ab['B']['conversion']}%"
    )


async def _prices_text() -> str:
    saved = await db.get_all_settings()
    lines = ["💰 Hozirgi narx va matnlar:\n"]
    for key, (label, default) in SETTINGS_META.items():
        current = saved.get(key, default)
        lines.append(f"• {label}: {current}")
    lines.append("\nO'zgartirish uchun pastdagi tugmalardan birini bosing 👇")
    return "\n".join(lines)


@router.message(Command("panel"))
async def cmd_panel(message: Message):
    if not is_super_admin(message.from_user.id):
        return
    await message.answer("🎛 Boshqaruv paneli", reply_markup=kb.panel_main_kb())


@router.callback_query(F.data == "panel:main")
async def panel_main(callback: CallbackQuery, state: FSMContext):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text("🎛 Boshqaruv paneli", reply_markup=kb.panel_main_kb())
    await callback.answer()


@router.callback_query(F.data == "panel:stats")
async def panel_stats(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.message.edit_text(await _stats_text(), reply_markup=kb.panel_back_kb())
    await callback.answer()


@router.callback_query(F.data == "panel:export")
async def panel_export(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    csv_buf = await db.export_users_csv()
    await callback.message.answer_document(
        BufferedInputFile(csv_buf.read(), filename="users.csv"),
        caption="📥 Barcha foydalanuvchilar ro'yxati",
        reply_markup=kb.panel_back_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "panel:files")
async def panel_files(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    sample = await db.get_sample_files()
    ruspeak = await db.get_ruspeak_files()
    text = (
        f"📁 Fayllar holati\n\n"
        f"🎁 Bepul namuna: {len(sample)} ta fayl\n"
        f"🎵 Ruspeak bonus: {len(ruspeak)} ta fayl\n\n"
        f"Yangilash uchun:\n"
        f"/setsample — namuna fayllarini qayta yuklash\n"
        f"/setruspeak — Ruspeak bonus fayllarini qayta yuklash"
    )
    await callback.message.edit_text(text, reply_markup=kb.panel_back_kb())
    await callback.answer()


@router.callback_query(F.data == "panel:operators")
async def panel_operators(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    ops = await db.list_operators()
    if ops:
        text = "👥 Operatorlar:\n\n" + "\n".join(f"- {op_id}" for op_id, _ in ops)
    else:
        text = "👥 Hozircha operatorlar yo'q."
    text += "\n\nQo'shish: /addoperator <id>\nO'chirish: /removeoperator <id>"
    await callback.message.edit_text(text, reply_markup=kb.panel_back_kb())
    await callback.answer()


@router.callback_query(F.data == "panel:prices")
async def panel_prices(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.message.edit_text(await _prices_text(), reply_markup=kb.settings_edit_kb(SETTINGS_META))
    await callback.answer()


@router.callback_query(F.data.startswith("edit_setting:"))
async def panel_edit_setting(callback: CallbackQuery, state: FSMContext):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    key = callback.data.split(":", 1)[1]
    if key not in SETTINGS_META:
        await callback.answer("Noma'lum sozlama", show_alert=True)
        return
    label = SETTINGS_META[key][0]
    await state.update_data(setting_key=key)
    await state.set_state(SettingEdit.waiting_value)
    await callback.message.edit_text(
        f"✏️ {label}\n\nYangi qiymatini yozib yuboring (yoki /cancel):"
    )
    await callback.answer()


@router.message(SettingEdit.waiting_value)
async def panel_setting_value(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    data = await state.get_data()
    key = data.get("setting_key")
    await state.clear()
    if not key or key not in SETTINGS_META:
        await message.answer("Xatolik yuz berdi, qaytadan /panel orqali urinib ko'ring.")
        return
    await db.set_setting(key, message.text.strip())
    label = SETTINGS_META[key][0]
    await message.answer(f"✅ Yangilandi: {label}\n\nYangi qiymat: {message.text.strip()}", reply_markup=kb.panel_back_kb())


# ---------- Panel orqali segmentlangan xabar yuborish ----------

@router.callback_query(F.data == "panel:broadcast")
async def panel_broadcast(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.message.edit_text(
        "📢 Kimlarga xabar yuborilsin?", reply_markup=kb.broadcast_segment_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bcast_seg:"))
async def panel_broadcast_segment(callback: CallbackQuery, state: FSMContext):
    if not is_super_admin(callback.from_user.id):
        await callback.answer()
        return
    segment = callback.data.split(":", 1)[1]
    if segment == "cancel":
        await callback.message.edit_text("🎛 Boshqaruv paneli", reply_markup=kb.panel_main_kb())
        await callback.answer()
        return

    await state.update_data(bcast_segment=segment)
    await state.set_state(BroadcastPanel.waiting_message)
    await callback.message.edit_text(
        "✍️ Endi yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm yoki video). Bekor qilish: /cancel"
    )
    await callback.answer()


@router.message(BroadcastPanel.waiting_message)
async def panel_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_super_admin(message.from_user.id):
        return
    data = await state.get_data()
    segment = data.get("bcast_segment", "all")
    await state.clear()

    if segment == "not_purchased":
        user_ids = await db.get_not_purchased_user_ids()
    elif segment == "ruspeak":
        user_ids = await db.get_ruspeak_lead_user_ids()
    else:
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
            await asyncio.sleep(1)
            await status_msg.edit_text(f"Yuborilmoqda... {i}/{len(user_ids)}")

    await status_msg.edit_text(
        f"✅ Broadcast tugadi (segment: {segment}).\nYuborildi: {sent}\nXato: {failed}",
        reply_markup=kb.panel_back_kb(),
    )
