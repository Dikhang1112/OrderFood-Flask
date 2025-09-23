# OrderFood/customer.py

from flask import Blueprint, render_template, request, session, abort, jsonify, redirect, url_for, flash

from OrderFood.dao import customer_dao as dao_cus
from OrderFood.models import (
    Restaurant, Dish, Category,
    Cart, CartItem, Customer,
    Order, StatusOrder, StatusCart, Notification, OrderRating
)

customer_bp = Blueprint("customer", __name__)


# ============== helpers ==============
def _role_to_str(r):
    return getattr(r, "value", r)


def is_customer(role: str) -> bool:
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "customer"


from datetime import datetime

def is_restaurant_open(restaurant):
    if not restaurant.is_open:
        return False
    try:
        open_time = datetime.strptime(restaurant.open_hour, "%H:%M").time()
        close_time = datetime.strptime(restaurant.close_hour, "%H:%M").time()
        now = datetime.now().time()
        return open_time <= now <= close_time
    except Exception as e:
        # Trường hợp open_hour/close_hour không hợp lệ
        return False


# ============== routes render customer/*.html ==============

@customer_bp.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    res = dao_cus.get_restaurant_by_id(restaurant_id)
    if not res:
        abort(404)

    dishes, categories = dao_cus.get_restaurant_menu_and_categories(restaurant_id)
    stars = dao_cus.get_star_display(res.rating_point or 0)

    # --- NEW: gom món theo category_id ---
    dishes_by_category = {}
    for c in categories:
        cid = getattr(c, "category_id", getattr(c, "id", None))
        if cid is not None:
            dishes_by_category[cid] = [d for d in dishes if d.category_id == cid]

    cart_items_count = 0
    user_id = session.get("user_id")
    is_open = is_restaurant_open(res)
    if user_id:
        cart = dao_cus.get_active_cart(user_id, res.restaurant_id)
        cart_items_count = dao_cus.count_cart_items(cart)

    return render_template(
        "/customer/restaurant_detail.html",
        res=res,
        dishes=dishes,  # giữ nguyên để không phá chỗ khác
        stars=stars,
        categories=categories,
        cart_items_count=cart_items_count,
        dishes_by_category=dishes_by_category,  # --- NEW
        is_open=is_open
    )


@customer_bp.route("/cart/<int:restaurant_id>")
def cart(restaurant_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Bạn chưa đăng nhập"}), 403

    customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        return jsonify({"error": "Bạn không phải là khách hàng"}), 403

    cart = dao_cus.get_active_cart(customer.user_id, restaurant_id)
    cart_items = cart.items if cart else []
    total_price = sum(item.quantity * item.dish.price for item in cart_items) if cart_items else 0
    is_open = is_restaurant_open(Restaurant.query.filter_by(restaurant_id=restaurant_id).first())
    return render_template("/customer/cart.html", cart=cart, cart_items=cart_items, total_price=total_price
                           , is_open=is_open)

@customer_bp.route("/orders")
def my_orders():
    uid = session.get("user_id")
    if not uid:
        abort(403)
    if not is_customer(session.get("role")):
        abort(403)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status_filter = (request.args.get("status") or "").strip().upper()

    orders, total = dao_cus.list_customer_orders(uid, status_filter, page, per_page)
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "customer/orders_list.html",
        orders=orders, page=page, per_page=per_page,
        total=total, total_pages=total_pages, status_filter=status_filter
    )



@customer_bp.route("/order/<int:order_id>/track")
def order_track(order_id):
    uid = session.get("user_id")
    if not uid:
        abort(403)

    order = Order.query.get_or_404(order_id)
    # chỉ chủ đơn (hoặc admin) mới xem được
    if order.customer_id != uid and (session.get("role") or "").upper() != "ADMIN":
        abort(403)

    s = getattr(order.status, "value", order.status) or ""
    s = s.upper()
    is_paid = (s == "PAID")
    is_accepted = (s in ("ACCEPTED", "ACCEPT"))
    is_canceled = (s == "CANCELED")
    is_completed = (s == "COMPLETED")

    if is_paid:
        active_idx = 0
    elif is_accepted:
        active_idx = 1
    elif is_canceled or is_completed:
        active_idx = 2
    else:
        active_idx = -1

    last_label = "Đã hủy" if is_canceled else "Đã giao hàng thành công"

    return render_template(
        "customer/order_track.html",
        order=order, active_idx=active_idx, last_label=last_label, status_str=s
    )



@customer_bp.route("/customer")
def customer_home():
    if not is_customer(session.get("role")):
        return redirect(url_for("login"))

    restaurants = dao_cus.list_top_restaurants(limit=50)
    restaurants_with_stars = [
        {"restaurant": r, "stars": dao_cus.get_star_display(r.rating_point or 0)}
        for r in restaurants
    ]
    return render_template("customer_home.html", restaurants=restaurants_with_stars)

@customer_bp.route("/notifications/json")
def notifications_json():
    uid = session.get("user_id")
    if not uid or not is_customer(session.get("role")):
        return jsonify({"items": [], "unread_count": 0}), 200

    items, unread = dao_cus.list_customer_notifications(uid, limit=30)

    def to_dict(n):
        return {
            "id": n.noti_id,
            "order_id": n.order_id,
            "message": n.message,
            "created_at": n.create_at.strftime("%H:%M %d/%m/%Y") if n.create_at else "",
            "is_read": bool(n.is_read),
        }

    return jsonify({"items": [to_dict(n) for n in items], "unread_count": unread}), 200

@customer_bp.route("/notifications/open/<int:noti_id>")
def notifications_open(noti_id):
    uid = session.get("user_id")
    if not uid or not is_customer(session.get("role")):
        abort(403)

    order_id = dao_cus.open_notification(noti_id, uid)
    return redirect(url_for("customer.order_track", order_id=order_id))

@customer_bp.route("/notifications/mark-all-read", methods=["POST"])
def notifications_mark_all_read():
    uid = session.get("user_id")
    if not uid or not is_customer(session.get("role")):
        abort(403)

    dao_cus.mark_all_notifications_read(uid)
    return jsonify({"ok": True})

@customer_bp.route("/order/<int:order_id>/rate", methods=["POST"])
def order_rate(order_id):
    uid = session.get("user_id") or abort(403)
    order = dao_cus.get_order_for_customer_or_admin(order_id, uid, (session.get("role") or "").upper())

    if not dao_cus.can_rate_order(order, uid):
        flash("Chỉ có thể đánh giá khi đơn đã giao thành công.", "warning")
        return redirect(url_for("customer.order_track", order_id=order_id))

    if dao_cus.has_rated(order_id, uid):
        flash("Bạn đã đánh giá đơn hàng này rồi.", "warning")
        return redirect(url_for("customer.order_track", order_id=order_id))

    rating = request.form.get("rating", type=int)
    comment = (request.form.get("comment") or "").strip()
    if not rating or rating < 1 or rating > 5:
        flash("Điểm đánh giá không hợp lệ.", "danger")
        return redirect(url_for("customer.order_track", order_id=order_id))

    dao_cus.add_order_rating(order_id, uid, rating, comment)
    dao_cus.update_restaurant_rating(order.restaurant_id)
    flash("Cảm ơn bạn đã đánh giá!", "success")
    return redirect(url_for("customer.order_track", order_id=order_id))

@customer_bp.route("/order/<int:order_id>/track")
def order_track(order_id):
    uid = session.get("user_id") or abort(403)
    role_upper = (session.get("role") or "").upper()
    order = dao_cus.get_order_for_customer_or_admin(order_id, uid, role_upper)

    status_str = (getattr(order.status, "value", order.status) or "").upper()
    active_idx, last_label, is_completed = dao_cus.compute_track_state(status_str)

    rated = OrderRating.query.filter_by(order_id=order_id, customer_id=uid).first()
    has_rated = bool(rated)
    user_rating = rated.rating if rated else None
    user_comment = rated.comment if rated else None

    return render_template(
        "customer/order_track.html",
        order=order,
        active_idx=active_idx,
        last_label=last_label,
        status_str=status_str,
        is_completed=is_completed,
        has_rated=has_rated,
        user_rating=user_rating,
        user_comment=user_comment,
    )


