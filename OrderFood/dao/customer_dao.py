from __future__ import annotations
from typing import List, Tuple, Optional
from sqlalchemy import func, or_
from OrderFood import db, dao_index
from OrderFood.models import (
    Restaurant, Dish, Category,
    Cart, Order, Notification, OrderRating,
    StatusOrder, StatusCart
)


# --------- Restaurant & menu ----------
def get_restaurant_by_id(restaurant_id: int) -> Optional[Restaurant]:
    return Restaurant.query.get(restaurant_id)


def get_restaurant_menu_and_categories(restaurant_id: int) -> Tuple[List[Dish], List[Category]]:
    dishes = Dish.query.filter_by(res_id=restaurant_id).all()
    categories = Category.query.filter_by(res_id=restaurant_id).all()
    return dishes, categories


def get_star_display(value: float):

    return dao_index.get_star_display(value or 0)


def list_top_restaurants(limit: int = 50) -> List[Restaurant]:
    rs = Restaurant.query.limit(limit).all()
    rs.sort(key=lambda r: r.rating_point or 0, reverse=True)
    return rs


# --------- Cart ----------
def get_active_cart(user_id: int, restaurant_id: int) -> Optional[Cart]:
    return Cart.query.filter(
        Cart.cus_id == user_id,
        Cart.res_id == restaurant_id,
        or_(Cart.status == StatusCart.ACTIVE, Cart.status == StatusCart.SAVED)
    ).first()


def count_cart_items(cart: Optional[Cart]) -> int:
    if not cart or not cart.items:
        return 0
    return sum((item.quantity or 0) for item in cart.items)


# --------- Orders (customer scope) ----------
def list_customer_orders(uid: int, status_filter: str, page: int, per_page: int) -> Tuple[List[Order], int]:
    q = Order.query.filter_by(customer_id=uid).order_by(Order.created_date.desc())
    if status_filter in ("PENDING", "PAID", "ACCEPT", "ACCEPTED", "CANCELED", "COMPLETED"):
        if status_filter == "ACCEPT":
            status_filter = "ACCEPTED"
        q = q.filter(Order.status == getattr(StatusOrder, status_filter))
    total = q.count()
    orders = q.offset((page - 1) * per_page).limit(per_page).all()
    return orders, total


def get_order_for_customer_or_admin(order_id: int, uid: int, role_upper: str) -> Order:
    order = Order.query.get_or_404(order_id)
    if order.customer_id != uid and role_upper != "ADMIN":
        from flask import abort
        abort(403)
    return order


# --------- Notifications (customer scope) ----------
def list_customer_notifications(uid: int, limit: int = 30) -> Tuple[List[Notification], int]:
    items = (db.session.query(Notification)
             .join(Order, Notification.order_id == Order.order_id)
             .filter(Order.customer_id == uid)
             .order_by(Notification.create_at.desc())
             .limit(limit)
             .all())
    unread = sum(0 if n.is_read else 1 for n in items)
    return items, unread


def open_notification(noti_id: int, uid: int) -> int:
    n = Notification.query.get_or_404(noti_id)
    if not n.order or n.order.customer_id != uid:
        from flask import abort
        abort(403)
    n.is_read = True
    db.session.commit()
    return n.order_id


def mark_all_notifications_read(uid: int) -> None:
    (db.session.query(Notification)
     .join(Order, Notification.order_id == Order.order_id)
     .filter(Order.customer_id == uid, Notification.is_read == False)
     .update({"is_read": True}, synchronize_session=False))
    db.session.commit()


# --------- Ratings ----------
def can_rate_order(order: Order, uid: int) -> bool:
    s = (getattr(order.status, "value", order.status) or "").upper()
    return (order.customer_id == uid) and (s == "COMPLETED")


def has_rated(order_id: int, uid: int) -> bool:
    return OrderRating.query.filter_by(order_id=order_id, customer_id=uid).first() is not None


def add_order_rating(order_id: int, uid: int, rating: int, comment: str) -> None:
    db.session.add(OrderRating(order_id=order_id, customer_id=uid, rating=rating, comment=comment))
    db.session.commit()


def update_restaurant_rating(restaurant_id: int) -> None:
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


# --------- Order track helpers ----------
def compute_track_state(status_str_upper: str):
    is_paid = (status_str_upper == "PAID")
    is_accepted = (status_str_upper in ("ACCEPTED", "ACCEPT"))
    is_canceled = (status_str_upper == "CANCELED")
    is_completed = (status_str_upper == "COMPLETED")

    if is_paid:
        active_idx = 0
    elif is_accepted:
        active_idx = 1
    elif is_canceled or is_completed:
        active_idx = 2
    else:
        active_idx = -1

    last_label = "Đã hủy" if is_canceled else "Đã giao hàng thành công"
    return active_idx, last_label, is_completed
