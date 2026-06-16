import io
import csv
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from services.follower_service import (
    get_followers,
    get_following,
    get_not_following_back,
    get_only_following_me,
    get_mutual,
    get_stats,
    get_unfollower_history,
    get_recently_unfollowed,
)

bp = Blueprint("followers", __name__)


def _data_dir():
    return current_user.data_dir


@bp.route("/followers")
@login_required
def followers_page():
    search    = request.args.get("search", "")
    sort      = request.args.get("sort", "newest")
    from_date = request.args.get("from_date", "")
    to_date   = request.args.get("to_date", "")
    data  = get_followers(_data_dir(), search, sort, from_date, to_date)
    stats = get_stats(_data_dir())
    return render_template("followers.html", data=data, stats=stats,
                           search=search, sort=sort, from_date=from_date, to_date=to_date)


@bp.route("/following")
@login_required
def following_page():
    search    = request.args.get("search", "")
    sort      = request.args.get("sort", "newest")
    from_date = request.args.get("from_date", "")
    to_date   = request.args.get("to_date", "")
    data  = get_following(_data_dir(), search, sort, from_date, to_date)
    stats = get_stats(_data_dir())
    return render_template("following.html", data=data, stats=stats,
                           search=search, sort=sort, from_date=from_date, to_date=to_date)


@bp.route("/unfollowers")
@login_required
def unfollowers_page():
    tab    = request.args.get("tab", "not_following_back")
    search = request.args.get("search", "")
    stats  = get_stats(_data_dir(), current_user.id)

    if tab == "not_following_back":
        data = get_not_following_back(_data_dir(), search)
    elif tab == "only_following_me":
        data = get_only_following_me(_data_dir(), search)
    elif tab == "unfollower_events":
        data = get_unfollower_history(current_user.id, search)
    elif tab == "recently_unfollowed":
        data = get_recently_unfollowed(_data_dir(), search)
    else:
        data = get_mutual(_data_dir(), search)

    return render_template("unfollowers.html", data=data, stats=stats, tab=tab, search=search)


# ── JSON API ──────────────────────────────────────────────────────────────────

@bp.route("/api/following")
@login_required
def api_following():
    search    = request.args.get("search", "")
    sort      = request.args.get("sort", "newest")
    from_date = request.args.get("from_date", "")
    to_date   = request.args.get("to_date", "")
    return jsonify(get_following(_data_dir(), search, sort, from_date, to_date))


@bp.route("/api/followers")
@login_required
def api_followers():
    search    = request.args.get("search", "")
    sort      = request.args.get("sort", "newest")
    from_date = request.args.get("from_date", "")
    to_date   = request.args.get("to_date", "")
    return jsonify(get_followers(_data_dir(), search, sort, from_date, to_date))


@bp.route("/api/unfollowers")
@login_required
def api_unfollowers():
    tab    = request.args.get("tab", "not_following_back")
    search = request.args.get("search", "")
    if tab == "not_following_back":
        return jsonify(get_not_following_back(_data_dir(), search))
    elif tab == "only_following_me":
        return jsonify(get_only_following_me(_data_dir(), search))
    elif tab == "unfollower_events":
        return jsonify(get_unfollower_history(current_user.id, search))
    elif tab == "recently_unfollowed":
        return jsonify(get_recently_unfollowed(_data_dir(), search))
    return jsonify(get_mutual(_data_dir(), search))


@bp.route("/api/stats")
@login_required
def api_stats():
    return jsonify(get_stats(_data_dir()))


# ── CSV Export ────────────────────────────────────────────────────────────────

@bp.route("/api/export/csv")
@login_required
def export_csv():
    export_type = request.args.get("type", "followers")

    if export_type == "followers":
        rows     = get_followers(_data_dir())["followers"]
        filename = "followers.csv"
    elif export_type == "following":
        rows     = get_following(_data_dir())["following"]
        filename = "following.csv"
    elif export_type == "not_following_back":
        rows     = get_not_following_back(_data_dir())["accounts"]
        filename = "not_following_back.csv"
    else:
        rows     = get_only_following_me(_data_dir())["accounts"]
        filename = "only_following_me.csv"

    fields = ["username", "followed_at", "profile_url"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        "﻿" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
