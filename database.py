import aiosqlite
import csv
import io
from datetime import datetime
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
    purchased INTEGER DEFAULT 0
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
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


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


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        leads = (await (await db.execute("SELECT COUNT(*) FROM users WHERE lead_captured=1")).fetchone())[0]
        purchased = (await (await db.execute("SELECT COUNT(*) FROM users WHERE purchased=1")).fetchone())[0]
        pending_receipts = (
            await (await db.execute("SELECT COUNT(*) FROM receipts WHERE status='pending'")).fetchone()
        )[0]
        return {
            "total": total,
            "leads": leads,
            "purchased": purchased,
            "pending_receipts": pending_receipts,
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
