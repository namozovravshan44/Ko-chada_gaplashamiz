from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def start_menu_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if lang == "ru":
        kb.button(text="🎁 Получить бесплатный образец", callback_data="get_free_sample")
        kb.button(text="💳 Купить", callback_data="buy_book")
        kb.button(text="👥 Пригласить друга", callback_data="my_ref_link")
        kb.button(text="🌍 O'zbekcha / Русский", callback_data="toggle_lang")
    else:
        kb.button(text="🎁 Bepul namuna olish", callback_data="get_free_sample")
        kb.button(text="💳 Sotib olish", callback_data="buy_book")
        kb.button(text="👥 Do'stni taklif qilish", callback_data="my_ref_link")
        kb.button(text="🌍 O'zbekcha / Русский", callback_data="toggle_lang")
    kb.adjust(1)
    return kb.as_markup()


def buy_menu_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if lang == "ru":
        kb.button(text="✅ Отправить чек", callback_data="send_receipt")
        kb.button(text="ℹ️ Подробнее о книге", callback_data="book_info")
        kb.button(text="✍️ Написать менеджеру", callback_data="contact_manager")
    else:
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


# ---------- Admin panel (buyruq yozmasdan, tugma orqali boshqarish) ----------

def panel_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Narxlar va matnlar", callback_data="panel:prices")
    kb.button(text="📊 Statistika", callback_data="panel:stats")
    kb.button(text="📥 Excel/CSV eksport", callback_data="panel:export")
    kb.button(text="📢 Xabar yuborish", callback_data="panel:broadcast")
    kb.button(text="📁 Fayllar", callback_data="panel:files")
    kb.button(text="👥 Operatorlar", callback_data="panel:operators")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def panel_back_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Bosh menyu", callback_data="panel:main")
    return kb.as_markup()


def broadcast_segment_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Barchaga", callback_data="bcast_seg:all")
    kb.button(text="🛒 Sotib olmaganlarga", callback_data="bcast_seg:not_purchased")
    kb.button(text="🎓 Ruspeak lidlariga", callback_data="bcast_seg:ruspeak")
    kb.button(text="❌ Bekor qilish", callback_data="bcast_seg:cancel")
    kb.adjust(1)
    return kb.as_markup()


def settings_edit_kb(settings_meta: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, (label, _default) in settings_meta.items():
        kb.button(text=f"✏️ {label}", callback_data=f"edit_setting:{key}")
    kb.button(text="🔙 Bosh menyu", callback_data="panel:main")
    kb.adjust(1)
    return kb.as_markup()
