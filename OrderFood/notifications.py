# OrderFood/notifications.py
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, session, request, url_for, abort
from sqlalchemy import select, desc

from OrderFood import db
from OrderFood.models import Notification, Restaurant, Order


# ========= Helpers =========

_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _now():
    """Trả về thời điểm hiện tại theo Asia/Ho_Chi_Minh (fallback UTC nếu thiếu zoneinfo)."""
    try:
        return datetime.now(_TZ)
    except Exception:
        return datetime.now(timezone.utc)


def _owner_user_id_from_order(order: Order) -> int | None:
    """order -> restaurant_id -> restaurant.res_owner_id"""
    return db.session.scalar(
        select(Restaurant.res_owner_id).where(Restaurant.restaurant_id == order.restaurant_id)
    )


def _role_to_str(r) -> str:
    return (getattr(r, "value", r) or "").lower()


def _require_auth() -> tuple[int, str]:
    uid = session.get("user_id")
    role = _role_to_str(session.get("role"))
    if not uid or role not in ("customer", "restaurant_owner"):
        abort(403)
    return uid, role


def _add_noti(order_id: int, message: str, *, customer_id: int | None, owner_id: int | None) -> None:
    """Tạo 1 bản ghi thông báo (có thể đồng thời cho cả customer & owner)."""
    n = Notification(
        order_id=order_id,
        message=message,
        customer_id=customer_id,
        owner_id=owner_id,
        is_read=False,
        create_at=_now(),
    )
    db.session.add(n)
    db.session.commit()


# ========= Pushers (gọi từ nghiệp vụ) =========

def push_owner_noti_on_paid(order: Order) -> None:
    """Khi đơn PAID -> noti cho OWNER."""
    owner_uid = _owner_user_id_from_order(order)
    if owner_uid:
        _add_noti(order.order_id, "Bạn có 1 đơn hàng cần xác nhận",
                  customer_id=None, owner_id=owner_uid)


def push_customer_noti_on_completed(order: Order) -> None:
    """Khi đơn COMPLETED -> noti cho CUSTOMER."""
    if order.customer_id:
        _add_noti(order.order_id, "Đơn hàng đã được giao thành công",
                  customer_id=order.customer_id, owner_id=None)


def push_both_noti(order: Order, message: str) -> None:
    """
    Tạo 1 thông báo gửi cho CẢ hai phía (customer & owner) trong CÙNG một dòng.
    Ví dụ dùng cho case quá thời gian xác nhận, hệ thống hủy, v.v.
    """
    owner_uid = _owner_user_id_from_order(order)
    _add_noti(order.order_id, message,
              customer_id=order.customer_id, owner_id=owner_uid)


# ========= Blueprint API =========

noti_bp = Blueprint("noti", __name__)


@noti_bp.get("/notifications/feed")
def notifications_feed():
    """
    Trả về cả đã đọc + chưa đọc (KHÔNG đánh dấu đã đọc),
    kèm 'unread' để hiện badge và 'target_url' để điều hướng.
    Query param optional: ?limit=30
    """
    uid, role = _require_auth()
    limit = request.args.get("limit", 30, type=int)

    if role == "restaurant_owner":
        q = Notification.query.filter_by(owner_id=uid)
    else:
        q = Notification.query.filter_by(customer_id=uid)

    items = q.order_by(desc(Notification.create_at)).limit(limit).all()
    unread = sum(1 for n in items if not n.is_read)

    data = []
    for n in items:
        if role == "restaurant_owner":
            # sửa: dùng đúng endpoint của owner
            target_url = url_for("manage_orders")
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
    Chỉ cập nhật các noti thuộc về user hiện tại.
    Body JSON: { "ids": [1,2,3] }
    """
    uid, role = _require_auth()
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids", [])
    if not ids:
        return jsonify({"ok": True, "updated": 0})

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

    q = Notification.query.filter_by(is_read=False)
    if role == "restaurant_owner":
        q = q.filter_by(owner_id=uid)
    else:
        q = q.filter_by(customer_id=uid)

    updated = q.update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"ok": True, "updated": int(updated or 0)})
