# OrderFood/owner.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from OrderFood.models import User, Restaurant, Dish, Category, StatusOrder, StatusCart, Refund, Payment, StatusRefund, Role, Order
from OrderFood.dao_index import *
from OrderFood import db
from datetime import datetime
from sqlalchemy import func

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")

# ================= Helpers =================
def is_owner(role):
    return (role or "").lower() == "restaurant_owner"

# ================= Owner Home =================
@owner_bp.route("/")
def owner_home():
    if not is_owner(session.get("role")):
        return redirect(url_for("login"))
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    user = User.query.get(user_id)
    restaurant = None
    if user and user.restaurant_owner:
        restaurant = user.restaurant_owner.restaurant
    return render_template("owner_home.html", restaurant=restaurant)

# ================= Menu =================
@owner_bp.route("/menu")
def get_menu():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    keyword = (request.args.get('keyword') or '').strip()
    if not keyword:
        dishes = load_menu_owner(user_id)
    else:
        dishes = get_dishes_by_name(user_id, keyword)
    user = User.query.get(user_id)
    restaurant = user.restaurant_owner.restaurant
    categories = get_categories_by_owner_id(user_id)
    return render_template("owner/menu.html", dishes=dishes, categories=categories, restaurant=restaurant)

@owner_bp.route("/add_dish", methods=["POST"])
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

@owner_bp.route("/menu/<int:dish_id>", methods=["POST"])
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
        return jsonify({"success": False, "error": str(e)}), 500

@owner_bp.route("/menu/<int:dish_id>", methods=["DELETE"])
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
        return jsonify({"success": False, "error": str(e)}), 500

# ================= Orders =================
@owner_bp.route("/orders")
def manage_orders():
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    if not user_id:
        return redirect(url_for("login"))

    if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
        return jsonify({"success": False, "error": "Bạn chưa có nhà hàng"})

    res_id = user.restaurant_owner.restaurant.restaurant_id

    pending_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.PAID).all()
    approved_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.ACCEPTED).all()
    cancelled_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.CANCELED).all()
    completed_orders = Order.query.filter_by(restaurant_id=res_id, status=StatusOrder.COMPLETED).all()
    restaurant = user.restaurant_owner.restaurant
    return render_template("owner/manage_orders.html",
                           pending_orders=pending_orders,
                           approved_orders=approved_orders,
                           cancelled_orders=cancelled_orders,
                           completed_orders=completed_orders,
                           res_id=res_id,
                           restaurant=restaurant)

@owner_bp.route("/orders/<int:order_id>/approve", methods=["POST"])
def approve_order(order_id):
    order = Order.query.get_or_404(order_id)
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

@owner_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    reason = data.get("reason", "")

    if isinstance(order.status, str):
        order.status = StatusOrder.CANCELED.value
    else:
        order.status = StatusOrder.CANCELED

    db.session.add(order)

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
    return jsonify({
        "order_id": order.order_id,
        "status": getattr(order.status, "value", order.status),
        "customer_name": order.customer.user.name,
        "reason": reason
    })


# ================= Restaurant Management =================
@owner_bp.route("/restaurant", methods=["GET"])
def manage_restaurant():
    user_id = session.get("user_id")
    if not user_id or not is_owner(session.get("role")):
        return redirect(url_for("login"))

    user = User.query.get(user_id)
    if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
        return "Bạn chưa có nhà hàng", 400

    restaurant = user.restaurant_owner.restaurant
    owner = user.restaurant_owner

    return render_template("owner/manage_res.html", restaurant=restaurant, owner=owner)


@owner_bp.route("/restaurant/update", methods=["POST"])
def update_restaurant():
    user_id = session.get("user_id")
    if not user_id or not is_owner(session.get("role")):
        return jsonify({"success": False, "error": "Chưa đăng nhập"}), 401

    user = User.query.get(user_id)
    if not user or not user.restaurant_owner or not user.restaurant_owner.restaurant:
        return jsonify({"success": False, "error": "Bạn chưa có nhà hàng"}), 400

    restaurant = user.restaurant_owner.restaurant
    owner = user.restaurant_owner

    data = request.get_json() or {}

    try:
        restaurant.name = data.get("name", restaurant.name)
        restaurant.address = data.get("address", restaurant.address)
        restaurant.open_hour = data.get("open_hour", restaurant.open_hour)
        restaurant.close_hour = data.get("close_hour", restaurant.close_hour)
        restaurant.is_open = data.get("is_open", restaurant.is_open)
        owner.tax = data.get("tax", owner.tax)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
