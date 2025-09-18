# OrderFood/customer.py
from flask import Blueprint, render_template, request, session, abort, jsonify, redirect, url_for, flash
from sqlalchemy import func
from sqlalchemy.orm import joinedload


from OrderFood import db, dao_index
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
def update_restaurant_rating(restaurant_id: int):
    subq = (
        db.session.query(OrderRating.rating)
        .join(Order, OrderRating.order_id == Order.order_id)
        .filter(Order.restaurant_id == restaurant_id,
                OrderRating.rating >= 1, OrderRating.rating <= 5)
        .order_by(OrderRating.orating_id.desc())
        .limit(20)
        .subquery()
    )

    avg_rating = db.session.query(func.avg(subq.c.rating)).scalar()

    res = Restaurant.query.get(restaurant_id)
    if res:
        res.rating_point = float(avg_rating or 0)
        db.session.commit()

# ============== routes render customer/*.html ==============

@customer_bp.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    res = dao_index.get_restaurant_by_id(restaurant_id)
    if not res:
        abort(404)

    dishes = Dish.query.filter_by(res_id=restaurant_id).all()
    categories = Category.query.filter_by(res_id=restaurant_id).all()
    stars = dao_index.get_star_display(res.rating_point or 0)

    cart_items_count = 0
    user_id = session.get("user_id")
    if user_id:
        from sqlalchemy import or_

        cart = Cart.query.filter(
            Cart.cus_id == user_id,
            Cart.res_id == res.restaurant_id,
            or_(Cart.status == StatusCart.ACTIVE, Cart.status == StatusCart.SAVED)
        ).first()

        if cart and cart.items:
            cart_items_count = sum(item.quantity or 0 for item in cart.items)

    return render_template(
        "/customer/restaurant_detail.html",
        res=res,
        dishes=dishes,
        stars=stars,
        categories=categories,
        cart_items_count=cart_items_count,
    )  # :contentReference[oaicite:4]{index=4}


@customer_bp.route("/cart/<int:restaurant_id>")
def cart(restaurant_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Bạn chưa đăng nhập"}), 403

    customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        return jsonify({"error": "Bạn không phải là khách hàng"}), 403
    cart = Cart.query.filter_by(cus_id=customer.user_id, res_id=restaurant_id, status=StatusCart.ACTIVE).first()
    cart_items = []
    total_price = 0

    if cart:
        cart_items = cart.items
        total_price = sum(item.quantity * item.dish.price for item in cart_items)

    return render_template("/customer/cart.html", cart=cart, cart_items=cart_items, total_price=total_price)


@customer_bp.route("/orders")
def my_orders():
    uid = session.get("user_id")
    if not uid:
        # để đúng yêu cầu, không redirect ra template ngoài /customer/*
        # view list orders chỉ khả dụng khi đã đăng nhập
        abort(403)

    if not is_customer(session.get("role")):
        abort(403)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status_filter = (request.args.get("status") or "").strip().upper()

    q = Order.query.filter_by(customer_id=uid).order_by(Order.created_date.desc())
    if status_filter in ("PENDING", "PAID", "ACCEPT", "ACCEPTED", "CANCELED", "COMPLETED"):
        if status_filter == "ACCEPT":
            status_filter = "ACCEPTED"
        q = q.filter(Order.status == getattr(StatusOrder, status_filter))

    total = q.count()
    orders = q.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "customer/orders_list.html",
        orders=orders, page=page, per_page=per_page,
        total=total, total_pages=total_pages, status_filter=status_filter
    )





@customer_bp.route("/customer")
def customer_home():
    if not is_customer(session.get("role")):
        return redirect(url_for("login"))

    restaurants = Restaurant.query.limit(50).all()
    restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)

    restaurants_with_stars = []
    for r in restaurants:
        restaurants_with_stars.append({
            "restaurant": r,
            "stars": dao_index.get_star_display(r.rating_point or 0)
        })

    return render_template("customer_home.html", restaurants=restaurants_with_stars)

@customer_bp.route("/notifications/json")
def notifications_json():
    uid = session.get("user_id")
    if not uid or not is_customer(session.get("role")):
        return jsonify({"items": [], "unread_count": 0}), 200

    # Lấy noti của chính customer qua JOIN với order
    items = (db.session.query(Notification)
             .join(Order, Notification.order_id == Order.order_id)
             .filter(Order.customer_id == uid)
             .order_by(Notification.create_at.desc())
             .limit(30)
             .all())

    def to_dict(n):
        return {
            "id": n.noti_id,
            "order_id": n.order_id,
            "message": n.message,
            "created_at": n.create_at.strftime("%H:%M %d/%m/%Y") if n.create_at else "",
            "is_read": bool(n.is_read),
        }

    unread = sum(0 if n.is_read else 1 for n in items)
    return jsonify({"items": [to_dict(n) for n in items], "unread_count": unread}), 200


@customer_bp.route("/notifications/open/<int:noti_id>")
def notifications_open(noti_id):
    uid = session.get("user_id")
    if not uid or not is_customer(session.get("role")):
        abort(403)

    n = Notification.query.get_or_404(noti_id)
    # Xác thực chủ đơn qua quan hệ n.order (đã có relationship)
    if not n.order or n.order.customer_id != uid:
        abort(403)

    n.is_read = True
    db.session.commit()
    return redirect(url_for("customer.order_track", order_id=n.order_id))


@customer_bp.route("/notifications/mark-all-read", methods=["POST"])
def notifications_mark_all_read():
    uid = session.get("user_id")
    if not uid or not is_customer(session.get("role")):
        abort(403)

    # Đánh dấu tất cả noti của uid là đã đọc (JOIN để lọc theo chủ đơn)
    (db.session.query(Notification)
       .join(Order, Notification.order_id == Order.order_id)
       .filter(Order.customer_id == uid, Notification.is_read == False)
       .update({"is_read": True}, synchronize_session=False))
    db.session.commit()
    return jsonify({"ok": True})


@customer_bp.route("/order/<int:order_id>/rate", methods=["POST"])
def order_rate(order_id):
    uid = session.get("user_id") or abort(403)
    order = Order.query.get_or_404(order_id)
    if order.customer_id != uid:
        abort(403)

    # Chỉ cho đánh giá khi hoàn tất
    if (getattr(order.status, "value", order.status) or "").upper() != "COMPLETED":
        flash("Chỉ có thể đánh giá khi đơn đã giao thành công.", "warning")
        return redirect(url_for("customer.order_track", order_id=order_id))

    # Chặn đánh giá lại
    if OrderRating.query.filter_by(order_id=order_id, customer_id=uid).first():
        flash("Bạn đã đánh giá đơn hàng này rồi.", "warning")
        return redirect(url_for("customer.order_track", order_id=order_id))

    rating = request.form.get("rating", type=int)
    comment = (request.form.get("comment") or "").strip()
    if not rating or rating < 1 or rating > 5:
        flash("Điểm đánh giá không hợp lệ.", "danger")
        return redirect(url_for("customer.order_track", order_id=order_id))

    db.session.add(OrderRating(order_id=order_id, customer_id=uid, rating=rating, comment=comment))
    db.session.commit()
    update_restaurant_rating(order.restaurant_id)
    flash("Cảm ơn bạn đã đánh giá!", "success")
    return redirect(url_for("customer.order_track", order_id=order_id))

@customer_bp.route("/order/<int:order_id>/track")
def order_track(order_id):
    uid = session.get("user_id")
    if not uid:
        abort(403)

    order = Order.query.get_or_404(order_id)
    if order.customer_id != uid and (session.get("role") or "").upper() != "ADMIN":
        abort(403)

    s = (getattr(order.status, "value", order.status) or "").upper()
    is_paid      = (s == "PAID")
    is_accepted  = (s in ("ACCEPTED", "ACCEPT"))
    is_canceled  = (s == "CANCELED")
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

    # === thông tin đánh giá ===
    rated = OrderRating.query.filter_by(order_id=order_id, customer_id=uid).first()
    has_rated = bool(rated)
    user_rating = rated.rating if rated else None
    user_comment = rated.comment if rated else None

    return render_template(
        "customer/order_track.html",
        order=order,
        active_idx=active_idx,
        last_label=last_label,
        status_str=s,
        is_completed=is_completed,
        has_rated=has_rated,
        user_rating=user_rating,
        user_comment=user_comment,
    )
