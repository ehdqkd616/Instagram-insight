"""관리자 알림 메일 — 회원가입 시 승인 요청을 보낸다.

설정은 환경변수(또는 config.py가 읽어 들이는 instagram_analyzer/.env)에서 온다:
ADMIN_NOTIFY_EMAILS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, PUBLIC_WEB_URL.
SMTP 계정이나 수신자가 비어 있으면 조용히 건너뛴다. 발송은 별도 스레드에서 해서
메일 서버가 느리거나 실패해도 가입 요청 처리에는 영향이 없다 (실패는 로그로만 남긴다).
"""

import html
import logging
import os
import smtplib
import ssl
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

logger = logging.getLogger("instagram_analyzer.notify")

APP_NAME = "Instagram Analyzer"

# 한국은 서머타임이 없어서 고정 오프셋으로 충분하다.
KST = timezone(timedelta(hours=9), "KST")

BRAND = "#d62976"
INK = "#0f1115"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def format_kst(dt: datetime) -> str:
    """2026-10-05T05:03:22Z -> '2026년 10월 5일 14시 03분 22초'"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    k = dt.astimezone(KST)
    return f"{k.year}년 {k.month}월 {k.day}일 {k.hour:02d}시 {k.minute:02d}분 {k.second:02d}초"


def _row(label: str, value: str, last: bool = False) -> str:
    border = "" if last else "border-bottom:1px solid #e5e7eb;"
    return f"""\
            <tr><td style="padding:16px 18px;{border}">
              <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">{label}</div>
              <div style="font-size:16px;font-weight:600;color:#111827;word-break:break-all;">{value}</div>
            </td></tr>"""


def _signup_html(username: str, display_name: str, signed_up_at: str, admin_url: str) -> str:
    u, t, url = html.escape(username), html.escape(signed_up_at), html.escape(admin_url, quote=True)
    rows = [_row("아이디", u)]
    if display_name:
        rows.append(_row("표시 이름", html.escape(display_name)))
    rows.append(_row("가입 일시 (한국 시간)", t, last=True))
    # 메일 클라이언트(특히 Gmail/Outlook)는 <style>과 flex를 제대로 지원하지 않아서
    # 테이블 + 인라인 스타일로만 짠다.
    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{u} 님이 가입했습니다. 승인을 기다리고 있어요.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;
                    font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;">
        <tr><td style="background:{INK};padding:22px 28px;">
          <span style="color:#f9a8d4;font-size:18px;font-weight:700;letter-spacing:.3px;">{APP_NAME}</span>
          <span style="color:#9ca3af;font-size:13px;margin-left:8px;">관리자 알림</span>
        </td></tr>

        <tr><td style="padding:32px 28px 8px;">
          <div style="display:inline-block;background:#fdf2f8;color:#be185d;font-size:12px;font-weight:600;
                      padding:4px 10px;border-radius:999px;">승인 대기</div>
          <h1 style="margin:14px 0 8px;font-size:22px;line-height:1.4;color:#111827;">새 회원이 가입했어요</h1>
          <p style="margin:0;font-size:15px;line-height:1.6;color:#4b5563;">
            아래 회원이 가입을 신청했습니다. 승인해야 로그인할 수 있어요.
          </p>
        </td></tr>

        <tr><td style="padding:20px 28px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;">
{chr(10).join(rows)}
          </table>
        </td></tr>

        <tr><td align="center" style="padding:8px 28px 32px;">
          <a href="{url}" target="_blank"
             style="display:inline-block;background:{BRAND};color:#ffffff;text-decoration:none;font-size:15px;
                    font-weight:700;padding:14px 28px;border-radius:10px;">관리자 페이지에서 승인하기</a>
          <p style="margin:14px 0 0;font-size:12px;color:#9ca3af;word-break:break-all;">
            버튼이 안 눌리면 이 주소로 들어가세요: <a href="{url}" style="color:#6b7280;">{url}</a>
          </p>
        </td></tr>

        <tr><td style="background:#f9fafb;padding:16px 28px;border-top:1px solid #e5e7eb;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#9ca3af;">
            이 메일은 {APP_NAME} 회원가입 시 자동으로 발송됩니다.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _signup_text(username: str, display_name: str, signed_up_at: str, admin_url: str) -> str:
    lines = [f"[{APP_NAME}] 새 회원가입 승인 요청", "", f"아이디: {username}"]
    if display_name:
        lines.append(f"표시 이름: {display_name}")
    lines += [
        f"가입 일시: {signed_up_at} (한국 시간)",
        "",
        "승인해야 로그인할 수 있어요. 아래 관리자 페이지에서 승인해 주세요.",
        admin_url,
        "",
    ]
    return "\n".join(lines)


def build_signup_message(username: str, display_name: str, created_at: datetime) -> EmailMessage | None:
    recipients = [e.strip() for e in _env("ADMIN_NOTIFY_EMAILS").split(",") if e.strip()]
    if not recipients:
        return None

    signed_up_at = format_kst(created_at)
    admin_url = _env("PUBLIC_WEB_URL", "http://localhost:5000").rstrip("/") + "/admin/"
    sender = _env("SMTP_FROM") or _env("SMTP_USER")

    msg = EmailMessage()
    msg["Subject"] = f"[{APP_NAME}] {username} 님이 가입했어요 — 승인해 주세요"
    msg["From"] = formataddr((f"{APP_NAME} 알림", sender))
    msg["To"] = ", ".join(recipients)
    msg["Message-ID"] = make_msgid(domain="instagram-insight.local")
    msg.set_content(_signup_text(username, display_name, signed_up_at, admin_url))
    msg.add_alternative(_signup_html(username, display_name, signed_up_at, admin_url), subtype="html")
    return msg


def send_signup_notification(username: str, display_name: str, created_at: datetime) -> None:
    user, password = _env("SMTP_USER"), _env("SMTP_PASSWORD")
    if not (user and password):
        logger.warning("SMTP 설정이 없어 가입 알림 메일을 건너뜁니다 (%s)", username)
        return
    msg = build_signup_message(username, display_name, created_at)
    if msg is None:
        return

    host, port = _env("SMTP_HOST", "smtp.gmail.com"), int(_env("SMTP_PORT", "587"))
    try:
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.starttls(context=context)
                smtp.login(user, password)
                smtp.send_message(msg)
        logger.info("가입 알림 메일 발송: %s -> %s", username, msg["To"])
    except Exception:
        logger.exception("가입 알림 메일 발송 실패 (%s)", username)


def notify_signup_async(username: str, display_name: str) -> None:
    """가입 직후 호출 — 요청 스레드를 붙잡지 않도록 데몬 스레드에서 보낸다."""
    created_at = datetime.now(timezone.utc)
    threading.Thread(
        target=send_signup_notification, args=(username, display_name, created_at), daemon=True
    ).start()
