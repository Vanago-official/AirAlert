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
            auto_mute INTEGER DEFAULT 0)
        """)

        # Migration: add auto_mute to databases created before it existed
        try:
            await db.execute("ALTER TABLE users ADD COLUMN auto_mute INTEGER DEFAULT 0")
            logger.info("[DATABASE] Added column auto_mute")
        except aiosqlite.OperationalError:
            pass  # Column already exists

        # Alert kinds a user has turned off. No row means the kind is enabled.
        await db.execute("""
        CREATE TABLE IF NOT EXISTS disabled_alerts (
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            PRIMARY KEY (user_id, kind))
        """)

        # Migration: drop the ai_clear_sending column left over from the removed AI feature
        try:
            await db.execute("ALTER TABLE users DROP COLUMN ai_clear_sending")
            logger.info("[DATABASE] Dropped obsolete column ai_clear_sending")
        except aiosqlite.OperationalError:
            pass  # Column does not exist

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


async def get_recipients(include_muted=False, require_clear=False):
    """Return [(user_id, disabled_kinds_set), ...] for active users.

    include_muted: also return muted users.
    require_clear: only users who want end-of-alert messages.
    """
    conditions = ["u.active = 1"]
    if not include_muted:
        conditions.append("u.is_muted = 0")
    if require_clear:
        conditions.append("u.clear_sending = 1")

    query = (
        "SELECT u.user_id, GROUP_CONCAT(d.kind) FROM users u "
        "LEFT JOIN disabled_alerts d ON d.user_id = u.user_id "
        f"WHERE {' AND '.join(conditions)} GROUP BY u.user_id"
    )
    async with aiosqlite.connect(DB_NAME) as db, db.execute(query) as cursor:
        rows = await cursor.fetchall()
        return [(row[0], set(row[1].split(",")) if row[1] else set()) for row in rows]


async def get_disabled_kinds(user_id):
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT kind FROM disabled_alerts WHERE user_id = ?", (user_id,)
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        return {row[0] for row in rows}


async def set_kind_enabled(user_id, kind, enabled):
    logger.info(f"[DATABASE] User {user_id} alert {kind} enabled set to {enabled}")
    async with aiosqlite.connect(DB_NAME) as db:
        if enabled:
            await db.execute(
                "DELETE FROM disabled_alerts WHERE user_id = ? AND kind = ?",
                (user_id, kind),
            )
        else:
            await db.execute(
                "INSERT OR IGNORE INTO disabled_alerts (user_id, kind) VALUES (?, ?)",
                (user_id, kind),
            )
        await db.commit()


async def set_all_kinds_enabled(user_id, kinds, enabled):
    logger.info(f"[DATABASE] User {user_id} all alerts enabled set to {enabled}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM disabled_alerts WHERE user_id = ?", (user_id,))
        if not enabled:
            await db.executemany(
                "INSERT INTO disabled_alerts (user_id, kind) VALUES (?, ?)",
                [(user_id, kind) for kind in kinds],
            )
        await db.commit()


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

async def set_auto_mute(user_id, flag):
    logger.info(f"[DATABASE] User {user_id} auto_mute set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET auto_mute = ? WHERE user_id = ?", (flag, user_id))
        await db.commit()


async def apply_auto_mute(user_ids):
    """Mute the given users who have auto_mute turned on."""
    if not user_ids:
        return
    placeholders = ",".join("?" * len(user_ids))
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            f"UPDATE users SET is_muted = 1 WHERE auto_mute = 1 AND user_id IN ({placeholders})",
            list(user_ids),
        )
        await db.commit()
        if cursor.rowcount:
            logger.info(f"[DATABASE] Auto-muted {cursor.rowcount} users")


async def set_user_active(user_id, flag):
    logger.info(f"[DATABASE] User {user_id} active set to {flag}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET active = ? WHERE user_id = ?", (flag, user_id))
        await db.commit()


async def get_user_info(user_id):
    logger.info(f"[DATABASE] Get info for user {user_id}")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT active, is_muted, clear_sending, auto_mute FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row
