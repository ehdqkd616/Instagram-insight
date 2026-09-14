import logging
from datetime import datetime

from db.connection import _get_db

logger = logging.getLogger("instagram_analyzer.db.followers")


def has_follower_snapshot(user_id: int) -> bool:
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM follower_snapshots WHERE user_id = ?",
            (int(user_id),)
        ).fetchone()
    return (row[0] if row else 0) > 0


def process_follower_snapshot(user_id: int, followers: list, last_seen_at: str = "") -> int:
    """last_seen_at: 이 스냅샷 직전(마지막으로 팔로우가 확인된) 업로드 시각.
    인스타그램 내보내기에는 실제 언팔 날짜가 없어서, '마지막으로 팔로우 확인됨(last_seen_at)
    ~ 지금 사라짐이 감지됨(unfollowed_at)' 범위로만 추정할 수 있다."""
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
                """INSERT INTO unfollower_events
                       (user_id, username, followed_at, last_seen_at, unfollowed_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, username) DO UPDATE
                   SET followed_at=excluded.followed_at,
                       last_seen_at=excluded.last_seen_at,
                       unfollowed_at=excluded.unfollowed_at,
                       detected_at=CURRENT_TIMESTAMP""",
                (int(user_id), username, prev[username], last_seen_at, now_str)
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
    with _get_db() as conn:
        rows = conn.execute(
            """SELECT username, followed_at, last_seen_at, unfollowed_at
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
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM unfollower_events WHERE user_id = ?",
            (int(user_id),)
        ).fetchone()
    return row[0] if row else 0
