import logging

from .parser import parse_liked_posts, parse_liked_comments, parse_comments

logger = logging.getLogger("instagram_analyzer.activity_service")


def search_sent_activity(data_dir, username, activity_type="all", from_date="", to_date=""):
    """내가 특정 계정에 남긴 좋아요/댓글 (F-04 발신)."""
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
    """특정 계정이 내 게시물에 남긴 좋아요/댓글 (F-03 수신).

    인스타그램 공식 내보내기에는 타인이 내 게시물에 남긴 좋아요·댓글 데이터가 포함되지 않음.
    """
    logger.warning(
        "search_received_activity: username=%r — 인스타그램 내보내기에 수신 데이터 미포함",
        username,
    )
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


def _apply_date_filter(items, from_date, to_date):
    if from_date:
        items = [i for i in items if i["occurred_at"] >= from_date]
    if to_date:
        items = [i for i in items if i["occurred_at"] <= to_date + " 23:59"]
    return items
