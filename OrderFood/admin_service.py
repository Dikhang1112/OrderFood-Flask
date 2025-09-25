from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from flask import current_app
from datetime import datetime
from sqlalchemy import func, extract
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from OrderFood import db
from OrderFood.dao.restaurant_dao import get_all_restaurants, get_restaurant_by_id
from OrderFood.dao.user_dao import get_all_user
from OrderFood.email_service import send_restaurant_status_email
from OrderFood.models import StatusRes, Order, StatusOrder, Customer, Role, Notification, Restaurant, User, \
    RestaurantOwner
from sqlalchemy.orm import joinedload

from OrderFood.notifications import push_customer_noti_on_completed

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def is_admin(role) -> bool:
    # lấy .value nếu là Enum, còn không thì giữ nguyên
    rolestr = getattr(role, "value", role)
    return (str(rolestr) or "").lower() == "admin"


@admin_bp.route("/")
def admin_home():
    current_year = datetime.now().year
    if not is_admin(session.get("role")):
        flash("Bạn không có quyền truy cập trang admin", "danger")
        return redirect(url_for("index"))
    return render_template("admin/admin_home.html", current_year=current_year)


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
    if not is_admin(session.get("role")):
        flash("Bạn không có quyền truy cập trang admin", "danger")
        return redirect(url_for("index"))

    orders = (
        Order.query
        .options(
            joinedload(Order.customer).joinedload(Customer.user),
            joinedload(Order.restaurant)
        )
        .order_by(Order.created_date.desc())
        .all()
    )
    waiting_time = current_app.config.get("WAITING_TIME", 10)
    return render_template("admin/admin_delivery.html",
                           orders=orders,
                           current_waiting_time=waiting_time)


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

@admin_bp.route("/delivery/mark_completed/<int:order_id>", methods=["POST"])
def mark_completed(order_id):
    """Cập nhật trạng thái order sang COMPLETED và gán delivery_id = admin_id"""
    if not is_admin(session.get("role")):
        return jsonify({"error": "forbidden"}), 403

    order = Order.query.get_or_404(order_id)

    # so sánh Enum trực tiếp cho chắc
    if order.status == StatusOrder.ACCEPTED:
        admin_id = session.get("user_id")  # id admin đăng nhập
        if not admin_id:
            flash("Không xác định được admin đang đăng nhập!", "danger")
            return redirect(url_for("admin.admin_delivery"))

        order.delivery_id = admin_id
        order.status = StatusOrder.COMPLETED
        db.session.commit()

        # tạo noti cho CUSTOMER (owner_id = None)
        push_customer_noti_on_completed(order)

    return redirect(url_for("admin.admin_delivery"))

@admin_bp.route("/cancel/<int:order_id>", methods=["POST"])
def cancel_order(order_id: int):
    """
    Khi admin nhấn hủy -> canceled_by = CUSTOMER.
    Gửi noti cho res_owner: "Đơn hàng của bạn bị hủy bởi phía khách hàng."
    """
    # kiểm tra quyền
    role = session.get("role")
    if not role or str(getattr(role, "value", role)).lower() != "admin":
        return jsonify({"error": "forbidden"}), 403

    order = Order.query.get_or_404(order_id)

    if order.status in (StatusOrder.PENDING, StatusOrder.ACCEPTED, StatusOrder.PAID):
        order.status = StatusOrder.CANCELED
        order.canceled_by = Role.CUSTOMER  # ✅

        # ===== Lấy res_owner_id từ bảng restaurant qua join =====
        res_owner_id = (
            db.session.query(Restaurant.res_owner_id)
            .filter(Restaurant.restaurant_id == order.restaurant_id)
            .scalar()
        )

        # ===== Tạo noti cho RESTAURANT_OWNER =====
        if res_owner_id:
            noti = Notification(
                order_id=order.order_id,
                message=f"Đơn hàng #{order.order_id} của bạn bị hủy bởi phía khách hàng.",
                owner_id=res_owner_id,   # ✅ gửi cho chủ nhà hàng
                customer_id=None
            )
            db.session.add(noti)

        db.session.commit()
        flash(f"Đã hủy đơn hàng #{order.order_id}.", "success")
    else:
        flash("Chỉ có thể hủy đơn ở trạng thái PENDING/ACCEPTED/PAID.", "warning")

    return redirect(url_for("admin.admin_delivery"))


from flask import request

@admin_bp.route("/api/stats/users-owners")
def stats_users_owners():
    if not is_admin(session.get("role")):
        return jsonify({"error": "forbidden"}), 403

    period = request.args.get("period", "month")
    year = int(request.args.get("year", datetime.now().year))

    labels, users, owners = [], [], []

    if period == "month":
        labels = [f"Tháng {i}" for i in range(1, 13)]
        months = range(1, 13)
        for m in months:
            u_count = db.session.query(func.count(Customer.user_id)) \
                .join(User, Customer.user_id == User.user_id) \
                .filter(extract("month", User.created_date) == m,
                        extract("year", User.created_date) == year) \
                .scalar() or 0

            o_count = db.session.query(func.count(RestaurantOwner.user_id)) \
                .join(User, RestaurantOwner.user_id == User.user_id) \
                .filter(extract("month", User.created_date) == m,
                        extract("year", User.created_date) == year) \
                .scalar() or 0

            users.append(u_count)
            owners.append(o_count)

    elif period == "quarter":
        labels = [f"Quý {i}" for i in range(1, 5)]
        quarters = [(1,3),(4,6),(7,9),(10,12)]
        for start, end in quarters:
            u_count = db.session.query(func.count(Customer.user_id)) \
                .join(User, Customer.user_id == User.user_id) \
                .filter(extract("month", User.created_date).between(start, end),
                        extract("year", User.created_date) == year) \
                .scalar() or 0

            o_count = db.session.query(func.count(RestaurantOwner.user_id)) \
                .join(User, RestaurantOwner.user_id == User.user_id) \
                .filter(extract("month", User.created_date).between(start, end),
                        extract("year", User.created_date) == year) \
                .scalar() or 0

            users.append(u_count)
            owners.append(o_count)


    return jsonify({
        "labels": labels,
        "users": users,
        "owners": owners
    })


@admin_bp.route("/api/stats/transactions")
def stats_transactions():
    if not is_admin(session.get("role")):
        return jsonify({"error": "forbidden"}), 403

    period = request.args.get("period", "month")  # month / quarter / year
    year = int(request.args.get("year", datetime.now().year))

    labels, transactions = [], []

    if period == "month":
        labels = [f"Tháng {i}" for i in range(1, 13)]
        months = range(1, 13)
        for m in months:
            t_count = db.session.query(func.count(Order.order_id)) \
                .filter(extract("month", Order.created_date) == m,
                        extract("year", Order.created_date) == year,
                        Order.status == StatusOrder.COMPLETED) \
                .scalar() or 0
            transactions.append(t_count)

    elif period == "quarter":
        labels = [f"Quý {i}" for i in range(1,5)]
        quarters = [(1,3),(4,6),(7,9),(10,12)]
        for start,end in quarters:
            t_count = db.session.query(func.count(Order.order_id)) \
                .filter(extract("month", Order.created_date).between(start, end),
                        extract("year", Order.created_date) == year,
                        Order.status == StatusOrder.COMPLETED) \
                .scalar() or 0
            transactions.append(t_count)

    return jsonify({
        "labels": labels,
        "transactions": transactions
    })


@admin_bp.route("/manage_user")
def manage_user():
    users = get_all_user()  # trả về tất cả user (trừ admin)

    customers = [u for u in users if u.role == Role.CUSTOMER]
    owners = [u for u in users if u.role == Role.RESTAURANT_OWNER]

    return render_template(
        "admin/manage_user.html",
        customers=customers,
        owners=owners
    )


@admin_bp.route("/<int:user_id>/delete_customer", methods=["DELETE"])
def delete_customer(user_id: int):
    try:
        customer = Customer.query.get(user_id)
        if not customer:
            return jsonify({"error": "not_found"}), 404

        # Xóa  Payment liên quan đến cus
        for order in customer.orders:
            if order.payment:
                db.session.delete(order.payment)

        # Xóa orderating của cus
        for rating in customer.ratings:
            db.session.delete(rating)

        #  Xóa Notification
        notifications = Notification.query.filter_by(customer_id=user_id).all()
        for noti in notifications:
            db.session.delete(noti)

        # Xóa Order
        for order in customer.orders:
            db.session.delete(order)

        #  Xóa CartItem + Cart
        for cart in customer.carts:
            for item in cart.items:
                db.session.delete(item)
            db.session.delete(cart)

        #  Xóa Customer và User
        db.session.delete(customer)
        db.session.delete(customer.user)

        db.session.commit()
        return jsonify({"message": "deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/<int:user_id>/delete_owner", methods=["DELETE"])
def delete_owner(user_id: int):
    if not is_admin(session.get("role")):
        return jsonify({"error": "forbidden"}), 403

    user = User.query.get(user_id)
    if not user or user.role.name != "RESTAURANT_OWNER":
        return jsonify({"error": "not_found"}), 404

    try:
        if user.restaurant_owner:
            if user.restaurant_owner.restaurant:
                db.session.delete(user.restaurant_owner.restaurant)
            db.session.delete(user.restaurant_owner)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"ok": True, "id": user_id})
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
