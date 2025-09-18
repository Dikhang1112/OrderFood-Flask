# OrderFood/notifications.py
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, session, request, url_for, abort
from sqlalchemy import select, desc

from OrderFood import db
from OrderFood.models import Notification, Restaurant, Order


# ===== Helpers =====

def _owner_user_id_from_order(order: Order) -> int | None:
    """order -> restaurant_id -> restaurant.res_owner_id"""
    return db.session.scalar(
        select(Restaurant.res_owner_id).where(Restaurant.restaurant_id == order.restaurant_id)
    )


def push_owner_noti_on_paid(order: Order) -> None:
    """PAID -> noti cho OWNER. (customer_id=None, owner_id=owner)"""
    owner_uid = _owner_user_id_from_order(order)
    if not owner_uid:
        return
    n = Notification(
        order_id=order.order_id,
        message="Bạn có 1 đơn hàng cần xác nhận",
        customer_id=None,
        owner_id=owner_uid,
        is_read=False,
        create_at=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")),
    )
    db.session.add(n)
    db.session.commit()


def push_customer_noti_on_completed(order: Order) -> None:
    """COMPLETED -> noti cho CUSTOMER. (owner_id=None, customer_id=order.customer_id)"""
    if not order.customer_id:
        return
    n = Notification(
        order_id=order.order_id,
        message="Đơn hàng đã được giao thành công",
        customer_id=order.customer_id,
        owner_id=None,
        is_read=False,
        create_at=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")),
    )
    db.session.add(n)
    db.session.commit()


# ===== Blueprint =====

noti_bp = Blueprint("noti", __name__)


def _role_to_str(r):
    return (getattr(r, "value", r) or "").lower()


def _require_auth():
    uid = session.get("user_id")
    role = _role_to_str(session.get("role"))
    if not uid or role not in ("customer", "restaurant_owner"):
        abort(403)
    return uid, role


@noti_bp.get("/notifications/feed")
def notifications_feed():
    """
    Trả về cả đã đọc + chưa đọc (không xóa item),
    kèm 'unread' để hiện badge và 'target_url' để điều hướng.
    """
    uid, role = _require_auth()

    if role == "restaurant_owner":
        q = Notification.query.filter_by(owner_id=uid)
    else:
        q = Notification.query.filter_by(customer_id=uid)

    items = q.order_by(desc(Notification.create_at)).limit(20).all()
    unread = sum(1 for n in items if not n.is_read)

    # URL đích theo role
    data = []
    for n in items:
        if role == "restaurant_owner":
            target_url = url_for("manage_orders")  # trang quản lý đơn của owner
        else:
            target_url = url_for("customer.order_track", order_id=n.order_id)
        data.append({
            "id": n.noti_id,
            "order_id": n.order_id,
            "message": n.message,
            "create_at": n.create_at.strftime("%H:%M %d/%m") if n.create_at else "",
            "is_read": bool(n.is_read),
            "target_url": target_url,
        })

    return jsonify({"items": data, "unread": unread})


@noti_bp.post("/notifications/mark-read")
def notifications_mark_read():
    """
    Đánh dấu đã đọc theo danh sách id (giữ lại item).
    Có kiểm tra quyền dựa trên role + user hiện tại.
    """
    uid, role = _require_auth()
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids", [])
    if not ids:
        return jsonify({"ok": True, "updated": 0})

    # chỉ update những noti thuộc về user hiện tại
    q = Notification.query.filter(Notification.noti_id.in_(ids))
    if role == "restaurant_owner":
        q = q.filter(Notification.owner_id == uid)
    else:
        q = q.filter(Notification.customer_id == uid)

    updated = q.update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"ok": True, "updated": int(updated or 0)})


@noti_bp.post("/notifications/mark-read/<int:noti_id>")
def notifications_mark_read_one(noti_id: int):
    """Đánh dấu 1 noti đã đọc (giữ lại item)."""
    uid, role = _require_auth()

    n = Notification.query.get_or_404(noti_id)
    if (role == "restaurant_owner" and n.owner_id != uid) or \
            (role == "customer" and n.customer_id != uid):
        abort(403)

    if not n.is_read:
        n.is_read = True
        db.session.commit()
    return jsonify({"ok": True})


@noti_bp.post("/notifications/mark-all-read")
def notifications_mark_all_read():
    """Đánh dấu tất cả noti của user hiện tại là đã đọc (không xóa)."""
    uid, role = _require_auth()
    q = Notification.query
    if role == "restaurant_owner":
        q = q.filter_by(owner_id=uid, is_read=False)
    else:
        q = q.filter_by(customer_id=uid, is_read=False)

    updated = q.update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"ok": True, "updated": int(updated or 0)})
