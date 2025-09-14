import traceback
from secrets import token_urlsafe
import hmac, hashlib
from urllib.parse import urlencode, quote_plus
from datetime import datetime

from flask import (
    render_template, request, redirect, url_for, flash, session, jsonify,
    current_app, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from OrderFood import app, dao_index, oauth
from OrderFood.dao_index import *
from OrderFood.models import *
from OrderFood.admin_service import is_admin

from flask_login import login_user, logout_user, current_user, login_required
import cloudinary.uploader

ENUM_UPPERCASE = True  # True nếu DB là 'CUSTOMER','RESTAURANT_OWNER'; False nếu 'customer','restaurant_owner'
import logging

logging.basicConfig(level=logging.DEBUG)


def norm_role_for_db(role: str) -> str:
    role = (role or "customer").strip().lower()
    if ENUM_UPPERCASE:
        return "CUSTOMER" if role == "customer" else "RESTAURANT_OWNER"
    return role


def _role_to_str(r):
    return getattr(r, "value", r)


def is_customer(role: str) -> bool:
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "customer"


def is_owner(role: str) -> bool:
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "restaurant_owner"



@app.route("/")
def index():
    keyword = (request.args.get("search") or "").strip()
    rating_filter = request.args.get("rating")
    location_filter = request.args.get("location")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    if not keyword:
        restaurants = Restaurant.query.limit(50).all()
    else:
        by_name = dao_index.get_restaurants_by_name(keyword)
        by_dish = dao_index.get_restaurants_by_dishes_name(keyword)
        restaurants = list({r.restaurant_id: r for r in (by_name + by_dish)}.values())

    if rating_filter and rating_filter.isdigit():
        min_rating = int(rating_filter)
        restaurants = [r for r in restaurants if (r.rating_point or 0) >= min_rating]

    if location_filter:
        restaurants = [r for r in restaurants if r.address and location_filter in r.address]

    locations = [row[0] for row in Restaurant.query.with_entities(Restaurant.address)
                 .filter(Restaurant.address.isnot(None)).distinct().all()]

    restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)
    total = len(restaurants)
    start = (page - 1) * per_page
    end = start + per_page
    restaurants_page = restaurants[start:end]
    restaurants_with_stars = [
        {"restaurant": r, "stars": dao_index.get_star_display(r.rating_point or 0)}
        for r in restaurants_page
    ]

    return render_template(
        "customer_home.html",
        restaurants=restaurants_with_stars,
        locations=locations,
        page=page,
        per_page=per_page,
        total=total,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        role = norm_role_for_db(request.form.get("role", "customer"))
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email và mật khẩu là bắt buộc", "danger")
            return redirect(url_for("register"))

        if get_user_by_email(email):
            flash("Email đã tồn tại", "warning")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        create_user(name=name, email=email, phone=phone, hashed_password=hashed, role=role)

        user = get_user_by_email(email)
        # ---- AUTO LOGIN ----
        session["user_id"] = user.user_id
        session["user_email"] = user.email
        session["user_name"] = user.name
        role_val = getattr(user.role, "value", user.role)  # Enum hoặc str
        session["role"] = (role_val or "").lower()

        flash("Đăng ký thành công! Bạn đã được đăng nhập.", "success")
        return redirect(url_for("index"))

    return render_template("auth.html")  # :contentReference[oaicite:3]{index=3}



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)

        if not user or not check_password_hash(user.password, password):
            flash("Sai email hoặc mật khẩu", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user.user_id
        session["user_email"] = user.email
        session["user_name"] = user.name
        session["role"] = _role_to_str(user.role)

        if is_owner(user.role):
            return redirect(url_for("owner_home"))
        if is_admin(user.role):
            return redirect(url_for("admin.admin_home"))
        return redirect(url_for("index"))

    return render_template("auth.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất", "info")
    return redirect(url_for("index"))



@app.route("/customer")
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



@app.route("/restaurant/<int:restaurant_id>")
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
        cart = (
            Cart.query.options(joinedload(Cart.items))
            .filter_by(cus_id=user_id, res_id=res.restaurant_id)
            .first()
        )
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




# ================== Owner ==================
@app.route("/owner")
def owner_home():
    if not is_owner(session.get("role")):
        return redirect(url_for("login"))
    return render_template("owner_home.html")



@app.route("/owner/menu")
def get_menu():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    keyword = (request.args.get('keyword') or '').strip()
    if not keyword:
        dishes = load_menu_owner(user_id)
    else:
        dishes = get_dishes_by_name(user_id, keyword)

    categories = get_categories_by_owner_id(user_id)
    return render_template("owner/menu.html", dishes=dishes, categories=categories)


@app.route("/owner/add_dish", methods=["POST"])
def add_dish():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user_id:
        return redirect(url_for("login"))

    if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
        return jsonify({"success": False, "error": "Bạn chưa có nhà hàng"})

    res_id = user.restaurant_owner.restaurant.restaurant_id

    name = request.form.get("name").strip()
    price = request.form.get("price")
    note = request.form.get("note")
    image_url = request.form.get("image_url")

    if not name or not price:
        return jsonify({"success": False, "error": "Tên món hoặc giá không được để trống"})

    category_name = None
    category_id = None

    selected_category = request.form.get("category")
    if selected_category == "new":
        category_name = request.form.get("new_category", "").strip()
        if category_name:
            category = Category.query.filter_by(res_id=res_id, name=category_name).first()
            if not category:
                category = Category(name=category_name, res_id=res_id)
                db.session.add(category)
                db.session.commit()
            category_id = category.category_id
    else:
        category_id = int(selected_category) if selected_category else None

    new_dish = Dish(
        name=name,
        price=price,
        note=note,
        category_id=category_id,
        res_id=res_id,
        image=image_url
    )
    db.session.add(new_dish)
    db.session.commit()

    category_name_for_json = ""
    if category_id:
        category_obj = Category.query.get(category_id)
        if category_obj:
            category_name_for_json = category_obj.name

    return jsonify({"success": True, "dish": {
        "dish_id": new_dish.dish_id,
        "name": new_dish.name,
        "price": new_dish.price,
        "note": new_dish.note,
        "category": category_name_for_json,
        "image": new_dish.image,
        "active": new_dish.is_available
    }})


@app.route("/owner/menu/<int:dish_id>", methods=["POST"])
def edit_dish(dish_id):
    try:
        dish = Dish.query.get(dish_id)
        if not dish:
            return jsonify({"success": False, "error": "Món ăn không tồn tại"}), 404

        name = request.form.get('name')
        note = request.form.get('note')
        price = request.form.get('price')
        category_name = request.form.get('category')
        is_available = request.form.get("is_available") == "1"
        image_url = request.form.get('image_url')

        dish.name = name
        dish.note = note
        dish.is_available = is_available
        try:
            dish.price = float(price) if price else 0.0
        except ValueError:
            return jsonify({"success": False, "error": f"Giá trị price không hợp lệ: {price}"}), 400

        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush()
            dish.category_id = category.category_id

        if image_url:
            dish.image = image_url

        db.session.commit()

        return jsonify({
            "success": True,
            "dish": {
                "dish_id": dish.dish_id,
                "name": dish.name,
                "note": dish.note,
                "price": dish.price,
                "category": dish.category.name if dish.category else None,
                "image": dish.image,
                "is_available": dish.is_available
            }
        })
    except Exception as e:
        db.session.rollback()
        print("Lỗi:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

    # index.py


@app.route("/owner/menu/<int:dish_id>", methods=["DELETE"])
def delete_dish(dish_id):
    try:
        dish = Dish.query.get(dish_id)
        if not dish:
            return jsonify({"success": False, "error": "Món ăn không tồn tại"}), 404

        db.session.delete(dish)
        db.session.commit()

        return jsonify({"success": True, "message": f"Đã xoá món ăn {dish.name}"})
    except Exception as e:
        db.session.rollback()
        print("Lỗi:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/owner/orders")
def manage_orders():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user_id:
        return redirect(url_for("login"))

    if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
        return jsonify({"success": False, "error": "Bạn chưa có nhà hàng"})

    res_id = user.restaurant_owner.restaurant.restaurant_id

    from OrderFood.models import StatusOrder

    pending_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.PAID).all()
    approved_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.ACCEPTED).all()
    cancelled_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.CANCELED).all()
    completed_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.COMPLETED).all()

    return render_template("owner/manage_orders.html",
                           pending_orders=pending_orders,
                           approved_orders=approved_orders,
                           cancelled_orders=cancelled_orders,
                           completed_orders=completed_orders,
                           res_id=res_id,
                           )


from flask import jsonify

@app.route("/owner/orders/<int:order_id>/approve", methods=["POST"])
def approve_order(order_id):
    order = Order.query.get_or_404(order_id)
    # Chỉ approve nếu trạng thái hiện tại là PAID
    if isinstance(order.status, str):
        # Nếu trong DB lưu string, chuyển sang Enum để gán
        if order.status == StatusOrder.PAID.value:
            order.status = StatusOrder.ACCEPTED
        else:
            return jsonify({"error": "Đơn hàng không ở trạng thái PAID"}), 400
    else:
        # Nếu là Enum
        if order.status == StatusOrder.PAID:
            order.status = StatusOrder.ACCEPTED
        else:
            return jsonify({"error": "Đơn hàng không ở trạng thái PAID"}), 400

    db.session.commit()

    return jsonify({
        "order_id": order.order_id,
        "status": order.status.value,
        "customer_name": order.customer.user.name,
        "total_price": order.total_price,
        "items": [{"name": item.dish.name, "quantity": item.quantity} for item in order.cart.items]
    })

@app.route("/owner/orders/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    reason = data.get("reason", "")

    # Cập nhật trạng thái
    if isinstance(order.status, str):
        order.status = StatusOrder.CANCELED.value
    else:
        order.status = StatusOrder.CANCELED

    db.session.add(order)

    # Tạo Refund nếu có payment
    if order.payment:
        refund = Refund(
            payment_id=order.payment.payment_id,
            reason=reason,
            requested_by=Role.ADMIN,
            created_at=datetime.utcnow(),
            status=StatusRefund.REQUESTED
        )
        db.session.add(refund)

    db.session.commit()

    # Trả về JSON đầy đủ
    return jsonify({
        "order_id": order.order_id,
        "status": getattr(order.status, "value", order.status),  # gửi status
        "customer_name": order.customer.user.name,
        "reason": reason
    })

#=========== Google Login ==================
@app.route("/login/google")
def login_google():
    redirect_uri = url_for("google_callback", _external=True)
    nonce = token_urlsafe(16)
    session["oidc_nonce"] = nonce
    return oauth.google.authorize_redirect(
        redirect_uri,
        nonce=nonce,
        prompt="consent",
    )

@app.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    nonce = session.pop("oidc_nonce", None)
    userinfo = oauth.google.parse_id_token(token, nonce=nonce)

    if not userinfo or "email" not in userinfo:
        flash("Không lấy được thông tin Google", "danger")
        return redirect(url_for("login"))

    email = userinfo["email"].lower()
    display_name = userinfo.get("name") or userinfo.get("given_name") or email.split("@")[0]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            name=display_name,
            avatar=userinfo.get("picture"),
            role="CUSTOMER",
        )
        db.session.add(user)
        db.session.commit()
    else:
        if not user.name and display_name:
            user.name = display_name
            db.session.commit()


    session["user_id"] = user.user_id
    session["user_email"] = user.email
    session["user_name"] = user.name or display_name or user.email
    session["role"] = _role_to_str(user.role).lower()

    flash("Đăng nhập bằng Google thành công!", "success")
    return redirect(url_for("customer_home"))


# ================== Cart APIs ==================
@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    dish_id = data.get("dish_id")
    restaurant_id = data.get("restaurant_id")
    if not dish_id or not restaurant_id:
        return jsonify({"error": "Thiếu dữ liệu"}), 400

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Bạn chưa đăng nhập"}), 403

    customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        return jsonify({"error": "Bạn không phải là khách hàng"}), 403

    cart = Cart.query.filter_by(
        cus_id=user_id, res_id=restaurant_id, status=StatusCart.ACTIVE
    ).first()

    if not cart:
        cart = Cart(cus_id=user_id, res_id=restaurant_id, status=StatusCart.ACTIVE)
        db.session.add(cart)
        db.session.commit()

    cart_item = CartItem.query.filter_by(cart_id=cart.cart_id, dish_id=dish_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.cart_id, dish_id=dish_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()

    total_items = sum(item.quantity for item in cart.items)
    return jsonify({"total_items": total_items})


@app.route("/cart/<int:restaurant_id>")
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




def _vnp_sign(params: dict) -> str:
    data = {k: v for k, v in params.items() if k not in ("vnp_SecureHash", "vnp_SecureHashType")}
    query = urlencode(sorted(data.items()), quote_via=quote_plus)  # dùng quote_plus
    secret = current_app.config["VNP_HASH_SECRET"]
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha512).hexdigest()



# ==== checkout & redirect (sửa route hiện có) ====
@app.route("/checkout/vnpay")
@app.route("/checkout/vnpay/<int:restaurant_id>")
def checkout_vnpay(restaurant_id=None):
    user_id = session.get("user_id")
    if not user_id:
        flash("Bạn cần đăng nhập trước khi thanh toán.", "warning")
        return redirect(url_for("login", next=request.url))

    rid = restaurant_id or request.args.get("restaurant_id", type=int)
    if not rid:
        # fallback: nếu user chỉ có 1 giỏ mở thì dùng luôn
        active_carts = Cart.query.filter_by(cus_id=user_id, status=StatusCart.ACTIVE).all()
        if len(open_carts) == 1:
            rid = open_carts[0].res_id
    if not rid:
        abort(400, "Thiếu restaurant_id")

    cart = Cart.query.filter_by(cus_id=user_id, res_id=rid, status=StatusCart.ACTIVE).first()
    if not cart or not cart.items:
        flash("Giỏ hàng trống.", "warning")
        return redirect(url_for("restaurant_detail", restaurant_id=rid))

    total_price = sum((ci.quantity or 0) * (ci.dish.price or 0) for ci in cart.items)
    amount_vnp = int(total_price) * 100  # VND x 100 theo quy định VNPay
    if amount_vnp <= 0:
        flash("Tổng tiền không hợp lệ.", "danger")
        return redirect(url_for("cart", restaurant_id=rid))

    waiting_time = current_app.config.get("WAITING_TIME", 30)  # mặc định 30 phút

    # Tạo order/payment PENDING
    order = Order(
        customer_id=user_id,
        restaurant_id=rid,
        cart_id=cart.cart_id,
        status=StatusOrder.PENDING,
        total_price=total_price,
        created_date=datetime.utcnow(),
        waiting_time=waiting_time
    )
    db.session.add(order)
    db.session.flush()  # để có order_id

    payment = Payment(order_id=order.order_id, status=StatusPayment.PENDING)
    db.session.add(payment)
    db.session.commit()

    # Build tham số VNPay
    client_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "127.0.0.1").split(",")[0].strip()
    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": current_app.config["VNP_TMN_CODE"],
        "vnp_Amount": amount_vnp,
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": f"OD{order.order_id}",
        "vnp_OrderInfo": f"Order {order.order_id}",  # tránh ký tự lạ như '#'
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_IpAddr": client_ip,
        "vnp_CreateDate": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "vnp_ReturnUrl": current_app.config["VNP_RETURN_URL"],
        "vnp_SecureHashType": "HmacSHA512",  # GỬI KÈM (không đưa vào ký)
    }
    params["vnp_SecureHash"] = _vnp_sign(params)
    pay_url = f"{current_app.config['VNP_PAY_URL']}?{urlencode(params, quote_via=quote_plus)}"
    return redirect(pay_url)



@app.route("/vnpay_return")
def vnpay_return():
    data = dict(request.args)
    received_hash = data.get("vnp_SecureHash", "")
    calc_hash = _vnp_sign(data)
    valid = hmac.compare_digest(received_hash, calc_hash)

    txn_ref = data.get("vnp_TxnRef", "")
    try:
        order_id = int(txn_ref.replace("OD", ""))
    except ValueError:
        order_id = None

    order = Order.query.get_or_404(order_id)

    if valid and data.get("vnp_ResponseCode") == "00":
        # 1) Set order PAID
        order.status = StatusOrder.PAID

        # 2) Đảm bảo có bản ghi payment cho order này
        pay = Payment.query.filter_by(order_id=order.order_id).first()
        if not pay:
            pay = Payment(order_id=order.order_id, status=StatusPayment.PAID)
            db.session.add(pay)
        else:
            pay.status = StatusPayment.PAID

        # 3) Đóng giỏ
        if order.cart:
            order.cart.status = StatusCart.CHECKOUT

        db.session.commit()
        flash("Thanh toán thành công.", "success")
    else:
        flash("Thanh toán chưa thành công hoặc không hợp lệ.", "warning")

    # -> Luôn chuyển về trang theo dõi đơn
    return redirect(url_for("order_track", order_id=order.order_id))


@app.route("/vnpay_ipn")
def vnpay_ipn():
    data = dict(request.args)
    received_hash = data.get("vnp_SecureHash", "")
    calc_hash = _vnp_sign(data)
    if not hmac.compare_digest(received_hash, calc_hash):
        # Sai chữ ký
        return jsonify({"RspCode": "97", "Message": "Invalid signature"})

    txn_ref = data.get("vnp_TxnRef", "")
    try:
        order_id = int(txn_ref.replace("OD", ""))
    except ValueError:
        return jsonify({"RspCode": "01", "Message": "Order not found"})

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"RspCode": "01", "Message": "Order not found"})

    if data.get("vnp_ResponseCode") == "00":
        order.status = StatusOrder.PAID
        if order.cart:
            order.cart.status = StatusCart.CHECKOUT
        if order.payment:
            order.payment.status = StatusPayment.PAID
        db.session.commit()
        return jsonify({"RspCode": "00", "Message": "Confirm Success"})
    else:
        # tuỳ trường hợp có thể giữ PENDING hoặc đánh dấu CANCELED
        db.session.commit()
        return jsonify({"RspCode": "00", "Message": "Confirm Received"})

@app.route("/orders")
def my_orders():
    uid = session.get("user_id")
    if not uid:
        flash("Vui lòng đăng nhập để xem đơn hàng.", "warning")
        return redirect(url_for("login", next=request.url))

    # (tuỳ chọn) chỉ cho Customer vào
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


@app.route("/order/<int:order_id>/track")
def order_track(order_id):
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login", next=request.url))

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

    if is_paid: active_idx = 0
    elif is_accepted: active_idx = 1
    elif is_canceled or is_completed: active_idx = 2
    else: active_idx = -1

    last_label = "Đã hủy" if is_canceled else "Đã giao hàng thành công"

    return render_template(
        "customer/order_track.html",
        order=order, active_idx=active_idx, last_label=last_label, status_str=s
    )


@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Lỗi 500: %s", error)  # log chi tiết vào terminal
    return jsonify({"success": False, "error": "Internal Server Error"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
