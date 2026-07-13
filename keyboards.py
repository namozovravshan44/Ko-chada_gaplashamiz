from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def start_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Bepul namuna olish", callback_data="get_free_sample")
    kb.button(text="💳 Sotib olish", callback_data="buy_book")
    kb.adjust(1)
    return kb.as_markup()


def buy_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Chekni yuborish", callback_data="send_receipt")
    kb.button(text="ℹ️ Kitob haqida to'liq ma'lumot", callback_data="book_info")
    kb.button(text="✍️ Menejerga yozish", callback_data="contact_manager")
    kb.adjust(1)
    return kb.as_markup()


def phone_request_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Raqamni yuborish", request_contact=True)
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def receipt_review_kb(receipt_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"approve_{receipt_id}")
    kb.button(text="❌ Rad etish", callback_data=f"reject_{receipt_id}")
    kb.adjust(2)
    return kb.as_markup()
