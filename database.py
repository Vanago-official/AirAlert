import logging

import aiosqlite  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

DB_NAME = "bot_database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            active INTEGER DEFAULT 1,
            is_muted INTEGER DEFAULT 0,
            clear_sending INTEGER DEFAULT 1,
            ai_clear_sending INTEGER DEFAULT 1)
        """)

        # Migration: add ai_clear_sending column if it doesn't exist
        try:
            await db.execute("ALTER TABLE users ADD COLUMN ai_clear_sending INTEGER DEFAULT 1")
        except aiosqlite.OperationalError:
            pass  # Column already exists

        await db.commit()


async def add_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

        if row is not None:
            return row
        logger.info(f"[DATABASE] New user: {user_id}")
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def get_active_users():
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT user_id FROM users WHERE is_muted = 0 AND active = 1"
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_muted_users():
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT user_id FROM users WHERE is_muted = 1 AND active = 1 AND clear_sending = 1"
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_ai_clear_users():
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT user_id FROM users WHERE is_muted = 1 AND active = 1 AND ai_clear_sending = 1"
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def set_all_mutes(flag):
    logger.info(f"[DATABASE] All is_muted set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_muted = ?", (flag,))
        await db.commit()


async def set_user_mute(user_id, flag):
    logger.info(f"[DATABASE] User {user_id} is_muted set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_muted = ? WHERE user_id = ?", (flag, user_id))
        await db.commit()

async def set_clear_sending(user_id, flag):
    logger.info(f"[DATABASE] User {user_id} clear_sending set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET clear_sending = ? WHERE user_id = ?", (flag, user_id))
        await db.commit()

async def set_ai_clear_sending(user_id, flag):
    logger.info(f"[DATABASE] User {user_id} ai_clear_sending set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ai_clear_sending = ? WHERE user_id = ?", (flag, user_id))
        await db.commit()

async def set_user_active(user_id, flag):
    logger.info(f"[DATABASE] User {user_id} active set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET active = ? WHERE user_id = ?", (flag, user_id))
        await db.commit()


async def get_user_info(user_id):
    logger.info(f"[DATABASE] Get info for user {user_id}")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT active, is_muted, clear_sending, ai_clear_sending FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row
