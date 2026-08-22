import logging
import aiosqlite

DB_NAME = "bot_database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            active INTEGER DEFAULT 1,
            is_muted INTEGER DEFAULT 0)
        """)
        await db.commit()


async def add_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()

        if row is not None:
            return row
        logging.info(f"[DATABASE] new user - {user_id}.")
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def get_active_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE is_muted  = 0 AND active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def set_all_mutes(flag):
    logging.info(f"[DATABASE] all is_muted changed to {flag}.")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_muted = ?", (flag,))
        await db.commit()


async def set_user_mute(id, flag):
    logging.info(f"[DATABASE] user {id} is_muted changed to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET is_muted = ? WHERE user_id = ?", (flag, id))
        await db.commit()


async def set_user_active(id, flag):
    logging.info(f"[DATABASE] user {id} active changed to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET active = ? WHERE user_id = ?", (flag, id))
        await db.commit()


async def get_user_info(id):
    logging.info(f"[DATABASE] user get info {id}")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            f"SELECT active, is_muted FROM users WHERE user_id = ?", (id,)
        )
        row = await cursor.fetchone()

        if row is not None:
            return row
        return None