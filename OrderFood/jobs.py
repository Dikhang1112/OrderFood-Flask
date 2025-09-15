def cancel_expired_orders():
    from OrderFood import db
    from OrderFood.models import Order, StatusOrder

    expired_orders = Order.query.filter(Order.status == StatusOrder.PAID).all()

    for o in expired_orders:
        if o.is_expired:
            o.status = StatusOrder.CANCELED
            print(f"Hủy order #{o.order_id}, hết hạn lúc {o.expire_time}")

    db.session.commit()
