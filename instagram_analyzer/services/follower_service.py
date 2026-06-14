from .parser import parse_followers, parse_following


def get_followers(data_dir, search="", sort="newest", from_date="", to_date=""):
    followers = parse_followers(data_dir)

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

    return {"total": len(followers), "followers": followers}


def get_not_following_back(data_dir, search=""):
    """내가 팔로우하지만 나를 팔로우하지 않는 계정 (맞팔 안 됨)."""
    following = parse_following(data_dir)
    followers_set = {f["username"] for f in parse_followers(data_dir)}

    result = [f for f in following if f["username"] not in followers_set]

    if search:
        q = search.lower()
        result = [f for f in result if q in f["username"].lower()]

    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"total": len(result), "accounts": result}


def get_only_following_me(data_dir, search=""):
    """나를 팔로우하지만 내가 팔로우하지 않는 계정."""
    followers = parse_followers(data_dir)
    following_set = {f["username"] for f in parse_following(data_dir)}

    result = [f for f in followers if f["username"] not in following_set]

    if search:
        q = search.lower()
        result = [f for f in result if q in f["username"].lower()]

    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"total": len(result), "accounts": result}


def get_mutual(data_dir, search=""):
    """맞팔 계정."""
    followers = parse_followers(data_dir)
    following_set = {f["username"] for f in parse_following(data_dir)}

    result = [f for f in followers if f["username"] in following_set]

    if search:
        q = search.lower()
        result = [f for f in result if q in f["username"].lower()]

    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"total": len(result), "accounts": result}


def get_stats(data_dir):
    followers = parse_followers(data_dir)
    following = parse_following(data_dir)
    followers_set = {f["username"] for f in followers}
    following_set = {f["username"] for f in following}
    mutual = followers_set & following_set
    return {
        "followers_count": len(followers),
        "following_count": len(following),
        "mutual_count": len(mutual),
        "not_following_back": len(following_set - followers_set),
        "only_following_me": len(followers_set - following_set),
        "mutual_ratio": round(len(mutual) / len(followers) * 100, 1) if followers else 0,
    }
