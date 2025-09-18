# OrderFood/jobs.py
from sqlalchemy import func, text
from OrderFood.models import Order, StatusOrder, Role, Notification, Restaurant


def cancel_expired_orders():
    from OrderFood import db

    # Tìm các đơn đã thanh toán nhưng quá thời gian chờ xác nhận
    expired = (
        Order.query
        .filter(Order.status == StatusOrder.PAID)
        .filter(
            func.timestampdiff(
                text('SECOND'),
                Order.created_date,
                func.now()
            ) >= (Order.waiting_time * 60)
        )
        .all()
    )

    if not expired:
        print("Không có đơn quá hạn.")
        return

    msg = "Đơn hàng bị hủy do quá thời gian xác nhận"
    notis = []

    for o in expired:
        print(f"[CANCEL] order #{o.order_id} quá hạn {o.waiting_time} phút")

        # Cập nhật trạng thái đơn
        o.status = StatusOrder.CANCELED
        o.canceled_by = Role.RESTAURANT_OWNER  # hoặc Role.SYSTEM nếu bạn muốn

        # ===== Notification cho CUSTOMER =====
        notis.append(Notification(
            order_id=o.order_id,
            message=msg,
            customer_id=o.customer_id,   # gửi cho khách
            owner_id=None
        ))

        # ===== Notification cho OWNER =====
        # Lấy res_owner_id từ bảng restaurant
        res_owner_id = (
            db.session.query(Restaurant.res_owner_id)
            .filter(Restaurant.restaurant_id == o.restaurant_id)
            .scalar()
        )
        if res_owner_id:
            notis.append(Notification(
                order_id=o.order_id,
                message=msg,
                owner_id=res_owner_id,  # gửi cho chủ nhà hàng
                customer_id=None
            ))

    # Ghi DB một lần
    if notis:
        db.session.add_all(notis)
    db.session.commit()
    print(f"Đã hủy {len(expired)} đơn quá hạn và tạo {len(notis)} thông báo.")
