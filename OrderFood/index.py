# index.py
import os, traceback
from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from OrderFood import app
from OrderFood.dao import *

# --- Helpers ---
ENUM_UPPERCASE = True
def norm_role_for_db(role: str) -> str:
    role = (role or "customer").strip().lower()
    if ENUM_UPPERCASE:
        return "CUSTOMER" if role == "customer" else "RESTAURANT_OWNER"
    return role

def _role_to_str(r):
    return getattr(r, "value", r)

def is_owner(role: str) -> bool:
    rolestr = _role_to_str(role)
    return (rolestr or "").lower() == "restaurant_owner"

# --- Routes ---
@app.route("/")
def index_route():
    keyword = (request.args.get("search") or "").strip()
    rating_filter = request.args.get("rating")
    location_filter = request.args.get("location")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    if not keyword:
        restaurants = Restaurant.query.limit(50).all()
    else:
        by_name = get_restaurants_by_name(keyword)
        by_dish = get_restaurants_by_dishes_name(keyword)
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
        {"restaurant": r, "stars": get_star_display(r.rating_point or 0)}
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
        session["user_id"] = user.user_id
        session["user_email"] = user.email
        session["user_name"] = user.name
        session["role"] = (getattr(user.role, "value", user.role) or "").lower()

        flash("Đăng ký thành công! Bạn đã được đăng nhập.", "success")
        if is_owner(user.role):
            return redirect(url_for("owner.owner_home"))
        return redirect(url_for("index_route"))

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
            return redirect(url_for("owner.owner_home"))
        return redirect(url_for("index_route"))

    return render_template("auth.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất", "info")
    return redirect(url_for("index_route"))

# --- Cart API ---
@app.route('/api/cart', methods=['POST'])
def add_to_cart_route():
    try:
        data = request.get_json()
        dish_id = data.get("dish_id")
        restaurant_id = data.get("restaurant_id")
        try:
            quantity = int(data.get("quantity", 1))
            if quantity <= 0:
                quantity = 1
        except:
            quantity = 1
        note = data.get("note", "")

        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Bạn chưa đăng nhập"}), 403

        customer = Customer.query.filter_by(user_id=user_id).first()
        if not customer:
            return jsonify({"error": "Bạn không phải là khách hàng"}), 403

        cart = get_active_cart(user_id, restaurant_id)
        if not cart:
            cart = Cart(cus_id=user_id, res_id=restaurant_id, status=StatusCart.ACTIVE)
            db.session.add(cart)
            db.session.commit()

        add_cart_item(cart, dish_id, quantity, note)
        total_items = count_cart_items(cart)
        return jsonify({"total_items": total_items})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/cart/<int:restaurant_id>")
def cart_route(restaurant_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Bạn chưa đăng nhập"}), 403

    customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        return jsonify({"error": "Bạn không phải là khách hàng"}), 403

    cart = get_active_cart(user_id, restaurant_id)
    cart_items = cart.items if cart else []
    total_price = sum(item.quantity * item.dish.price for item in cart_items) if cart_items else 0

    return render_template("/customer/cart.html", cart=cart, cart_items=cart_items, total_price=total_price)
