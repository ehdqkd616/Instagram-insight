import logging
import os

from parsers.utils import _fix_str, _load_json, _ts_to_str

logger = logging.getLogger("instagram_analyzer.parsers.activity")


def parse_liked_posts(data_dir: str) -> list:
    raw = _load_json(os.path.join(data_dir, "liked_posts.json"), "liked_posts")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("likes_media_likes", [])

    results = []
    for item in raw:
        if "label_values" in item:
            timestamp = item.get("timestamp", 0)
            post_url = ""
            username = ""
            for lv in item.get("label_values", []):
                if lv.get("label") == "URL":
                    post_url = lv.get("href") or lv.get("value", "")
                if lv.get("dict") and not lv.get("label"):
                    for d in lv.get("dict", []):
                        d_label = _fix_str(d.get("label", ""))
                        if "사용자 이름" in d_label or d_label.lower() == "username":
                            username = d.get("value", "")
                            break
            results.append({
                "username":  username,
                "post_url":  post_url,
                "liked_at":  _ts_to_str(timestamp),
                "timestamp": timestamp,
            })
        else:
            title = item.get("title", "")
            for entry in item.get("string_list_data", []):
                results.append({
                    "username":  title,
                    "post_url":  entry.get("href", ""),
                    "liked_at":  _ts_to_str(entry.get("timestamp", 0)),
                    "timestamp": entry.get("timestamp", 0),
                })
    logger.info("[liked_posts] 게시물 좋아요 %d건 파싱 완료", len(results))
    return results


def parse_liked_comments(data_dir: str) -> list:
    raw = _load_json(os.path.join(data_dir, "liked_comments.json"), "liked_comments")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("likes_comment_likes", [])

    results = []
    for item in raw:
        title = item.get("title", "")
        for entry in item.get("string_list_data", []):
            results.append({
                "username": title,
                "post_url": entry.get("href", ""),
                "liked_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp": entry.get("timestamp", 0),
            })
    logger.info("[liked_comments] 댓글 좋아요 %d건 파싱 완료", len(results))
    return results


def parse_comments(data_dir: str) -> list:
    raw = _load_json(os.path.join(data_dir, "post_comments_1.json"), "comments")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("comments_media_comments", [])

    results = []
    for item in raw:
        if "string_map_data" in item:
            smd = item["string_map_data"]
            username  = _fix_str(smd.get("Media Owner", {}).get("value", ""))
            content   = _fix_str(smd.get("Comment", {}).get("value", ""))
            timestamp = smd.get("Time", {}).get("timestamp", 0)
            results.append({
                "username":     username,
                "content":      content,
                "post_url":     "",
                "commented_at": _ts_to_str(timestamp),
                "timestamp":    timestamp,
            })
        else:
            title = _fix_str(item.get("title", ""))
            for entry in item.get("string_list_data", []):
                results.append({
                    "username":     title,
                    "content":      _fix_str(entry.get("value", "")),
                    "post_url":     entry.get("href", ""),
                    "commented_at": _ts_to_str(entry.get("timestamp", 0)),
                    "timestamp":    entry.get("timestamp", 0),
                })
    logger.info("[comments] 댓글 %d건 파싱 완료", len(results))
    return results
