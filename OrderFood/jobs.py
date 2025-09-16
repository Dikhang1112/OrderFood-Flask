# OrderFood/jobs.py
from sqlalchemy import func, text
from OrderFood.models import Order, StatusOrder, Role


def cancel_expired_orders():
    from OrderFood import db
    expired = (
        Order.query
        .filter(Order.status == StatusOrder.PAID)
        .filter(
            func.timestampdiff(
                text('SECOND'),
                Order.created_date,
                func.now()            # <--- dùng NOW() thay vì UTC_TIMESTAMP()
            ) >= (Order.waiting_time * 60)
        )
        .all()
    )
    for o in expired:
        print(f"[CANCEL] order #{o.order_id} quá hạn {o.waiting_time} phút")
        o.status = StatusOrder.CANCELED
        o.canceled_by = Role.RESTAURANT_OWNER

    if expired:
        db.session.commit()
        print(f"Đã hủy {len(expired)} đơn quá hạn.")
    else:
        print("Không có đơn quá hạn.")
