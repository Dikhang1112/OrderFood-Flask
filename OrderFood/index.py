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
from admin_service import is_admin

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
        return jsonify({"success": False, "error": "Chưa login"})

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

    # Kiểm tra role từ session (nhanh) và DB (phòng trường hợp session lệch)
    role_in_session = (session.get("role") or "").lower()
    user = User.query.get(user_id)
    role_in_db = (getattr(user.role, "value", user.role) or "").lower() if user else ""

    if not (role_in_session == "customer" or role_in_db == "customer"):
        return jsonify({"error": "Bạn không phải là khách hàng"}), 403

    # Đảm bảo có Customer profile
    customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        customer = Customer(user_id=user_id)
        db.session.add(customer)
        db.session.commit()

    cart = Cart.query.filter_by(
        cus_id=user_id, res_id=restaurant_id, is_open=True
    ).first()

    if not cart:
        cart = Cart(cus_id=user_id, res_id=restaurant_id, is_open=True)
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


@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Lỗi 500: %s", error)  # log chi tiết vào terminal
    return jsonify({"success": False, "error": "Internal Server Error"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
