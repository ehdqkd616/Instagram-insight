import glob
import os
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import (
    admin_delete_user, admin_get_all_users, admin_update_user,
    create_user, get_system_stats,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@login_required
@admin_required
def dashboard():
    stats = get_system_stats()
    users = admin_get_all_users()
    return render_template("admin/index.html", stats=stats, users=users)


@bp.route("/users/create", methods=["POST"])
@login_required
@admin_required
def create_user_action():
    username     = request.form.get("username", "").strip()
    display_name = request.form.get("display_name", "").strip()
    password     = request.form.get("password", "")
    is_admin     = bool(request.form.get("is_admin"))

    if not username or not password:
        flash("아이디와 비밀번호를 입력해주세요.", "danger")
        return redirect(url_for("admin.dashboard"))
    if len(password) < 6:
        flash("비밀번호는 6자 이상이어야 합니다.", "danger")
        return redirect(url_for("admin.dashboard"))

    user = create_user(username, password, display_name)
    if user is None:
        flash("이미 사용 중인 아이디입니다.", "danger")
    else:
        if is_admin:
            admin_update_user(user.id, is_admin=True)
        flash(f"사용자 '{username}' 생성 완료.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    from models import find_user_by_id
    target = find_user_by_id(user_id)
    if target is None:
        flash("존재하지 않는 사용자입니다.", "danger")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        new_password = request.form.get("new_password", "").strip()
        is_admin     = bool(request.form.get("is_admin"))

        if new_password and len(new_password) < 6:
            flash("비밀번호는 6자 이상이어야 합니다.", "danger")
            return render_template("admin/edit_user.html", target=target)

        # 마지막 관리자의 관리자 권한은 제거 불가
        if target.is_admin and not is_admin:
            from models import get_system_stats as _gs
            if _gs()["admin_users"] <= 1:
                flash("마지막 관리자의 권한은 제거할 수 없습니다.", "danger")
                return render_template("admin/edit_user.html", target=target)

        admin_update_user(
            user_id,
            display_name=display_name or None,
            is_admin=is_admin,
            new_password=new_password or None,
        )
        flash(f"'{target.username}' 정보가 수정됐습니다.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/edit_user.html", target=target)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    from models import find_user_by_id, get_system_stats as _gs

    if user_id == current_user.id:
        flash("자기 자신은 삭제할 수 없습니다.", "danger")
        return redirect(url_for("admin.dashboard"))

    target = find_user_by_id(user_id)
    if target is None:
        flash("존재하지 않는 사용자입니다.", "danger")
        return redirect(url_for("admin.dashboard"))

    if target.is_admin and _gs()["admin_users"] <= 1:
        flash("마지막 관리자 계정은 삭제할 수 없습니다.", "danger")
        return redirect(url_for("admin.dashboard"))

    admin_delete_user(user_id)
    flash(f"'{target.username}' 계정과 모든 데이터가 삭제됐습니다.", "warning")
    return redirect(url_for("admin.dashboard"))
