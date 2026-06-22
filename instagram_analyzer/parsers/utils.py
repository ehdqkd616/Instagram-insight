import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("instagram_analyzer.parsers")


def _ts_to_str(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _fix_str(s: str) -> str:
    """Instagram이 한글을 Latin-1 mojibake로 내보낸 경우 UTF-8로 복원."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _load_json(path: str, label: str):
    if not os.path.exists(path):
        logger.debug("[%s] 파일 없음: %s", label, path)
        return None
    size_kb = os.path.getsize(path) / 1024
    logger.debug("[%s] 파싱 시작 (%.1f KB): %s", label, size_kb, os.path.basename(path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    logger.debug("[%s] 파싱 완료", label)
    return data
