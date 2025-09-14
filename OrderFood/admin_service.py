from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from flask import current_app
from sqlalchemy.orm import joinedload

from OrderFood import db
from OrderFood.dao.restaurant_dao import get_all_restaurants, get_restaurant_by_id
from OrderFood.email_service import send_restaurant_status_email
from OrderFood.models import StatusRes,Order

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


@admin_bp.route("/logout")
def admin_logout():
    session.clear()
    flash("Đã đăng xuất", "info")
    return redirect(url_for("index"))


@admin_bp.route("/restaurants")
def admin_restaurant():
    restaurants = get_all_restaurants(limit=50)
    return render_template("admin/restaurants.html", restaurants=restaurants)


@admin_bp.route("/restaurant/detail/<int:restaurant_id>")
def restaurant_detail(restaurant_id: int):
    if not is_admin(session.get("role")):
        flash("Bạn không có quyền truy cập trang admin", "danger")
        return redirect(url_for("index"))

    res = get_restaurant_by_id(restaurant_id)
    if not res:
        flash("Không tìm thấy nhà hàng.", "warning")
        return redirect(url_for("admin.admin_restaurant"))
    # Gợi ý: tạo template 'admin/restaurant_detail.html'
    return render_template("admin/restaurant_detail.html", res=res)


@admin_bp.route("/restaurants/<int:restaurant_id>/reject", methods=["PATCH"])
def reject_restaurant(restaurant_id: int):
    # chỉ cho ADMIN
    role = session.get("role")
    if not role or str(role).lower() != "admin":
        return jsonify({"error": "forbidden"}), 403

    res = get_restaurant_by_id(restaurant_id)
    if not res:
        return jsonify({"error": "not_found"}), 404
    payload = request.get_json(silent=True) or {}
    reason = (payload.get("reason") or "").strip()
    # cập nhật trạng thái
    res.status = StatusRes.REJECTED
    if session.get("user_id"):
        res.by_admin_id = session["user_id"]

    db.session.commit()

    # GỬI MAIL CHO OWNER
    try:
        owner_email = getattr(getattr(res.owner, "user", None), "email", None)
        if owner_email:
            send_restaurant_status_email(owner_email, res.name, "REJECT", reason=reason)
    except Exception:
        current_app.logger.warning("Không gửi được email thông báo REJECT", exc_info=True)

    return jsonify({"ok": True, "id": restaurant_id, "status": res.status.value})


@admin_bp.route("/restaurants/<int:restaurant_id>/approve", methods=["PATCH"])
def approve_restaurant(restaurant_id: int):
    # chỉ cho ADMIN
    role = session.get("role")
    if not role or str(role).lower() != "admin":
        return jsonify({"error": "forbidden"}), 403

    res = get_restaurant_by_id(restaurant_id)
    if not res:
        return jsonify({"error": "not_found"}), 404

    # cập nhật trạng thái
    res.status = StatusRes.APPROVED
    if session.get("user_id"):
        res.by_admin_id = session["user_id"]

    db.session.commit()

    # GỬI MAIL CHO OWNER
    try:
        owner_email = getattr(getattr(res.owner, "user", None), "email", None)
        if owner_email:
            send_restaurant_status_email(owner_email, res.name, "APPROVED")
    except Exception:
        current_app.logger.warning("Không gửi được email thông báo APPROVE", exc_info=True)

    return jsonify({"ok": True, "id": restaurant_id, "status": res.status.value})

@admin_bp.route("/delivery", methods=["GET"])
def admin_delivery():
    """Trang danh sách Orders + ô cập nhật waiting_time"""
    if not is_admin(session.get("role")):
        flash("Bạn không có quyền truy cập trang admin", "danger")
        return redirect(url_for("index"))

    orders = (Order.query
              .options(joinedload(Order.customer), joinedload(Order.restaurant))
              .order_by(Order.created_date.desc())
              .all())
    waiting_time = current_app.config.get("WAITING_TIME", 30)  # mặc định 30 phút

    return render_template(
        "admin/admin_delivery.html",
        orders=orders,
        current_waiting_time=waiting_time
    )


@admin_bp.route("/delivery/set_waiting_time", methods=["POST"])
def set_waiting_time():
    """Cập nhật waiting_time dùng khi tạo Order mới (VD: checkout VNPay)"""
    if not is_admin(session.get("role")):
        return jsonify({"error": "forbidden"}), 403

    wt = request.form.get("waiting_time", type=int)
    if wt and wt > 0:
        current_app.config["WAITING_TIME"] = wt
        flash(f"Đã cập nhật waiting time = {wt} phút", "success")
    else:
        flash("Waiting time không hợp lệ", "danger")

    return redirect(url_for("admin.admin_delivery"))
