# OrderFood/customer.py
from flask import Blueprint, render_template, request, session, abort, jsonify,redirect, url_for
from sqlalchemy.orm import joinedload


from OrderFood import db, dao_index
from OrderFood.models import (
    Restaurant, Dish, Category,
    Cart, CartItem, Customer,
    Order, StatusOrder, StatusCart
)

customer_bp = Blueprint("customer", __name__)

# ============== helpers ==============
def _role_to_str(r):
    return getattr(r, "value", r)

def is_customer(role: str) -> bool:
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "customer"

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

    cart = Cart.query.filter_by(
        cus_id=customer.user_id, is_open=True, res_id=restaurant_id
    ).first()

    cart_items, total_price = [], 0
    if cart:
        cart_items = cart.items
        total_price = sum(item.quantity * item.dish.price for item in cart_items)

    return render_template(
        "customer/cart.html",
        cart=cart, cart_items=cart_items, total_price=total_price
    )


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

    return render_template(
        "customer/order_track.html",
        order=order, active_idx=active_idx, last_label=last_label, status_str=s
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
