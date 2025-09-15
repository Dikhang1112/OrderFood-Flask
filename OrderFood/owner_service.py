# OrderFood/owner_service.py
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, request, session, redirect, url_for, jsonify
)
from sqlalchemy.orm import joinedload

from OrderFood import db, dao_index
from OrderFood.dao_index import (
    load_menu_owner, get_dishes_by_name, get_categories_by_owner_id
)
from OrderFood.models import (
    User, RestaurantOwner, Restaurant, Category, Dish,
    Order, Cart, CartItem, Refund,
    StatusOrder, StatusCart, StatusRefund, Role
)

owner_bp = Blueprint("owner", __name__)



# ===== Helpers =====
def _role_to_str(r):
    return getattr(r, "value", r)

def is_owner(role) -> bool:
    rolestr = (_role_to_str(role) or "").lower()
    return rolestr == "restaurant_owner"

def require_owner(f):
    """Bảo vệ route chỉ dành cho Owner đã đăng nhập & có nhà hàng"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))

        role = session.get("role")
        # session["role"] có thể là Enum.value hoặc string
        if not is_owner(role):
            return redirect(url_for("login"))

        # đảm bảo user có RestaurantOwner và có Restaurant
        user = User.query.options(
            joinedload(User.restaurant_owner).joinedload(RestaurantOwner.restaurant)
        ).get(user_id)

        if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
            # Cho các API JSON, trả về lỗi JSON; cho view, redirect sang login/home tùy bạn
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({"success": False, "error": "Bạn chưa có nhà hàng"}), 403
            return redirect(url_for("login"))

        return f(user, *args, **kwargs)
    return wrapper


# ===== Routes =====
@owner_bp.route("/")
@require_owner
def home(user: User):
    return render_template("owner_home.html")


@owner_bp.route("/owner/menu")
@require_owner
def get_menu(user: User):
    keyword = (request.args.get('keyword') or '').strip()
    if not keyword:
        dishes = load_menu_owner(user.user_id)
    else:
        dishes = get_dishes_by_name(user.user_id, keyword)

    categories = get_categories_by_owner_id(user.user_id)
    return render_template("owner/menu.html", dishes=dishes, categories=categories)


@owner_bp.route("/owner/add_dish", methods=["POST"])
@require_owner
def add_dish(user: User):
    res = user.restaurant_owner.restaurant
    res_id = res.restaurant_id

    name = (request.form.get("name") or "").strip()
    price = request.form.get("price")
    note = request.form.get("note")
    image_url = request.form.get("image_url")

    if not name or not price:
        return jsonify({"success": False, "error": "Tên món hoặc giá không được để trống"})

    # Xử lý category (chọn có sẵn hoặc tạo mới)
    category_id = None
    selected_category = request.form.get("category")
    if selected_category == "new":
        category_name = (request.form.get("new_category") or "").strip()
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


@owner_bp.route("/owner/menu/<int:dish_id>", methods=["POST"])
@require_owner
def edit_dish(user: User, dish_id):
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
                category = Category(name=category_name, res_id=dish.res_id)
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
        return jsonify({"success": False, "error": str(e)}), 500


@owner_bp.route("/owner/menu/<int:dish_id>", methods=["DELETE"])
@require_owner
def delete_dish(user: User, dish_id):
    try:
        dish = Dish.query.get(dish_id)
        if not dish:
            return jsonify({"success": False, "error": "Món ăn không tồn tại"}), 404

        db.session.delete(dish)
        db.session.commit()

        return jsonify({"success": True, "message": f"Đã xoá món ăn {dish.name}"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@owner_bp.route("/owner/orders")
@require_owner
def manage_orders(user: User):
    res_id = user.restaurant_owner.restaurant.restaurant_id

    pending_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.PAID).all()
    approved_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.ACCEPTED).all()
    cancelled_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.CANCELED).all()
    completed_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.COMPLETED).all()

    return render_template(
        "owner/manage_orders.html",
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        cancelled_orders=cancelled_orders,
        completed_orders=completed_orders,
        res_id=res_id,
    )


@owner_bp.route("/owner/orders/<int:order_id>/approve", methods=["POST"])
@require_owner
def approve_order(user: User, order_id):
    order = Order.query.get_or_404(order_id)

    # Chỉ approve nếu hiện tại là PAID
    if isinstance(order.status, str):
        if order.status == StatusOrder.PAID.value:
            order.status = StatusOrder.ACCEPTED
        else:
            return jsonify({"error": "Đơn hàng không ở trạng thái PAID"}), 400
    else:
        if order.status == StatusOrder.PAID:
            order.status = StatusOrder.ACCEPTED
        else:
            return jsonify({"error": "Đơn hàng không ở trạng thái PAID"}), 400

    db.session.commit()

    return jsonify({
        "order_id": order.order_id,
        "status": getattr(order.status, "value", order.status),
        "customer_name": order.customer.user.name,
        "total_price": order.total_price,
        "items": [{"name": item.dish.name, "quantity": item.quantity} for item in order.cart.items]
    })


@owner_bp.route("/owner/orders/<int:order_id>/cancel", methods=["POST"])
@require_owner
def cancel_order(user: User, order_id):
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
            requested_by=Role.ADMIN,  # hoặc Role.RESTAURANT_OWNER nếu bạn muốn
            created_at=datetime.utcnow(),
            status=StatusRefund.REQUESTED
        )
        db.session.add(refund)

    db.session.commit()

    return jsonify({
        "order_id": order.order_id,
        "status": getattr(order.status, "value", order.status),
        "customer_name": order.customer.user.name,
        "reason": reason
    })
