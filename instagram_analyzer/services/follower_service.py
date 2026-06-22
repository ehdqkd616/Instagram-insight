import logging

from parsers import parse_followers, parse_following, parse_recently_unfollowed

logger = logging.getLogger("instagram_analyzer.follower_service")


def get_followers(data_dir, search="", sort="newest", from_date="", to_date=""):
    followers = parse_followers(data_dir)
    total_raw = len(followers)

    if search:
        q = search.lower()
        followers = [f for f in followers if q in f["username"].lower()]

    if from_date:
        followers = [f for f in followers if f["followed_at"] >= from_date]
    if to_date:
        followers = [f for f in followers if f["followed_at"] <= to_date + " 23:59"]

    if sort == "newest":
        followers.sort(key=lambda x: x["timestamp"], reverse=True)
    elif sort == "oldest":
        followers.sort(key=lambda x: x["timestamp"])
    elif sort == "username":
        followers.sort(key=lambda x: x["username"].lower())

    logger.debug(
        "get_followers: 전체 %d명 → 필터 후 %d명 (search=%r, sort=%s)",
        total_raw, len(followers), search, sort,
    )
    return {"total": len(followers), "followers": followers}


def get_following(data_dir, search="", sort="newest", from_date="", to_date=""):
    following = parse_following(data_dir)
    followers_set = {f["username"] for f in parse_followers(data_dir)}
    total_raw = len(following)

    for f in following:
        f["is_mutual"] = f["username"] in followers_set

    if search:
        q = search.lower()
        following = [f for f in following if q in f["username"].lower()]

    if from_date:
        following = [f for f in following if f["followed_at"] >= from_date]
    if to_date:
        following = [f for f in following if f["followed_at"] <= to_date + " 23:59"]

    if sort == "newest":
        following.sort(key=lambda x: x["timestamp"], reverse=True)
    elif sort == "oldest":
        following.sort(key=lambda x: x["timestamp"])
    elif sort == "username":
        following.sort(key=lambda x: x["username"].lower())

    logger.debug(
        "get_following: 전체 %d명 → 필터 후 %d명 (search=%r, sort=%s)",
        total_raw, len(following), search, sort,
    )
    return {"total": len(following), "following": following}


def get_not_following_back(data_dir, search=""):
    following = parse_following(data_dir)
    followers_set = {f["username"] for f in parse_followers(data_dir)}
    result = [f for f in following if f["username"] not in followers_set]
    if search:
        q = search.lower()
        result = [f for f in result if q in f["username"].lower()]
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    logger.info("get_not_following_back: 팔로잉 %d명 중 맞팔 안 됨 %d명", len(following), len(result))
    return {"total": len(result), "accounts": result}


def get_only_following_me(data_dir, search=""):
    followers = parse_followers(data_dir)
    following_set = {f["username"] for f in parse_following(data_dir)}
    result = [f for f in followers if f["username"] not in following_set]
    if search:
        q = search.lower()
        result = [f for f in result if q in f["username"].lower()]
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    logger.info("get_only_following_me: 팔로워 %d명 중 나만 팔로우 %d명", len(followers), len(result))
    return {"total": len(result), "accounts": result}


def get_mutual(data_dir, search=""):
    followers = parse_followers(data_dir)
    following_set = {f["username"] for f in parse_following(data_dir)}
    result = [f for f in followers if f["username"] in following_set]
    if search:
        q = search.lower()
        result = [f for f in result if q in f["username"].lower()]
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    logger.info("get_mutual: 맞팔 %d명", len(result))
    return {"total": len(result), "accounts": result}


def get_stats(data_dir, user_id=None):
    followers = parse_followers(data_dir)
    following = parse_following(data_dir)
    followers_set = {f["username"] for f in followers}
    following_set = {f["username"] for f in following}
    mutual = followers_set & following_set

    unfollower_count = 0
    if user_id is not None:
        from db import get_unfollower_count
        unfollower_count = get_unfollower_count(user_id)

    stats = {
        "followers_count":    len(followers),
        "following_count":    len(following),
        "mutual_count":       len(mutual),
        "not_following_back": len(following_set - followers_set),
        "only_following_me":  len(followers_set - following_set),
        "mutual_ratio":       round(len(mutual) / len(followers) * 100, 1) if followers else 0,
        "unfollower_count":   unfollower_count,
    }
    logger.info(
        "stats: 팔로워=%d, 팔로잉=%d, 맞팔=%d, 맞팔안됨=%d, 언팔=%d",
        stats["followers_count"], stats["following_count"],
        stats["mutual_count"], stats["not_following_back"], unfollower_count,
    )
    return stats


def get_unfollower_history(user_id: int, search: str = "") -> dict:
    from db import get_unfollower_events
    events = get_unfollower_events(user_id, search)
    return {"total": len(events), "accounts": events}


def get_recently_unfollowed(data_dir: str, search: str = "") -> dict:
    accounts = parse_recently_unfollowed(data_dir)
    if search:
        q = search.lower()
        accounts = [a for a in accounts if q in a["username"].lower()]
    accounts.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"total": len(accounts), "accounts": accounts}
