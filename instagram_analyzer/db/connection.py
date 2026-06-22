import logging
import sqlite3

from config import DB_PATH

logger = logging.getLogger("instagram_analyzer.db")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                username           TEXT    UNIQUE NOT NULL,
                password_hash      TEXT    NOT NULL,
                display_name       TEXT    DEFAULT '',
                instagram_username TEXT    DEFAULT '',
                is_admin           INTEGER NOT NULL DEFAULT 0,
                created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col_sql in (
            "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN security_question TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN security_answer_hash TEXT DEFAULT ''",
        ):
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass

        admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0]
        if admin_count == 0:
            conn.execute("UPDATE users SET is_admin=1 WHERE id=(SELECT MIN(id) FROM users)")
            logger.info("관리자 없음 → 최초 사용자에게 관리자 권한 자동 부여")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS follower_snapshots (
                user_id     INTEGER NOT NULL,
                username    TEXT    NOT NULL,
                followed_at TEXT    DEFAULT '',
                PRIMARY KEY (user_id, username)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unfollower_events (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                username      TEXT    NOT NULL,
                followed_at   TEXT    DEFAULT '',
                unfollowed_at TEXT    DEFAULT '',
                detected_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, username)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dm_activity (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                thread_title  TEXT    DEFAULT '',
                other_party   TEXT    DEFAULT '',
                activity_type TEXT    DEFAULT '',
                content       TEXT    DEFAULT '',
                link          TEXT    DEFAULT '',
                timestamp     INTEGER DEFAULT 0,
                occurred_at   TEXT    DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dm_user_party
            ON dm_activity(user_id, other_party)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER NOT NULL,
                key     TEXT    NOT NULL,
                value   TEXT    DEFAULT '',
                PRIMARY KEY (user_id, key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER NOT NULL,
                uploaded_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                files_uploaded     TEXT    DEFAULT '',
                followers_count    INTEGER DEFAULT 0,
                following_count    INTEGER DEFAULT 0,
                mutual_count       INTEGER DEFAULT 0,
                not_following_back INTEGER DEFAULT 0,
                only_following_me  INTEGER DEFAULT 0,
                new_unfollowers    INTEGER DEFAULT 0
            )
        """)
    logger.info("DB 초기화 완료: %s", DB_PATH)
