from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import get_upload_history, delete_upload_history_entry

bp = Blueprint("history", __name__)


@bp.route("/history")
@login_required
def history_page():
    history = get_upload_history(current_user.id)

    # 오래된 순으로 변화량(diff) 계산 후 다시 최신순으로 정렬
    chrono = list(reversed(history))
    prev = None
    for h in chrono:
        if prev:
            h["diff_followers"] = h["followers_count"] - prev["followers_count"]
            h["diff_following"] = h["following_count"] - prev["following_count"]
            h["diff_mutual"]    = h["mutual_count"] - prev["mutual_count"]
        else:
            h["diff_followers"] = None
            h["diff_following"] = None
            h["diff_mutual"]    = None
        prev = h
    history = list(reversed(chrono))

    first = history[-1] if history else None
    latest = history[0] if history else None
    total_growth_followers = (
        latest["followers_count"] - first["followers_count"]
        if first and latest and first is not latest else None
    )

    return render_template(
        "history.html",
        history=history,
        total_growth_followers=total_growth_followers,
    )


@bp.route("/history/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete_entry(entry_id):
    delete_upload_history_entry(current_user.id, entry_id)
    flash("히스토리 기록이 삭제됐습니다.", "info")
    return redirect(url_for("history.history_page"))
