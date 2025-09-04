from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify
from OrderFood import db
from OrderFood.dao.restaurant_dao import get_all_restaurants, get_restaurant_by_id
from OrderFood.models import StatusRes

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def is_admin(role) -> bool:
    # lấy .value nếu là Enum, còn không thì giữ nguyên
    rolestr = getattr(role, "value", role)
    return (str(rolestr) or "").lower() == "admin"


@admin_bp.route("/")
def admin_home():
    if not is_admin(session.get("role")):
        flash("Bạn không có quyền truy cập trang admin", "danger")
        return redirect(url_for("index"))
    return render_template("admin/admin_home.html")


@admin_bp.route("/restaurants")
def admin_restaurant():
    restaurants = get_all_restaurants(limit=50)
    return render_template("admin/restaurants.html", restaurants=restaurants)


@admin_bp.route("/restaurants/<int:restaurant_id>/reject", methods=["PATCH"])
def reject_restaurant(restaurant_id: int):
    if not is_admin(session.get("role")):
        return jsonify({"error": "forbidden"}), 403
    res = get_restaurant_by_id(restaurant_id)  # dùng DAO
    if not res:
        return jsonify({"error": "not_found"}), 404
    # cập nhật trạng thái
    res.status = StatusRes.REJECTED
    # lưu lại admin thực hiện
    if session.get("user_id"):
        res.by_admin_id = session["user_id"]
    db.session.commit()
    return jsonify({"ok": True, "id": restaurant_id, "status": res.status.value})
