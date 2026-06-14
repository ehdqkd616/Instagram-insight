from .parser import parse_liked_posts, parse_liked_comments, parse_comments


def search_sent_activity(data_dir, username, activity_type="all", from_date="", to_date=""):
    """내가 특정 계정에 남긴 좋아요/댓글 (F-04 발신)."""
    results = []
    uname = username.lower().strip()

    if activity_type in ("all", "like"):
        for item in parse_liked_posts(data_dir):
            if uname in item["username"].lower():
                results.append({
                    "type": "like",
                    "post_url": item["post_url"],
                    "content": "",
                    "occurred_at": item["liked_at"],
                    "timestamp": item["timestamp"],
                })
        for item in parse_liked_comments(data_dir):
            if uname in item["username"].lower():
                results.append({
                    "type": "like_comment",
                    "post_url": item["post_url"],
                    "content": "",
                    "occurred_at": item["liked_at"],
                    "timestamp": item["timestamp"],
                })

    if activity_type in ("all", "comment"):
        for item in parse_comments(data_dir):
            if uname in item["username"].lower():
                results.append({
                    "type": "comment",
                    "post_url": item["post_url"],
                    "content": item["content"],
                    "occurred_at": item["commented_at"],
                    "timestamp": item["timestamp"],
                })

    results = _apply_date_filter(results, from_date, to_date)
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"username": username, "total": len(results), "activities": results}


def search_received_activity(data_dir, username, activity_type="all", from_date="", to_date=""):
    """특정 계정이 내 게시물에 남긴 좋아요/댓글 (F-03 수신).

    liked_posts / liked_comments 는 '내가 누른' 데이터이므로 수신 분석에 직접 사용 불가.
    post_comments_1 에서 내 게시물에 달린 댓글은 별도 파일(comments_on_my_posts)이 필요하지만
    인스타그램 내보내기에 포함되지 않을 수 있으므로 현재 파악 가능한 정보만 반환.
    """
    # 인스타그램 공식 내보내기에서 '타인이 내 게시물에 남긴 좋아요'는 제공되지 않음.
    # post_comments_1.json은 '내가 남긴 댓글'이므로 F-03(수신)에는 사용 불가.
    # 따라서 현재 구조에서는 수신 데이터를 제공할 수 없음을 안내.
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
