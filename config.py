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
BOOK_PRICE = os.getenv("BOOK_PRICE", "130.000 so'm")
