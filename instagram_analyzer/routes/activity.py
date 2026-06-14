import io
import csv
from flask import Blueprint, render_template, request, jsonify, Response, current_app
from services.activity_service import search_sent_activity, search_received_activity

bp = Blueprint("activity", __name__)


def _data_dir():
    return current_app.config["DATA_DIR"]


@bp.route("/activity/search")
def activity_page():
    username = request.args.get("username", "")
    direction = request.args.get("direction", "sent")
    activity_type = request.args.get("activity_type", "all")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    data = None
    if username:
        if direction == "sent":
            data = search_sent_activity(_data_dir(), username, activity_type, from_date, to_date)
        else:
            data = search_received_activity(_data_dir(), username, activity_type, from_date, to_date)

    return render_template(
        "activity.html",
        data=data,
        username=username,
        direction=direction,
        activity_type=activity_type,
        from_date=from_date,
        to_date=to_date,
    )


@bp.route("/api/activity")
def api_activity():
    username = request.args.get("username", "")
    direction = request.args.get("type", "sent")
    activity_type = request.args.get("activity_type", "all")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    if not username:
        return jsonify({"error": "username 파라미터가 필요합니다."}), 400

    if direction == "sent":
        return jsonify(search_sent_activity(_data_dir(), username, activity_type, from_date, to_date))
    return jsonify(search_received_activity(_data_dir(), username, activity_type, from_date, to_date))


@bp.route("/api/export/activity/csv")
def export_activity_csv():
    username = request.args.get("username", "unknown")
    direction = request.args.get("direction", "sent")
    activity_type = request.args.get("activity_type", "all")

    if direction == "sent":
        data = search_sent_activity(_data_dir(), username, activity_type)
    else:
        data = search_received_activity(_data_dir(), username, activity_type)

    rows = data.get("activities", [])
    fields = ["type", "occurred_at", "content", "post_url"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    filename = f"activity_{username}_{direction}.csv"
    return Response(
        "﻿" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
