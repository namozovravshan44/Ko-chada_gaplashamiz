from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import LeadForm, ReceiptForm
from config import CARD_NUMBER, CARD_OWNER, BOOK_PRICE, BOOK_DISCOUNT_PRICE, BOOK_INFO_TEXT, MANAGER_CONTACT_TEXT, APPROVAL_CHAT_ID

router = Router()

DEFAULT_START_TEXT = (
    "Assalomu alaykum! 👋\n\n"
    "\"Ko'chada gaplashamiz\" — rus tilini his qilib, hayotiy suhbatlar orqali "
    "o'rganish uchun yaratilgan kitob.\n\n"
    "Bepul namuna olish yoki hoziroq sotib olish uchun quyidagi tugmalardan birini tanlang 👇"
)

RUSPEAK_WELCOME_TEXT = (
    "Assalomu alaykum! 👋\n\n"
    "Ruspeak saytida ro'yxatdan o'tganingiz uchun rahmat! 🎉\n"
    "Bonus sifatida \"Musiqa bilan rus tilini o'rganish\" darsini hoziroq yuboramiz 👇"
)


def _is_ruspeak_token(payload: str) -> bool:
    # Ruspeak lending sahifasi generatsiya qiladigan token har doim "W" bilan boshlanadi
    # (masalan: Wmt49oy1uiekzcj) — kitob boti uchun boshqa deep-link'lar bilan aralashmasin
    return bool(payload) and payload.startswith("W") and len(payload) > 5


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    await state.clear()
    payload = (command.args or "").strip()
    user = message.from_user

    # ── 4. Referal havolasi: ref_<taklif_qilgan_user_id> ──
    if payload.startswith("ref_"):
        await db.upsert_user(user.id, user.username, user.first_name)
        ref_id_str = payload[4:]
        if ref_id_str.isdigit():
            await db.set_referrer(user.id, int(ref_id_str))
        await cmd_start(message, state, bot)
        return

    if not _is_ruspeak_token(payload):
        # Tanish bo'lmagan/eski formatdagi deep-link — oddiy /start sifatida davom etamiz
        await cmd_start(message, state, bot)
        return

    await db.upsert_user(user.id, user.username, user.first_name)
    await db.save_ruspeak_lead(payload, user.id, user.username or "", user.first_name or "")

    await message.answer(RUSPEAK_WELCOME_TEXT)
    await send_ruspeak_files(bot, user.id)

    if APPROVAL_CHAT_ID:
        try:
            await bot.send_message(
                APPROVAL_CHAT_ID,
                f"📩 Yangi Ruspeak lidi botga ulandi!\n"
                f"👤 {user.full_name} (@{user.username or 'username yoq'})\n"
                f"🆔 User ID: {user.id}\n"
                f"🔗 Token: {payload}\n\n"
                f"ℹ️ Username bo'lmasa ham, shu ID orqali bog'lanish mumkin:\n"
                f"/msg {user.id} <xabar matni>",
            )
        except Exception:
            pass


async def _send_content_with_buttons(bot: Bot, user_id: int, files):
    """Fayllar/matn/rasmlarni ketma-ket yuboradi. Agar keyingi yozuv 'button' turida bo'lsa,
    uni oldingi yuborilgan xabarga tugma sifatida biriktiradi (edit_reply_markup orqali)."""
    last_message = None
    pending_kb = None

    for file_id, file_type, file_name in files:
        try:
            if file_type == "button":
                if last_message is not None:
                    if pending_kb is None:
                        pending_kb = InlineKeyboardMarkup(inline_keyboard=[])
                    pending_kb.inline_keyboard.append(
                        [InlineKeyboardButton(text=file_name, url=file_id)]
                    )
                    await last_message.edit_reply_markup(reply_markup=pending_kb)
                else:
                    # Tugmadan oldin hech narsa yuborilmagan — alohida xabar sifatida yuboramiz
                    single_kb = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text=file_name, url=file_id)]]
                    )
                    await bot.send_message(user_id, "👇", reply_markup=single_kb)
                continue

            # Yangi (button bo'lmagan) kontent — oldingi tugmalar zanjirini tozalaymiz
            pending_kb = None

            if file_type == "document":
                last_message = await bot.send_document(user_id, file_id, caption=file_name)
            elif file_type == "audio":
                last_message = await bot.send_audio(user_id, file_id, caption=file_name)
            elif file_type == "voice":
                last_message = await bot.send_voice(user_id, file_id)
            elif file_type == "video":
                last_message = await bot.send_video(user_id, file_id, caption=file_name)
            elif file_type == "photo":
                last_message = await bot.send_photo(user_id, file_id, caption=file_name or None)
            elif file_type == "text":
                last_message = await bot.send_message(user_id, file_id)
        except Exception:
            pass


async def send_ruspeak_files(bot: Bot, user_id: int):
    files = await db.get_ruspeak_files()
    if not files:
        await bot.send_message(
            user_id,
            "⚠️ Bonus dars fayli hali tizimga yuklanmagan. Tez orada operator siz bilan bog'lanadi.",
        )
        return
    await _send_content_with_buttons(bot, user_id, files)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await db.upsert_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )

    # ── Xavfsizlik: g'ayrioddiy tez-tez /start bosilishini kuzatamiz ──
    if db.check_suspicious_start(message.from_user.id):
        if APPROVAL_CHAT_ID:
            try:
                await bot.send_message(
                    APPROVAL_CHAT_ID,
                    f"⚠️ Shubhali faollik: {message.from_user.full_name} "
                    f"(ID: {message.from_user.id}) qisqa vaqt ichida /start'ni juda ko'p bosdi.",
                )
            except Exception:
                pass

    lang = await db.get_user_language(message.from_user.id)

    content = await db.get_content("start")
    text = content[1] if content and content[1] else DEFAULT_START_TEXT
    video_file_id = content[0] if content else None

    if video_file_id:
        await message.answer_video(video_file_id, caption=text, reply_markup=kb.start_menu_kb(lang))
    else:
        await message.answer(text, reply_markup=kb.start_menu_kb(lang))


@router.callback_query(F.data == "get_free_sample")
async def get_free_sample(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Ajoyib tanlov! 🎉\nBepul namunani olish uchun to'liq ism-familiyangizni yozing:"
    )
    await state.set_state(LeadForm.waiting_full_name)
    await callback.answer()


@router.message(LeadForm.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer(
        "Rahmat! Endi telefon raqamingizni yuboring 👇",
        reply_markup=kb.phone_request_kb(),
    )
    await state.set_state(LeadForm.waiting_phone)


@router.message(LeadForm.waiting_phone, F.content_type == ContentType.CONTACT)
async def process_phone_contact(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    phone = message.contact.phone_number
    await db.save_lead(message.from_user.id, data.get("full_name", ""), phone)
    await send_sample_files(bot, message.from_user.id)
    await state.clear()


@router.message(LeadForm.waiting_phone)
async def process_phone_text(message: Message, state: FSMContext, bot: Bot):
    # Agar foydalanuvchi kontakt tugmasi o'rniga qo'lda raqam yozsa ham qabul qilamiz
    data = await state.get_data()
    await db.save_lead(message.from_user.id, data.get("full_name", ""), message.text)
    await send_sample_files(bot, message.from_user.id)
    await state.clear()


async def send_sample_files(bot: Bot, user_id: int):
    await bot.send_message(user_id, "Rahmat! Namunani tayyorlab yubordik. 📚👇")

    sample_files = await db.get_sample_files()
    if not sample_files:
        await bot.send_message(
            user_id,
            "⚠️ Namuna fayllari hali tizimga yuklanmagan. Tez orada operator siz bilan bog'lanadi.",
        )
        return
    await _send_content_with_buttons(bot, user_id, sample_files)

    lang = await db.get_user_language(user_id)
    await bot.send_message(
        user_id,
        "Kitobning to'liq versiyasini olish uchun pastdagi \"Sotib olish\" tugmasini bosing."
        if lang != "ru"
        else "Нажмите кнопку \"Купить\" ниже, чтобы получить полную версию книги.",
        reply_markup=kb.start_menu_kb(lang),
    )


@router.callback_query(F.data == "my_ref_link")
async def my_ref_link(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user_id}"
    invited = await db.get_referral_count(user_id)
    purchased = await db.get_referral_purchased_count(user_id)
    lang = await db.get_user_language(user_id)
    if lang == "ru":
        text = (
            f"👥 Пригласите друга — получите бонус!\n\n"
            f"Ваша персональная ссылка:\n{link}\n\n"
            f"📊 Приглашено: {invited}\n"
            f"💰 Купили книгу: {purchased}"
        )
    else:
        text = (
            f"👥 Do'stingizni taklif qiling — bonus oling!\n\n"
            f"Sizning shaxsiy havolangiz:\n{link}\n\n"
            f"📊 Taklif qilinganlar: {invited}\n"
            f"💰 Kitob sotib olganlar: {purchased}"
        )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "toggle_lang")
async def toggle_lang(callback: CallbackQuery):
    current = await db.get_user_language(callback.from_user.id)
    new_lang = "ru" if current != "ru" else "uz"
    await db.set_user_language(callback.from_user.id, new_lang)
    confirm = "Til o'zbekchaga o'zgartirildi ✅" if new_lang == "uz" else "Язык изменён на русский ✅"
    await callback.answer(confirm, show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb.start_menu_kb(new_lang))
    except Exception:
        pass


@router.callback_query(F.data == "buy_book")
async def buy_book(callback: CallbackQuery):
    import html as _html
    user_id = callback.from_user.id
    lang = await db.get_user_language(user_id)
    price = _html.escape(await db.get_setting("book_price", BOOK_PRICE))
    discount_price = _html.escape(await db.get_setting("book_discount_price", BOOK_DISCOUNT_PRICE))
    card_number = _html.escape(await db.get_setting("card_number", CARD_NUMBER))
    card_owner = _html.escape(await db.get_setting("card_owner", CARD_OWNER))

    await db.mark_buy_clicked(user_id)  # 24/72 soatlik follow-up uchun vaqt belgilanadi
    variant = await db.get_or_assign_ab_variant(user_id)  # 10. A/B test

    if lang == "ru":
        text = (
            f"Отлично!\n\n"
            f"💰 Полная цена книги: <b>{price}</b>\n"
            f"🔥 Но если купите именно сегодня — всего за <b>{discount_price}</b>!\n\n"
            f"<b>Шаг 1.</b> Оплатите {discount_price} на карту 👇\n"
            f"{card_number}\n{card_owner}\n\n"
            f"<b>Шаг 2.</b> Отправьте нам чек об оплате"
        )
    elif variant == "B":
        # B-variant: avval kitobning qiymatini, keyin narxni ta'kidlaydi (urg'u tartibi boshqacha)
        text = (
            f"🔥 <b>6 ta hayotiy mavzu, real suhbatlar va kundalik hayotda kerak bo'ladigan "
            f"ruscha so'zlar va iboralar</b> — bularning barchasi endi sizniki bo'ladi!\n\n"
            f"💰 To'liq narxi {price} bo'lsa-da, aynan bugun — bor-yo'g'i <b>{discount_price}</b>.\n\n"
            f"<b>1-qadam.</b> Ushbu kartaga {discount_price} miqdorida to'lov qiling 👇\n"
            f"{card_number}\n{card_owner}\n\n"
            f"<b>2-qadam.</b> To'lov chekini bizga yuboring"
        )
    else:
        text = (
            f"Ajoyib!\n\n"
            f"💰 Kitobning to'liq narxi: <b>{price}</b>\n"
            f"🔥 Ammo aynan bugun sotib olsangiz — bor-yo'g'i <b>{discount_price}</b>ga qo'lga kiritasiz!\n\n"
            f"<b>1-qadam.</b> Ushbu kartaga {discount_price} miqdorida to'lov qiling 👇\n"
            f"{card_number}\n{card_owner}\n\n"
            f"<b>2-qadam.</b> To'lov chekini bizga yuboring"
        )
    await callback.message.answer(text, reply_markup=kb.buy_menu_kb(lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "send_receipt")
async def ask_receipt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("To'lov chekining skrinshotini (rasm ko'rinishida) yuboring 📎")
    await state.set_state(ReceiptForm.waiting_photo)
    await callback.answer()


@router.callback_query(F.data == "book_info")
async def book_info(callback: CallbackQuery):
    text = await db.get_setting("book_info_text", BOOK_INFO_TEXT)
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery):
    text = await db.get_setting("manager_contact_text", MANAGER_CONTACT_TEXT)
    await callback.message.answer(text)
    await callback.answer()


@router.message(ReceiptForm.waiting_photo, F.content_type == ContentType.PHOTO)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    photo_file_id = message.photo[-1].file_id
    receipt_id = await db.add_receipt(message.from_user.id, photo_file_id)

    user = message.from_user
    caption = (
        f"🧾 Yangi chek!\n"
        f"Foydalanuvchi: {user.full_name} (@{user.username or '-'})\n"
        f"ID: {user.id}"
    )
    if APPROVAL_CHAT_ID:
        await bot.send_photo(
            APPROVAL_CHAT_ID,
            photo_file_id,
            caption=caption,
            reply_markup=kb.receipt_review_kb(receipt_id),
        )

    await message.answer(
        "Chekingiz qabul qilindi ✅\nTez orada operatorlarimiz tekshirib, sizga kitobni yuboradi."
    )
    await state.clear()


@router.message(ReceiptForm.waiting_photo)
async def process_receipt_wrong_type(message: Message):
    await message.answer("Iltimos, to'lov chekining rasmini (screenshot) yuboring 📎")
