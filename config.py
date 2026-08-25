import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Vergul bilan ajratilgan Telegram user_id lar. Masalan: "123456789,987654321"
SUPER_ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("SUPER_ADMIN_IDS", "").split(",") if x.strip()
]

# To'lov chekini tasdiqlash uchun operatorlar/admin yuboriladigan guruh yoki shaxsiy chat ID
# (o'zingizning shaxsiy ID'ingizni ham shu yerga qo'yishingiz mumkin)
APPROVAL_CHAT_ID = int(os.getenv("APPROVAL_CHAT_ID", "0") or 0)

DB_PATH = os.getenv("DB_PATH", "bot_database.db")

CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0329 4328 2921")
CARD_OWNER = os.getenv("CARD_OWNER", "Muhammadbobur Mahamadjonov")
BOOK_PRICE = os.getenv("BOOK_PRICE", "196 000 so'm")
BOOK_DISCOUNT_PRICE = os.getenv("BOOK_DISCOUNT_PRICE", "57 000 so'm")

BOOK_INFO_TEXT = os.getenv(
    "BOOK_INFO_TEXT",
    "📖 Bu oddiy kitob emas!\n"
    "🔥 6 ta hayotiy mavzu, real suhbatlar va kundalik hayotda kerak bo'ladigan ruscha so'zlar va iboralar.\n"
    "❌ Zerikarli monologlar yo'q.\n"
    "💬 Faqat jonli, amaliy va hayotda ishlatiladigan nutq!\n"
    "📚 O'qing — va rus tilini real hayotda ishlata boshlang!",
)

MANAGER_CONTACT_TEXT = os.getenv(
    "MANAGER_CONTACT_TEXT",
    "Savolingiz bo'lsa shu yerga yozing, tez orada operatorlarimiz javob beradi ✍️",
)

# --- Webhook sozlamalari (Render kabi platformalar uchun) ---
# Render bu o'zgaruvchini avtomatik beradi (https://sizning-servisingiz.onrender.com)
# Agar boshqa platforma ishlatilsa, WEBHOOK_HOST'ni qo'lda .env orqali kiriting
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8080))

# ── Botdan (kodga tegmasdan) o'zgartirish mumkin bo'lgan sozlamalar ──
# key: (odam o'qiydigan nomi, boshlang'ich qiymat)
SETTINGS_META = {
    "book_price": ("Kitobning to'liq narxi", BOOK_PRICE),
    "book_discount_price": ("Bugungi chegirmali narx", BOOK_DISCOUNT_PRICE),
    "book_info_text": ("Kitob haqida ma'lumot matni", BOOK_INFO_TEXT),
    "manager_contact_text": ("Operator bilan bog'lanish matni", MANAGER_CONTACT_TEXT),
    "card_number": ("To'lov karta raqami", CARD_NUMBER),
    "card_owner": ("Karta egasi ismi", CARD_OWNER),
}
