import aiosqlite
import csv
import io
from datetime import datetime, timedelta
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    full_name TEXT,
    phone TEXT,
    started_at TEXT,
    lead_captured INTEGER DEFAULT 0,
    purchased INTEGER DEFAULT 0,
    language TEXT DEFAULT 'uz',
    referred_by INTEGER,
    buy_clicked_at TEXT,
    reminder_24h_sent INTEGER DEFAULT 0,
    discount_offer_sent INTEGER DEFAULT 0,
    purchased_at TEXT,
    review_requested INTEGER DEFAULT 0,
    ab_variant TEXT
);

CREATE TABLE IF NOT EXISTS operators (
    user_id INTEGER PRIMARY KEY,
    role TEXT DEFAULT 'operator',
    added_at TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    photo_file_id TEXT,
    status TEXT DEFAULT 'pending',
    reviewed_by INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_content (
    key TEXT PRIMARY KEY,
    video_file_id TEXT,
    text TEXT
);

CREATE TABLE IF NOT EXISTS book_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    file_type TEXT,
    file_name TEXT
);

CREATE TABLE IF NOT EXISTS sample_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    file_type TEXT,
    file_name TEXT
);

CREATE TABLE IF NOT EXISTS ruspeak_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    file_type TEXT,
    file_name TEXT
);

CREATE TABLE IF NOT EXISTS ruspeak_leads (
    token TEXT PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    linked_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

        # Mavjud (eski) bazalarda quyidagi ustunlar bo'lmasligi mumkin — xavfsiz qo'shamiz
        migrations = [
            "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'uz'",
            "ALTER TABLE users ADD COLUMN referred_by INTEGER",
            "ALTER TABLE users ADD COLUMN buy_clicked_at TEXT",
            "ALTER TABLE users ADD COLUMN reminder_24h_sent INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN discount_offer_sent INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN purchased_at TEXT",
            "ALTER TABLE users ADD COLUMN review_requested INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN ab_variant TEXT",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
                await db.commit()
            except Exception:
                pass  # ustun allaqachon mavjud


async def upsert_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, started_at) VALUES (?, ?, ?, ?)",
                (user_id, username, first_name, datetime.utcnow().isoformat()),
            )
            await db.commit()
            return True  # yangi foydalanuvchi
        return False


async def save_lead(user_id: int, full_name: str, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET full_name=?, phone=?, lead_captured=1 WHERE user_id=?",
            (full_name, phone, user_id),
        )
        await db.commit()


async def mark_purchased(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET purchased=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def add_receipt(user_id: int, photo_file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO receipts (user_id, photo_file_id, created_at) VALUES (?, ?, ?)",
            (user_id, photo_file_id, datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def update_receipt_status(receipt_id: int, status: str, reviewed_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE receipts SET status=?, reviewed_by=? WHERE id=?",
            (status, reviewed_by, receipt_id),
        )
        await db.commit()


async def get_receipt(receipt_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, user_id, status FROM receipts WHERE id=?", (receipt_id,))
        return await cur.fetchone()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_not_purchased_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE purchased=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_ruspeak_lead_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT DISTINCT user_id FROM ruspeak_leads WHERE user_id IS NOT NULL")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        leads = (await (await db.execute("SELECT COUNT(*) FROM users WHERE lead_captured=1")).fetchone())[0]
        purchased = (await (await db.execute("SELECT COUNT(*) FROM users WHERE purchased=1")).fetchone())[0]
        pending_receipts = (
            await (await db.execute("SELECT COUNT(*) FROM receipts WHERE status='pending'")).fetchone()
        )[0]

        now = datetime.utcnow()
        today_start = now.strftime("%Y-%m-%d")
        week_start = (now - timedelta(days=7)).isoformat()
        month_start = (now - timedelta(days=30)).isoformat()

        today_count = (
            await (await db.execute(
                "SELECT COUNT(*) FROM users WHERE started_at LIKE ?", (today_start + "%",)
            )).fetchone()
        )[0]
        week_count = (
            await (await db.execute(
                "SELECT COUNT(*) FROM users WHERE started_at >= ?", (week_start,)
            )).fetchone()
        )[0]
        month_count = (
            await (await db.execute(
                "SELECT COUNT(*) FROM users WHERE started_at >= ?", (month_start,)
            )).fetchone()
        )[0]

        conversion = round((purchased / total * 100), 1) if total else 0.0

        return {
            "total": total,
            "leads": leads,
            "purchased": purchased,
            "pending_receipts": pending_receipts,
            "today": today_count,
            "week": week_count,
            "month": month_count,
            "conversion": conversion,
        }


async def export_users_csv() -> io.BytesIO:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, username, first_name, full_name, phone, started_at, lead_captured, purchased FROM users"
        )
        rows = await cur.fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["user_id", "username", "first_name", "full_name", "phone", "started_at", "lead_captured", "purchased"]
    )
    writer.writerows(rows)
    byte_buf = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    byte_buf.name = "users.csv"
    return byte_buf


async def clear_book_files():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM book_files")
        await db.commit()


async def add_book_file(file_id: str, file_type: str, file_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO book_files (file_id, file_type, file_name) VALUES (?, ?, ?)",
            (file_id, file_type, file_name),
        )
        await db.commit()


async def get_book_files():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT file_id, file_type, file_name FROM book_files ORDER BY id")
        return await cur.fetchall()


async def clear_sample_files():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sample_files")
        await db.commit()


async def add_sample_file(file_id: str, file_type: str, file_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sample_files (file_id, file_type, file_name) VALUES (?, ?, ?)",
            (file_id, file_type, file_name),
        )
        await db.commit()


async def get_sample_files():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT file_id, file_type, file_name FROM sample_files ORDER BY id")
        return await cur.fetchall()


async def is_operator(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM operators WHERE user_id=?", (user_id,))
        return (await cur.fetchone()) is not None


async def add_operator(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO operators (user_id, added_at) VALUES (?, ?)",
            (user_id, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def remove_operator(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM operators WHERE user_id=?", (user_id,))
        await db.commit()


async def list_operators():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, added_at FROM operators")
        return await cur.fetchall()


async def set_content(key: str, video_file_id: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bot_content (key, video_file_id, text) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET video_file_id=excluded.video_file_id, text=excluded.text",
            (key, video_file_id, text),
        )
        await db.commit()


async def get_content(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT video_file_id, text FROM bot_content WHERE key=?", (key,))
        return await cur.fetchone()


# ---------- Ruspeak (kurs) bonus fayllari ----------

async def clear_ruspeak_files():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ruspeak_files")
        await db.commit()


async def add_ruspeak_file(file_id: str, file_type: str, file_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ruspeak_files (file_id, file_type, file_name) VALUES (?, ?, ?)",
            (file_id, file_type, file_name),
        )
        await db.commit()


async def get_ruspeak_files():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT file_id, file_type, file_name FROM ruspeak_files ORDER BY id")
        return await cur.fetchall()


# ---------- Ruspeak lidlarini token orqali bog'lash ----------

async def save_ruspeak_lead(token: str, user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ruspeak_leads (token, user_id, username, first_name, linked_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(token) DO UPDATE SET user_id=excluded.user_id, username=excluded.username, "
            "first_name=excluded.first_name, linked_at=excluded.linked_at",
            (token, user_id, username, first_name, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_ruspeak_lead(token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT token, user_id, username, first_name, linked_at FROM ruspeak_leads WHERE token=?", (token,)
        )
        return await cur.fetchone()


async def get_ruspeak_lead_by_user_id(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT token, user_id, username, first_name, linked_at FROM ruspeak_leads WHERE user_id=? "
            "ORDER BY linked_at DESC LIMIT 1",
            (user_id,),
        )
        return await cur.fetchone()


# ---------- Umumiy sozlamalar (narx, matnlar va h.k. — botdan o'zgartiriladi) ----------

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT key, value FROM settings")
        rows = await cur.fetchall()
        return {k: v for k, v in rows}


# ---------- Foydalanuvchi tili (uz/ru) ----------

async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return (row[0] if row and row[0] else "uz")


async def set_user_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        await db.commit()


# ---------- Xavfsizlik: shubhali faollikni kuzatish ----------
# (soddalik uchun xotirada saqlanadi — bot qayta ishga tushsa tozalanadi, bu yetarli)
_start_activity: dict[int, list[float]] = {}

def check_suspicious_start(user_id: int, window_seconds: int = 60, max_starts: int = 5) -> bool:
    """True qaytarsa — shu foydalanuvchi shubhali darajada tez-tez /start bosayapti."""
    import time
    now = time.time()
    history = _start_activity.setdefault(user_id, [])
    history.append(now)
    # eskirgan yozuvlarni tozalaymiz
    _start_activity[user_id] = [t for t in history if now - t <= window_seconds]
    return len(_start_activity[user_id]) >= max_starts


# ---------- 4. Referal tizimi ----------

async def set_referrer(user_id: int, referrer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Faqat hali referred_by bo'sh bo'lsa yozamiz (o'zini o'zi taklif qilmasligi va qayta yozilmasligi uchun)
        await db.execute(
            "UPDATE users SET referred_by=? WHERE user_id=? AND referred_by IS NULL AND user_id != ?",
            (referrer_id, user_id, referrer_id),
        )
        await db.commit()


async def get_referral_count(referrer_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (referrer_id,))
        return (await cur.fetchone())[0]


async def get_referrer(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def get_referral_purchased_count(referrer_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by=? AND purchased=1", (referrer_id,)
        )
        return (await cur.fetchone())[0]


# ---------- 3 & 13. Sotib olishni bosib, tugatmaganlar (follow-up / chegirma) ----------

async def mark_buy_clicked(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT buy_clicked_at FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row and not row[0]:  # faqat birinchi marta yozamiz
            await db.execute(
                "UPDATE users SET buy_clicked_at=? WHERE user_id=?",
                (datetime.utcnow().isoformat(), user_id),
            )
            await db.commit()


async def get_users_needing_24h_reminder():
    threshold = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM users WHERE buy_clicked_at IS NOT NULL AND buy_clicked_at <= ? "
            "AND purchased=0 AND reminder_24h_sent=0",
            (threshold,),
        )
        return [r[0] for r in await cur.fetchall()]


async def mark_reminder_sent(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET reminder_24h_sent=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def get_users_needing_discount_offer():
    threshold = (datetime.utcnow() - timedelta(hours=72)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM users WHERE buy_clicked_at IS NOT NULL AND buy_clicked_at <= ? "
            "AND purchased=0 AND discount_offer_sent=0",
            (threshold,),
        )
        return [r[0] for r in await cur.fetchall()]


async def mark_discount_offer_sent(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET discount_offer_sent=1 WHERE user_id=?", (user_id,))
        await db.commit()


# ---------- 12. Xarid qilgandan keyin sharh so'rash ----------

async def mark_purchased_at(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET purchased_at=? WHERE user_id=?", (datetime.utcnow().isoformat(), user_id)
        )
        await db.commit()


async def get_users_needing_review_request():
    threshold = (datetime.utcnow() - timedelta(days=3)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM users WHERE purchased_at IS NOT NULL AND purchased_at <= ? "
            "AND review_requested=0",
            (threshold,),
        )
        return [r[0] for r in await cur.fetchall()]


async def mark_review_requested(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET review_requested=1 WHERE user_id=?", (user_id,))
        await db.commit()


# ---------- 10. A/B test ----------

async def get_or_assign_ab_variant(user_id: int) -> str:
    import random
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT ab_variant FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row and row[0]:
            return row[0]
        variant = random.choice(["A", "B"])
        if row is None:
            # Foydalanuvchi hali users jadvalida yo'q (odatiy holatda bo'lmasligi kerak,
            # lekin xavfsizlik uchun) — minimal yozuv yaratamiz
            await db.execute(
                "INSERT INTO users (user_id, started_at, ab_variant) VALUES (?, ?, ?)",
                (user_id, datetime.utcnow().isoformat(), variant),
            )
        else:
            await db.execute("UPDATE users SET ab_variant=? WHERE user_id=?", (variant, user_id))
        await db.commit()
        return variant


async def get_ab_test_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        result = {}
        for variant in ("A", "B"):
            total = (
                await (await db.execute(
                    "SELECT COUNT(*) FROM users WHERE ab_variant=?", (variant,)
                )).fetchone()
            )[0]
            purchased = (
                await (await db.execute(
                    "SELECT COUNT(*) FROM users WHERE ab_variant=? AND purchased=1", (variant,)
                )).fetchone()
            )[0]
            result[variant] = {
                "total": total,
                "purchased": purchased,
                "conversion": round(purchased / total * 100, 1) if total else 0.0,
            }
        return result


# ---------- 5. Kunlik avtomatik hisobot ----------

async def get_last_report_date() -> str:
    return await get_setting("last_daily_report_date", "")


async def set_last_report_date(date_str: str):
    await set_setting("last_daily_report_date", date_str)
