import traceback
from secrets import token_urlsafe

import hmac, hashlib
from urllib.parse import urlencode, quote_plus
from datetime import datetime

from flask import (
    render_template, request, redirect, url_for, flash, session, jsonify,
    current_app, abort
)
from sqlalchemy.orm import joinedload
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
            return redirect(url_for("owner.home"))
        if is_admin(user.role):
            return redirect(url_for("admin.admin_home"))
        return redirect(url_for("index"))

    return render_template("auth.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất", "info")
    return redirect(url_for("index"))




@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Lỗi 500: %s", error)  # log chi tiết vào terminal
    return jsonify({"success": False, "error": "Internal Server Error"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
