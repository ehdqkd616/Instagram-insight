import logging

from db.connection import _get_db

logger = logging.getLogger("instagram_analyzer.db.activity")


# ── 사용자 설정 ───────────────────────────────────────────────────────────────

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


# ── DM 활동 ───────────────────────────────────────────────────────────────────

def store_dm_activity(user_id: int, activities: list) -> int:
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
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM dm_activity WHERE user_id=?", (int(user_id),)
        ).fetchone()
    return row[0] if row else 0


def get_dm_thread_partners(user_id: int, search: str = "", limit: int = 50) -> list:
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
