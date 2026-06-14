import logging
import logging.handlers
import os
import re

LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)-24s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 로그 파일 경로 (app.py 에서 setup 후 설정됨)
LOG_FILE: str = ""

# 레벨별 색상 (ANSI — 터미널 전용)
_COLORS = {
    "DEBUG":    "\033[90m",
    "INFO":     "\033[36m",
    "WARNING":  "\033[33m",
    "ERROR":    "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = _COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{_RESET}"
        return super().format(record)


def setup_logging(base_dir: str) -> str:
    """로깅 초기화. 로그 파일 경로 반환."""
    global LOG_FILE
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    LOG_FILE = os.path.join(logs_dir, "app.log")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    plain_fmt  = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    color_fmt  = ColorFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 파일 핸들러: DEBUG 이상, 최대 2MB × 5개 보관
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(plain_fmt)
    root.addHandler(fh)

    # 콘솔 핸들러: INFO 이상, 색상 출력
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(color_fmt)
    root.addHandler(ch)

    # Werkzeug 요청 로그 억제 (직접 기록)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    return LOG_FILE


# ── 로그 파일 읽기 유틸 ──────────────────────────────────
_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\s*\] (\S+)\s+— (.*)$"
)


def read_recent_logs(n: int = 200) -> list[dict]:
    """최근 n 줄을 파싱하여 구조화된 리스트로 반환."""
    if not LOG_FILE or not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    results = []
    for line in lines[-n:]:
        line = line.rstrip()
        m = _LINE_RE.match(line)
        if m:
            results.append({
                "ts":      m.group(1),
                "level":   m.group(2),
                "module":  m.group(3),
                "message": m.group(4),
            })
        else:
            # 멀티라인 스택 트레이스 등은 이전 항목에 붙이기
            if results:
                results[-1]["message"] += " | " + line
    return results
