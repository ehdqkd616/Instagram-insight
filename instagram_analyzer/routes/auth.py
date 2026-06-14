import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import create_user, find_user_by_username

bp = Blueprint("auth", __name__)
logger = logging.getLogger("instagram_analyzer.auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = find_user_by_username(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            logger.info("로그인 성공: user_id=%d username=%r", user.id, user.username)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        logger.warning("로그인 실패: username=%r", username)
        flash("아이디 또는 비밀번호가 올바르지 않습니다.", "danger")

    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username     = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm", "")

        error = None
        if not username or not password:
            error = "아이디와 비밀번호를 입력해주세요."
        elif len(username) < 3:
            error = "아이디는 3자 이상이어야 합니다."
        elif len(password) < 6:
            error = "비밀번호는 6자 이상이어야 합니다."
        elif password != confirm:
            error = "비밀번호가 일치하지 않습니다."

        if error:
            flash(error, "danger")
        else:
            user = create_user(username, password, display_name)
            if user is None:
                flash("이미 사용 중인 아이디입니다.", "danger")
            else:
                flash("회원가입이 완료됐습니다. 로그인해주세요.", "success")
                return redirect(url_for("auth.login"))

    return render_template("register.html")


@bp.route("/logout")
@login_required
def logout():
    logger.info("로그아웃: user_id=%d username=%r", current_user.id, current_user.username)
    logout_user()
    flash("로그아웃됐습니다.", "info")
    return redirect(url_for("auth.login"))
