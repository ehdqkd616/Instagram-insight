import logging

from parsers import parse_liked_posts, parse_liked_comments, parse_comments

logger = logging.getLogger("instagram_analyzer.activity_service")


def search_sent_activity(data_dir, username, activity_type="all", from_date="", to_date=""):
    """내가 특정 계정에 남긴 좋아요/댓글 (발신)."""
    uname = username.lower().strip()
    logger.info(
        "search_sent_activity: username=%r, type=%s, from=%s, to=%s",
        username, activity_type, from_date, to_date,
    )

    results = []

    if activity_type in ("all", "like"):
        liked = parse_liked_posts(data_dir)
        before = len(results)
        for item in liked:
            if uname in item["username"].lower():
                results.append({
                    "type":       "like",
                    "post_url":   item["post_url"],
                    "content":    "",
                    "occurred_at": item["liked_at"],
                    "timestamp":  item["timestamp"],
                })
        logger.debug("liked_posts 검색: %d건 → %d건 매칭", len(liked), len(results) - before)

        liked_c = parse_liked_comments(data_dir)
        before = len(results)
        for item in liked_c:
            if uname in item["username"].lower():
                results.append({
                    "type":       "like_comment",
                    "post_url":   item["post_url"],
                    "content":    "",
                    "occurred_at": item["liked_at"],
                    "timestamp":  item["timestamp"],
                })
        logger.debug("liked_comments 검색: %d건 → %d건 매칭", len(liked_c), len(results) - before)

    if activity_type in ("all", "comment"):
        comments = parse_comments(data_dir)
        before = len(results)
        for item in comments:
            if uname in item["username"].lower():
                results.append({
                    "type":       "comment",
                    "post_url":   item["post_url"],
                    "content":    item["content"],
                    "occurred_at": item["commented_at"],
                    "timestamp":  item["timestamp"],
                })
        logger.debug("comments 검색: %d건 → %d건 매칭", len(comments), len(results) - before)

    results = _apply_date_filter(results, from_date, to_date)
    results.sort(key=lambda x: x["timestamp"], reverse=True)

    logger.info("search_sent_activity 결과: %d건", len(results))
    return {"username": username, "total": len(results), "activities": results}


def search_received_activity(data_dir, username, activity_type="all", from_date="", to_date=""):
    """특정 계정이 내 게시물에 남긴 활동 (수신) — 인스타그램 내보내기에 미포함."""
    logger.warning("search_received_activity: 수신 데이터 미포함 username=%r", username)
    return {
        "username": username,
        "total": 0,
        "activities": [],
        "notice": (
            "인스타그램 공식 데이터 내보내기에는 타인이 내 게시물에 남긴 "
            "좋아요·댓글 정보가 포함되지 않습니다. "
            "현재 '내가 보낸 활동(발신)' 데이터만 조회 가능합니다."
        ),
    }


def search_dm_activity(user_id: int, other_party: str = "", activity_type: str = "dm_all",
                       from_date: str = "", to_date: str = "") -> dict:
    """DB에서 DM 활동 검색."""
    from db import search_dm_activity as db_search, get_dm_count
    rows = db_search(user_id, other_party, activity_type, from_date, to_date)
    activities = [{
        "type":         row["activity_type"],
        "post_url":     row["link"],
        "content":      row["content"],
        "occurred_at":  row["occurred_at"],
        "timestamp":    row["timestamp"],
        "other_party":  row["other_party"],
        "thread_title": row["thread_title"],
    } for row in rows]

    total_stored = get_dm_count(user_id)
    label = other_party if other_party else "전체 DM"
    logger.info("search_dm_activity: %r type=%s → %d건", other_party, activity_type, len(activities))
    return {
        "username":     label,
        "total":        len(activities),
        "total_stored": total_stored,
        "activities":   activities,
        "is_dm":        True,
    }


def _apply_date_filter(items, from_date, to_date):
    if from_date:
        items = [i for i in items if i["occurred_at"] >= from_date]
    if to_date:
        items = [i for i in items if i["occurred_at"] <= to_date + " 23:59"]
    return items
