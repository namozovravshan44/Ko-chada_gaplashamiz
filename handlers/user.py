from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import LeadForm, ReceiptForm
from config import CARD_NUMBER, CARD_OWNER, BOOK_PRICE, APPROVAL_CHAT_ID

router = Router()

DEFAULT_START_TEXT = (
    "Assalomu alaykum! 👋\n\n"
    "\"Ko'chada gaplashamiz\" — rus tilini his qilib, hayotiy suhbatlar orqali "
    "o'rganish uchun yaratilgan kitob.\n\n"
    "Bepul namuna olish yoki hoziroq sotib olish uchun quyidagi tugmalardan birini tanlang 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_new = await db.upsert_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )

    content = await db.get_content("start")
    text = content[1] if content and content[1] else DEFAULT_START_TEXT
    video_file_id = content[0] if content else None

    if video_file_id:
        await message.answer_video(video_file_id, caption=text, reply_markup=kb.start_menu_kb())
    else:
        await message.answer(text, reply_markup=kb.start_menu_kb())


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
async def process_phone_contact(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number
    await db.save_lead(message.from_user.id, data.get("full_name", ""), phone)
    await message.answer(
        "Rahmat! Namunani tayyorlab yubordik. 📚\n\n"
        "Kitobning to'liq versiyasini olish uchun pastdagi \"Sotib olish\" tugmasini bosing.",
        reply_markup=kb.start_menu_kb(),
    )
    await state.clear()


@router.message(LeadForm.waiting_phone)
async def process_phone_text(message: Message, state: FSMContext):
    # Agar foydalanuvchi kontakt tugmasi o'rniga qo'lda raqam yozsa ham qabul qilamiz
    data = await state.get_data()
    await db.save_lead(message.from_user.id, data.get("full_name", ""), message.text)
    await message.answer(
        "Rahmat! Namunani tayyorlab yubordik. 📚\n\n"
        "Kitobning to'liq versiyasini olish uchun pastdagi \"Sotib olish\" tugmasini bosing.",
        reply_markup=kb.start_menu_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "buy_book")
async def buy_book(callback: CallbackQuery):
    text = (
        f"Ajoyib!\n\n"
        f"1-qadam. Ushbu kartaga {BOOK_PRICE} miqdorida to'lov qiling 👇\n"
        f"{CARD_NUMBER}\n{CARD_OWNER}\n\n"
        f"2-qadam. To'lov chekini bizga yuboring"
    )
    await callback.message.answer(text, reply_markup=kb.buy_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "send_receipt")
async def ask_receipt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("To'lov chekining skrinshotini (rasm ko'rinishida) yuboring 📎")
    await state.set_state(ReceiptForm.waiting_photo)
    await callback.answer()


@router.callback_query(F.data == "book_info")
async def book_info(callback: CallbackQuery):
    await callback.message.answer(
        "📖 Kitobda 24 ta hayotiy mavzu, real suhbatlar, sifatli audio va rasmlar mavjud. "
        "Zerikarli monolog va foydasiz mavzular yo'q — faqat kundalik hayotda kerak bo'ladigan amaliy nutq."
    )
    await callback.answer()


@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery):
    await callback.message.answer(
        "Savolingiz bo'lsa shu yerga yozing, tez orada operatorlarimiz javob beradi ✍️"
    )
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
