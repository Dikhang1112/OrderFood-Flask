import traceback
from secrets import token_urlsafe

import login
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from sqlalchemy.sql.functions import current_user
from werkzeug.security import generate_password_hash, check_password_hash
from OrderFood import app, dao_index, oauth
from OrderFood.dao_index import *
from OrderFood.models import Restaurant, Category, Customer, Cart, CartItem
from adminService import is_admin
from flask_login import login_user, logout_user, current_user, login_required
import cloudinary.uploader

ENUM_UPPERCASE = True  # True nếu DB là 'CUSTOMER','RESTAURANT_OWNER'; False nếu 'customer','restaurant_owner'

import logging

# cấu hình log
logging.basicConfig(level=logging.DEBUG)

def norm_role_for_db(role: str) -> str:
    role = (role or "customer").strip().lower()
    if ENUM_UPPERCASE:
        return "CUSTOMER" if role == "customer" else "RESTAURANT_OWNER"
    return role  # dùng chữ thường


def _role_to_str(r):
    # nếu r là Enum => lấy .value, còn lại giữ nguyên
    return getattr(r, "value", r)


def is_customer(role: str) -> bool:
    # return role in ("customer", "CUSTOMER")
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "customer"


def is_owner(role: str) -> bool:
    # return role in ("restaurant_owner", "RESTAURANT_OWNER")
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "restaurant_owner"


@app.route("/")
def index():
    restaurants = Restaurant.query.limit(50).all()
    restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)
    keyword = (request.args.get('search') or '').strip()
    rating_filter = request.args.get('rating')
    location_filter = request.args.get('location')

    page = request.args.get("page", 1, type=int)
    per_page = 20

    # không tìm kiếm thì trả về 50 nhà hàng đầu tiên
    if not keyword:
        restaurants = Restaurant.query.limit(50).all()
    else:
        restaurants_by_name = dao_index.get_restaurants_by_name(keyword)
        restaurants_by_dishes = dao_index.get_restaurants_by_dishes_name(keyword)
        restaurants = list({r.restaurant_id: r for r in restaurants_by_name + restaurants_by_dishes}.values())

        # Lọc theo rating nếu có
    if rating_filter and rating_filter.isdigit():
        rating_value = int(rating_filter)
        restaurants = [r for r in restaurants if (r.rating_point or 0) >= rating_value]

    locations = (
        db.session.query(Restaurant.address)
        .filter(Restaurant.address.isnot(None))
        .distinct()
        .all()
    )
    locations = [loc[0] for loc in locations]
    if location_filter:
        restaurants = [r for r in restaurants if r.address and location_filter in r.address]

    restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)

    total = len(restaurants)
    start = (page - 1) * per_page
    end = start + per_page
    restaurants_page = restaurants[start:end]
    restaurants_with_stars = []
    for r in restaurants_page:
        restaurants_with_stars.append({
            "restaurant": r,
            "stars": dao_index.get_star_display(r.rating_point or 0)
        })

    return render_template("customer_home.html", restaurants=restaurants_with_stars,
                           locations=locations,
                           page=page,
                           per_page=per_page,
                           total=total)


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
        # Tạo user
        create_user(name=name, email=email, phone=phone, hashed_password=hashed, role=role)

        # LẤY user vừa tạo để đưa vào session
        user = get_user_by_email(email)

        # ---- AUTO LOGIN ----
        session["user_id"] = user.user_id
        session["user_email"] = user.email
        session["user_name"] = user.name
        role_val = getattr(user.role, "value", user.role)  # Enum hoặc str
        session["role"] = (role_val or "").lower()

        flash("Đăng ký thành công! Bạn đã được đăng nhập.", "success")
        return redirect(url_for("index"))

    return render_template("auth.html")


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


# @app.route("/customer")
# def customer_home():
#     if not is_customer(session.get("role")):
#         return redirect(url_for("login"))
#     restaurants = Restaurant.query.limit(50).all()
#     restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)
#
#     restaurants_with_stars = []
#     for r in restaurants:
#         restaurants_with_stars.append({
#             "restaurant": r,
#             "stars": dao_index.get_star_display(r.rating_point or 0)
#         })
#     return render_template("customer_home.html",restaurants=restaurants_with_stars)

@app.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    res = dao_index.get_restaurant_by_id(restaurant_id)
    dishes = Dish.query.filter_by(res_id=restaurant_id).all()
    stars = dao_index.get_star_display(res.rating_point or 0)
    categories = Category.query.filter_by(res_id=restaurant_id).all()
    user_id = session.get("user_id")
    cart = Cart.query.filter_by(cus_id=user_id, res_id=res.restaurant_id).first()
    cart_items_count = 0;
    if cart:  # chỉ khi cart tồn tại
        cart_items_count = sum(item.quantity for item in cart.items)
        # cart_items_count = len(CartItem.query.filter_by( cart_id=cart.cart_id).all())
    return render_template("/customer/restaurant_detail.html", res=res,
                           dishes=dishes, stars=stars,
                           categories=categories,
                           cart_items_count=cart_items_count)


@app.route("/owner")
def owner_home():
    if not is_owner(session.get("role")):
        return redirect(url_for("login"))
    return render_template("owner_home.html")


# chỉnh sửa thực đơn của owner
@app.route("/owner/menu")
# @login_required
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

    return render_template("customer_home.html", restaurants=restaurants_with_stars,
                           locations=locations,
                           page=page,
                           per_page=per_page,
                           total=total)


@app.route("/owner/add_dish", methods=["POST"])
def add_dish():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user_id:
        return jsonify({"success": False, "error": "Chưa login"})

    if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
        return jsonify({"success": False, "error": "Bạn chưa có nhà hàng"})

    res_id = user.restaurant_owner.restaurant.restaurant_id

    name = request.form.get("name").strip()
    price = request.form.get("price")
    note = request.form.get("note")
    image_url = request.form.get("image_url")  # nhận link Cloudinary từ JS

    if not name or not price:
        return jsonify({"success": False, "error": "Tên món hoặc giá không được để trống"})

    category_name = None
    category_id = None

    # Nếu chọn category cũ
    selected_category = request.form.get("category")
    if selected_category == "new":
        # Lấy tên category mới
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


# ================= GOOGLE LOGIN =================

@app.route("/login/google")
def login_google():
    redirect_uri = url_for("google_callback", _external=True)
    nonce = token_urlsafe(16)
    session["oidc_nonce"] = nonce
    # prompt=consent là tùy chọn
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

    # ĐĂNG NHẬP
    session["user_id"] = user.user_id  # <- đừng dùng user.id
    session["user_email"] = user.email
    session["user_name"] = user.name or display_name or user.email
    session["role"] = _role_to_str(user.role).lower()

    flash("Đăng nhập bằng Google thành công!", "success")
    return redirect(url_for("customer_home"))


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

    # Tìm giỏ hàng đang mở
    cart = Cart.query.filter_by(
        cus_id=user_id, res_id=restaurant_id, is_open=True
    ).first()

    if not cart:
        cart = Cart(cus_id=user_id, res_id=restaurant_id, is_open=True)
        db.session.add(cart)
        db.session.commit()

    # Thêm hoặc tăng số lượng món
    cart_item = CartItem.query.filter_by(cart_id=cart.cart_id, dish_id=dish_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.cart_id, dish_id=dish_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()

    # Đếm tổng số sản phẩm trong giỏ
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
    cart = Cart.query.filter_by(cus_id=customer.user_id, is_open=True, res_id=restaurant_id).first()

    cart_items = []
    total_price = 0

    if cart:
        cart_items = cart.items
        total_price = sum(item.quantity * item.dish.price for item in cart_items)

    return render_template("/customer/cart.html", cart=cart, cart_items=cart_items, total_price=total_price)




@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Lỗi 500: %s", error)  # log chi tiết vào terminal
    return jsonify({"success": False, "error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
