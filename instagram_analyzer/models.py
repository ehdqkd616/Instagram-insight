import logging
import os
import sqlite3

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from config import DATA_DIR, DB_PATH

logger = logging.getLogger("instagram_analyzer.models")


# ── User 모델 ─────────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, id: int, username: str, password_hash: str,
                 display_name: str = "", instagram_username: str = ""):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.display_name = display_name or username
        self.instagram_username = instagram_username

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def data_dir(self) -> str:
        """계정별 전용 데이터 디렉토리. 없으면 자동 생성."""
        path = os.path.join(DATA_DIR, str(self.id))
        os.makedirs(path, exist_ok=True)
        return path

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"


# ── DB 연결 ───────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """앱 시작 시 테이블 초기화."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                username           TEXT    UNIQUE NOT NULL,
                password_hash      TEXT    NOT NULL,
                display_name       TEXT    DEFAULT '',
                instagram_username TEXT    DEFAULT '',
                created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, display_name: str = "") -> "User | None":
    """회원 생성. 중복 username이면 None 반환."""
    ph = generate_password_hash(password)
    try:
        with _get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username.strip(), ph, display_name.strip()),
            )
            user_id = cur.lastrowid
        logger.info("신규 사용자 생성: id=%d username=%r", user_id, username)
        return find_user_by_id(user_id)
    except sqlite3.IntegrityError:
        logger.warning("사용자 생성 실패 — 중복 username: %r", username)
        return None


def find_user_by_username(username: str) -> "User | None":
    with _get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username "
            "FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row:
        return User(*row)
    return None


def find_user_by_id(user_id: int) -> "User | None":
    with _get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username "
            "FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
    if row:
        return User(*row)
    return None


def update_instagram_username(user_id: int, ig_username: str):
    """업로드된 JSON에서 감지한 인스타그램 계정명 저장."""
    with _get_db() as conn:
        conn.execute(
            "UPDATE users SET instagram_username = ? WHERE id = ?",
            (ig_username, int(user_id)),
        )
    logger.info("instagram_username 업데이트: user_id=%d → %r", user_id, ig_username)


def list_users() -> list[User]:
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username FROM users"
        ).fetchall()
    return [User(*r) for r in rows]


# ── 팔로워 스냅샷 / 언팔로워 감지 ────────────────────────────────────────────

def has_follower_snapshot(user_id: int) -> bool:
    """이전에 저장된 팔로워 스냅샷이 있는지 확인."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM follower_snapshots WHERE user_id = ?",
            (int(user_id),)
        ).fetchone()
    return (row[0] if row else 0) > 0


def process_follower_snapshot(user_id: int, followers: list) -> int:
    """
    새 팔로워 목록을 이전 스냅샷과 비교해 언팔로워를 감지하고 저장.
    첫 업로드 시엔 스냅샷만 저장하고 0을 반환.
    Returns: 새로 감지된 언팔로워 수
    """
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    with _get_db() as conn:
        prev_rows = conn.execute(
            "SELECT username, followed_at FROM follower_snapshots WHERE user_id = ?",
            (int(user_id),)
        ).fetchall()
        prev = {row["username"]: row["followed_at"] for row in prev_rows}

        new_set = {f["username"] for f in followers}
        unfollowed = set(prev.keys()) - new_set
        count = 0

        for username in unfollowed:
            conn.execute(
                """INSERT INTO unfollower_events (user_id, username, followed_at, unfollowed_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, username) DO UPDATE
                   SET followed_at=excluded.followed_at,
                       unfollowed_at=excluded.unfollowed_at,
                       detected_at=CURRENT_TIMESTAMP""",
                (int(user_id), username, prev[username], now_str)
            )
            count += 1

        conn.execute("DELETE FROM follower_snapshots WHERE user_id = ?", (int(user_id),))
        conn.executemany(
            "INSERT INTO follower_snapshots (user_id, username, followed_at) VALUES (?, ?, ?)",
            [(int(user_id), f["username"], f.get("followed_at", "")) for f in followers]
        )

    logger.info("팔로워 스냅샷: user_id=%d, 이전=%d, 현재=%d, 언팔=%d",
                user_id, len(prev), len(followers), count)
    return count


def get_unfollower_events(user_id: int, search: str = "") -> list:
    """감지된 언팔로워 이벤트 목록 (최신순)."""
    with _get_db() as conn:
        rows = conn.execute(
            """SELECT username, followed_at, unfollowed_at
               FROM unfollower_events
               WHERE user_id = ?
               ORDER BY detected_at DESC""",
            (int(user_id),)
        ).fetchall()
    events = [dict(row) for row in rows]
    if search:
        q = search.lower()
        events = [e for e in events if q in e["username"].lower()]
    return events


def get_unfollower_count(user_id: int) -> int:
    """감지된 언팔로워 총 수."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM unfollower_events WHERE user_id = ?",
            (int(user_id),)
        ).fetchone()
    return row[0] if row else 0


# ── DM 활동 ───────────────────────────────────────────────────────────────────

def set_user_setting(user_id: int, key: str, value: str):
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO user_settings(user_id, key, value) VALUES(?,?,?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value",
            (int(user_id), key, value)
        )


def get_user_setting(user_id: int, key: str, default: str = "") -> str:
    with _get_db() as conn:
        row = conn.execute(
            "SELECT value FROM user_settings WHERE user_id=? AND key=?",
            (int(user_id), key)
        ).fetchone()
    return row["value"] if row else default


def store_dm_activity(user_id: int, activities: list) -> int:
    """DM 활동 기록 저장 (기존 데이터 전체 교체)."""
    with _get_db() as conn:
        conn.execute("DELETE FROM dm_activity WHERE user_id=?", (int(user_id),))
        conn.executemany(
            """INSERT INTO dm_activity
               (user_id, thread_title, other_party, activity_type, content, link, timestamp, occurred_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            [(int(user_id), a["thread_title"], a["other_party"], a["activity_type"],
              a["content"], a["link"], a["timestamp"], a["occurred_at"])
             for a in activities]
        )
    logger.info("DM 활동 저장: user_id=%d, %d건", user_id, len(activities))
    return len(activities)


def search_dm_activity(user_id: int, other_party: str = "",
                        activity_type: str = "", from_date: str = "", to_date: str = "") -> list:
    """DM 활동 검색 (DB)."""
    query = "SELECT * FROM dm_activity WHERE user_id=?"
    params: list = [int(user_id)]

    if other_party:
        query += " AND LOWER(other_party) LIKE ?"
        params.append(f"%{other_party.lower()}%")

    if activity_type and activity_type not in ("dm_all", ""):
        query += " AND activity_type=?"
        params.append(activity_type)

    if from_date:
        query += " AND occurred_at >= ?"
        params.append(from_date)

    if to_date:
        query += " AND occurred_at <= ?"
        params.append(to_date + " 23:59")

    query += " ORDER BY timestamp DESC LIMIT 2000"

    with _get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_dm_count(user_id: int) -> int:
    """저장된 DM 활동 총 건수."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM dm_activity WHERE user_id=?", (int(user_id),)
        ).fetchone()
    return row[0] if row else 0


def get_dm_thread_partners(user_id: int, search: str = "", limit: int = 50) -> list:
    """DM 대화 상대 목록 (메시지 수 많은 순). DM 표시 이름은 @username과 다를 수 있음."""
    query = """SELECT other_party, COUNT(*) as cnt, MAX(timestamp) as last_ts
               FROM dm_activity WHERE user_id=?"""
    params: list = [int(user_id)]
    if search:
        query += " AND LOWER(other_party) LIKE ?"
        params.append(f"%{search.lower()}%")
    query += " GROUP BY other_party ORDER BY cnt DESC LIMIT ?"
    params.append(limit)
    with _get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


# ── 업로드 히스토리 ───────────────────────────────────────────────────────────

def record_upload_snapshot(user_id: int, stats: dict, files_uploaded: list, new_unfollowers: int = 0) -> int:
    """업로드 시점의 통계를 히스토리로 기록."""
    import json as _json
    with _get_db() as conn:
        cur = conn.execute(
            """INSERT INTO upload_history
               (user_id, files_uploaded, followers_count, following_count,
                mutual_count, not_following_back, only_following_me, new_unfollowers)
               VALUES (?,?,?,?,?,?,?,?)""",
            (int(user_id), _json.dumps(files_uploaded, ensure_ascii=False),
             stats.get("followers_count", 0), stats.get("following_count", 0),
             stats.get("mutual_count", 0), stats.get("not_following_back", 0),
             stats.get("only_following_me", 0), new_unfollowers)
        )
        row_id = cur.lastrowid
    logger.info("업로드 히스토리 기록: user_id=%d, id=%d", user_id, row_id)
    return row_id


def get_upload_history(user_id: int) -> list:
    """업로드 히스토리 (최신순)."""
    import json as _json
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM upload_history WHERE user_id=? ORDER BY uploaded_at DESC",
            (int(user_id),)
        ).fetchall()
    history = []
    for row in rows:
        d = dict(row)
        try:
            d["files_uploaded"] = _json.loads(d["files_uploaded"]) if d["files_uploaded"] else []
        except Exception:
            d["files_uploaded"] = []
        history.append(d)
    return history


def delete_upload_history_entry(user_id: int, entry_id: int):
    with _get_db() as conn:
        conn.execute(
            "DELETE FROM upload_history WHERE user_id=? AND id=?",
            (int(user_id), int(entry_id))
        )
    logger.info("업로드 히스토리 삭제: user_id=%d, id=%d", user_id, entry_id)
