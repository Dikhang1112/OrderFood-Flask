import hmac
import hashlib
import time as pytime                     # ✅ dùng module time
from datetime import datetime, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode, quote_plus

from flask import (
    Blueprint, request, redirect, url_for, flash, jsonify,
    session, current_app, abort
)

from OrderFood import db
from OrderFood.models import (
    Order, Cart, Payment,
    StatusOrder, StatusPayment, StatusCart
)
from OrderFood.notifications import push_owner_noti_on_paid

vnpay_bp = Blueprint("vnpay", __name__)

def _new_txn_ref(order_id: int) -> str:
    # Ví dụ: OD1234-<epoch>-<rand>  (đủ duy nhất cho mỗi lần điều hướng sang VNPay)
    return f"OD{order_id}-{int(pytime.time())}-{token_urlsafe(4)}"   # ✅

def _vnp_sign(params: dict) -> str:
    """Tạo chữ ký HmacSHA512 theo chuẩn VNPay."""
    data = {k: v for k, v in params.items()
            if k not in ("vnp_SecureHash", "vnp_SecureHashType")}
    query = urlencode(sorted(data.items()), quote_via=quote_plus)
    secret = current_app.config["VNP_HASH_SECRET"]
    return hmac.new(secret.encode("utf-8"),
                    query.encode("utf-8"),
                    hashlib.sha512).hexdigest()

@vnpay_bp.route("/checkout/vnpay")
@vnpay_bp.route("/checkout/vnpay/<int:restaurant_id>")
def checkout_vnpay(restaurant_id=None):
    user_id = session.get("user_id")
    if not user_id:
        flash("Bạn cần đăng nhập trước khi thanh toán.", "warning")
        return redirect(url_for("login", next=request.url))

    # ===== Xác định restaurant_id (rid) =====
    rid = restaurant_id or request.args.get("restaurant_id", type=int)
    if not rid:
        open_carts = Cart.query.filter_by(cus_id=user_id, is_open=True).all()
        if len(open_carts) == 1:
            rid = open_carts[0].res_id
    if not rid:
        abort(400, "Thiếu restaurant_id")

    # ===== Tìm cart đang mở =====
    cart = Cart.query.filter_by(cus_id=user_id, res_id=rid, status=StatusCart.ACTIVE).first()
    if not cart or not cart.items:
        flash("Giỏ hàng trống.", "warning")
        return redirect(url_for("admin.restaurant_detail", restaurant_id=rid))

    # ===== Tính tiền & waiting time =====
    total_price = sum((ci.quantity or 0) * (ci.dish.price or 0) for ci in cart.items)
    if total_price <= 0:
        flash("Tổng tiền không hợp lệ.", "danger")
        return redirect(url_for("cart", restaurant_id=rid))
    waiting_time = current_app.config.get("WAITING_TIME", 10)
    amount_vnp = int(total_price) * 100  # VNPay cần VND x 100

    try:
        # ===== Idempotent Order theo cart =====
        order = (Order.query
                    .filter(Order.cart_id == cart.cart_id,
                            Order.status.in_([StatusOrder.PENDING,
                                              StatusOrder.PAID,
                                              StatusOrder.ACCEPTED]))
                    .order_by(Order.order_id.desc())
                    .first())

        if order:
            # đồng bộ lại tổng tiền & thời gian chờ
            order.total_price = total_price
            order.waiting_time = waiting_time
        else:
            # Chưa có -> tạo mới
            order = Order(
                customer_id=user_id,
                restaurant_id=rid,
                cart_id=cart.cart_id,
                status=StatusOrder.PENDING,
                total_price=total_price,
                waiting_time=waiting_time
            )
            db.session.add(order)
            db.session.flush()   # lấy order_id


        # ===== Đảm bảo có Payment & làm mới txn_ref =====
        payment = Payment.query.filter_by(order_id=order.order_id).first()
        new_ref = _new_txn_ref(order.order_id)

        if not payment:
            payment = Payment(
                order_id=order.order_id,
                status=StatusPayment.PENDING,
                txn_ref=new_ref,
                amount=amount_vnp
            )
            db.session.add(payment)
        else:
            payment.status = StatusPayment.PENDING
            payment.txn_ref = new_ref
            payment.amount = amount_vnp

        db.session.commit()

    except Exception as ex:
        db.session.rollback()
        current_app.logger.exception("checkout_vnpay failed: %s", ex)
        flash("Có lỗi khi tạo giao dịch. Vui lòng thử lại.", "danger")
        return redirect(url_for("restaurant_detail", restaurant_id=rid))

    # ===== Sinh URL VNPay dùng txn_ref mới =====
    client_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "127.0.0.1").split(",")[0].strip()
    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": current_app.config["VNP_TMN_CODE"],
        "vnp_Amount": payment.amount,
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": payment.txn_ref,           # ✅ luôn mới
        "vnp_OrderInfo": f"Order {order.order_id}",
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_IpAddr": client_ip,
        "vnp_CreateDate": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "vnp_ReturnUrl": current_app.config["VNP_RETURN_URL"],
        "vnp_SecureHashType": "HmacSHA512",
    }
    params["vnp_SecureHash"] = _vnp_sign(params)
    pay_url = f"{current_app.config['VNP_PAY_URL']}?{urlencode(params, quote_via=quote_plus)}"
    return redirect(pay_url)


@vnpay_bp.route("/vnpay_return")
def vnpay_return():
    """Return URL: cập nhật trạng thái khi người dùng quay lại site."""
    # Loại vnp_SecureHash khỏi params để tính chữ ký
    params = {k: v for k, v in request.args.items() if k != "vnp_SecureHash"}
    received_hash = request.args.get("vnp_SecureHash", "")
    calc_hash = _vnp_sign(params)
    valid = hmac.compare_digest(received_hash, calc_hash)

    txn_ref = params.get("vnp_TxnRef", "")
    payment = Payment.query.filter_by(txn_ref=txn_ref).first()   # ✅ tra theo txn_ref
    if not payment:
        flash("Không tìm thấy giao dịch.", "danger")
        return redirect(url_for("index"))

    order = Order.query.get_or_404(payment.order_id)

    # (khuyến nghị) kiểm tra số tiền
    try:
        vnp_amount = int(params.get("vnp_Amount", "0"))
    except ValueError:
        vnp_amount = 0
    if vnp_amount and vnp_amount != int(payment.amount):
        flash("Số tiền giao dịch không khớp.", "danger")
        return redirect(url_for("index"))

    if valid and params.get("vnp_ResponseCode") == "00":
        just_marked = False
        if payment.status != StatusPayment.PAID:
            payment.status = StatusPayment.PAID
            just_marked = True
        if order.status != StatusOrder.PAID:
            order.status = StatusOrder.PAID
            just_marked = True

        if order.cart:
            order.cart.is_open = False
            order.cart.status = StatusCart.CHECKOUT

        db.session.commit()

        # chỉ push noti khi thực sự vừa chuyển sang PAID
        if just_marked:
            push_owner_noti_on_paid(order)

        flash("Thanh toán thành công.", "success")
    else:
        if payment.status != StatusPayment.PENDING:
            payment.status = StatusPayment.PENDING
            db.session.commit()
        flash("Thanh toán chưa thành công hoặc không hợp lệ.", "warning")

    return redirect(url_for("customer.order_track", order_id=order.order_id))

@vnpay_bp.route("/vnpay_ipn")
def vnpay_ipn():
    """IPN: VNPay gọi về để xác nhận giao dịch (server-to-server)."""
    params = {k: v for k, v in request.args.items() if k != "vnp_SecureHash"}
    received_hash = request.args.get("vnp_SecureHash", "")
    calc_hash = _vnp_sign(params)
    if not hmac.compare_digest(received_hash, calc_hash):
        return jsonify({"RspCode": "97", "Message": "Invalid signature"})

    txn_ref = params.get("vnp_TxnRef", "")
    payment = Payment.query.filter_by(txn_ref=txn_ref).first()
    if not payment:
        return jsonify({"RspCode": "01", "Message": "Payment not found"})

    order = Order.query.get(payment.order_id)
    if not order:
        return jsonify({"RspCode": "01", "Message": "Order not found"})

    # (khuyến nghị) kiểm tra số tiền
    try:
        vnp_amount = int(params.get("vnp_Amount", "0"))
    except ValueError:
        vnp_amount = 0
    if vnp_amount and vnp_amount != int(payment.amount):
        return jsonify({"RspCode": "04", "Message": "Invalid amount"})

    if params.get("vnp_ResponseCode") == "00":
        just_marked = False
        if payment.status != StatusPayment.PAID:
            payment.status = StatusPayment.PAID
            just_marked = True
        if order.status != StatusOrder.PAID:
            order.status = StatusOrder.PAID
            just_marked = True

        if order.cart:
            order.cart.is_open = False
            order.cart.status = StatusCart.CHECKOUT

        db.session.commit()

        # đẩy noti cho owner nếu lần đầu thành PAID (phòng TH user không quay lại return)
        if just_marked:
            push_owner_noti_on_paid(order)

        return jsonify({"RspCode": "00", "Message": "Confirm Success"})
    else:
        if payment.status != StatusPayment.PENDING:
            payment.status = StatusPayment.PENDING
            db.session.commit()
        return jsonify({"RspCode": "00", "Message": "Confirm Received"})
