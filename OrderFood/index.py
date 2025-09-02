from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required
# from OrderFood import

from OrderFood import app, dao
from OrderFood.dao import *
from OrderFood.models import Restaurant

ENUM_UPPERCASE = True   # True nếu DB là 'CUSTOMER','RESTAURANT_OWNER'; False nếu 'customer','restaurant_owner'

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
    keyword = (request.args.get('search') or '').strip()
    if not keyword:
        return render_template("customer_home.html", restaurants=[])
    restaurants_by_name = dao.get_restaurants_by_name(keyword)
    restaurants_by_dishes = dao.get_restaurants_by_dishes_name(keyword)
    all_restaurants = list({r.restaurant_id: r for r in restaurants_by_name + restaurants_by_dishes}.values())
    print(all_restaurants)
    return render_template("customer_home.html", restaurants=all_restaurants)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name  = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        role  = norm_role_for_db(request.form.get("role", "customer"))
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
        session["user_id"]    = user.user_id
        session["user_email"] = user.email
        role_val = getattr(user.role, "value", user.role)   # Enum hoặc str
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
        session["role"] = _role_to_str(user.role)

        if is_owner(user.role):
            return redirect(url_for("owner_home"))
        return redirect(url_for("customer_home"))

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
    return render_template("customer_home.html",restaurants=restaurants)

@app.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    res = dao.get_restaurant_by_id(restaurant_id)
    dishes = Dish.query.filter_by(res_id=restaurant_id).all()
    return render_template("/customer/restaurant_detail.html", res=res, dishes = dishes)

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

    dishes = load_menu_owner(user_id)
    return render_template("owner/menu.html", dishes=dishes)

@app.route("/admin")
def admin_home():
    if session.get("role") not in ("ADMIN", "admin"):
        flash("Bạn không có quyền truy cập trang admin", "danger")
        return redirect(url_for("index"))
    return render_template("admin_home.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
