from secrets import token_urlsafe

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from OrderFood import app, dao_index, oauth
from OrderFood.dao_index import *
from OrderFood.models import Restaurant, Category, Customer, Cart, CartItem
from admin_service import is_admin

from flask_login import login_user, logout_user, current_user, login_required
import cloudinary.uploader


ENUM_UPPERCASE = True  # True nếu DB là 'CUSTOMER','RESTAURANT_OWNER'; False nếu 'customer','restaurant_owner'


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
    # Params
    keyword = (request.args.get("search") or "").strip()
    rating_filter = request.args.get("rating")
    location_filter = request.args.get("location")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Lấy danh sách ban đầu
    if not keyword:
        restaurants = Restaurant.query.limit(50).all()   # mặc định hiển thị 50
    else:
        by_name = dao_index.get_restaurants_by_name(keyword)               # list[Restaurant]
        by_dish = dao_index.get_restaurants_by_dishes_name(keyword)        # list[Restaurant]
        # Hợp nhất theo restaurant_id để không trùng
        restaurants = list({r.restaurant_id: r for r in (by_name + by_dish)}.values())

    # Lọc rating (nếu có)
    if rating_filter and rating_filter.isdigit():
        min_rating = int(rating_filter)
        restaurants = [r for r in restaurants if (r.rating_point or 0) >= min_rating]

    # Lọc địa điểm (nếu có)
    if location_filter:
        restaurants = [r for r in restaurants if r.address and location_filter in r.address]

    # Danh sách địa điểm để render dropdown
    locations = [row[0] for row in Restaurant.query.with_entities(Restaurant.address)
                 .filter(Restaurant.address.isnot(None)).distinct().all()]

    # Sắp xếp & phân trang
    restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)
    total = len(restaurants)
    start = (page - 1) * per_page
    end = start + per_page
    restaurants_page = restaurants[start:end]

    # Gắn hiển thị sao (để template có thể vẽ rating)
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

@app.route("/customer")
def customer_home():
    if not is_customer(session.get("role")):
        return redirect(url_for("login"))

    # Lấy 50 nhà hàng, sắp xếp theo rating giảm dần
    restaurants = Restaurant.query.limit(50).all()
    restaurants.sort(key=lambda r: r.rating_point or 0, reverse=True)

    # Gắn thêm hiển thị sao
    restaurants_with_stars = []
    for r in restaurants:
        restaurants_with_stars.append({
            "restaurant": r,
            "stars": dao_index.get_star_display(r.rating_point or 0)
        })

    return render_template("customer_home.html", restaurants=restaurants_with_stars)


@app.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    # Lấy nhà hàng; nếu không có thì 404
    res = dao_index.get_restaurant_by_id(restaurant_id)
    if not res:
        abort(404)

    # Lấy món & category theo res_id (có thể eager-load nếu cần)
    dishes = Dish.query.filter_by(res_id=restaurant_id).all()
    categories = Category.query.filter_by(res_id=restaurant_id).all()

    # Hiển thị sao an toàn khi rating_point = None
    stars = dao_index.get_star_display(res.rating_point or 0)

    # Đếm số item trong giỏ của user hiện tại (nếu đăng nhập)
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
    )


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
                           locations = locations,
                           page=page,
                           per_page= per_page,
                           total = total)



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
    cart = Cart.query.filter_by(cus_id=customer.user_id, is_open=True, res_id = restaurant_id).first()

    cart_items = []
    total_price = 0

    if cart:
        cart_items = cart.items
        total_price = sum(item.quantity * item.dish.price for item in cart_items)

    return render_template("/customer/cart.html", cart=cart, cart_items=cart_items, total_price=total_price)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
