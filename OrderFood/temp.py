@app.route("/owner/res_register", methods=["GET", "POST"])
def res_register():
    if request.method == "GET":
        return render_template("owner/res_register.html")

    if request.method == "POST":
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "Chưa đăng nhập"}), 401

        # Check đã có restaurant chưa
        existing = Restaurant.query.filter_by(res_owner_id=user_id).first()
        if existing:
            return jsonify({"success": False, "error": "Bạn đã đăng ký nhà hàng rồi"}), 400

        name = request.form.get("name")
        address = request.form.get("address")
        open_hour = request.form.get("open_hour")
        close_hour = request.form.get("close_hour")
        tax = request.form.get("tax")
        image_url = request.form.get("image_url")

        if not all([name, address, open_hour, close_hour, tax]):
            return jsonify({"success": False, "error": "Thiếu thông tin bắt buộc"}), 400

        # cập nhật tax vào bảng restaurant_owner
        owner = RestaurantOwner.query.get(user_id)
        if owner:
            owner.tax = tax
        else:
            owner = RestaurantOwner(user_id=user_id, tax=tax)
            db.session.add(owner)

        # tạo restaurant
        restaurant = Restaurant(
            name=name,
            address=address,
            open_hour=open_hour,
            close_hour=close_hour,
            image=image_url,
            res_owner_id=user_id,
            status=StatusRes.PENDING
        )

        db.session.add(restaurant)
        db.session.commit()

        return jsonify({"success": True, "restaurant_id": restaurant.restaurant_id})


# ==========================API CHART ====================
@app.route("/api/owner/<int:restaurant_id>/stats/revenue")
def revenue_summary(restaurant_id):
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    month = today.month
    year = today.year

    # Doanh thu ngày (tổng payment đã PAID)
    day_total = db.session.query(func.coalesce(func.sum(Payment.amount), 0))\
        .join(Order, Order.order_id == Payment.order_id)\
        .filter(Order.restaurant_id == restaurant_id,
                func.date(Order.created_date) == today,
                Payment.status == "PAID").scalar()

    # Doanh thu tháng
    month_total = db.session.query(func.coalesce(func.sum(Payment.amount), 0))\
        .join(Order, Order.order_id == Payment.order_id)\
        .filter(Order.restaurant_id == restaurant_id,
                func.extract('month', Order.created_date) == month,
                func.extract('year', Order.created_date) == year,
                Payment.status == "PAID").scalar()

    return jsonify({
        "today": int(day_total/100),   # Payment.amount đang *100 theo VNPay
        "month": int(month_total/100)
    })


# =============================
# API donut chart: số lượng món ăn
# =============================
@app.route("/api/owner/<int:restaurant_id>/stats/dishes")
def dish_stats(restaurant_id):
    mode = request.args.get("mode", "day")
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    month = today.month
    year = today.year

    query = db.session.query(
        Dish.name,
        func.sum(CartItem.quantity).label("qty")
    ).join(CartItem, CartItem.dish_id == Dish.dish_id)\
     .join(Order, Order.cart_id == CartItem.cart_id)\
     .filter(Order.restaurant_id == restaurant_id,
             Order.status.in_(["PAID", "ACCEPTED", "COMPLETED"]))

    if mode == "day":
        query = query.filter(func.date(Order.created_date) == today)
    elif mode == "month":
        query = query.filter(func.extract("month", Order.created_date) == month,
                             func.extract("year", Order.created_date) == year)

    data = query.group_by(Dish.name).all()

    return jsonify([{"dish": d[0], "quantity": int(d[1])} for d in data])


# =============================
# API line chart: doanh thu theo ngày/tháng
# =============================
@app.route("/api/owner/<int:restaurant_id>/stats/revenue_line")
def revenue_line(restaurant_id):
    mode = request.args.get("mode", "day")
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    month = today.month
    year = today.year

    if mode == "day":
        data = db.session.query(
            func.extract("day", Order.created_date).label("d"),
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(Payment, Payment.order_id == Order.order_id)\
         .filter(Order.restaurant_id == restaurant_id,
                 func.extract("month", Order.created_date) == month,
                 func.extract("year", Order.created_date) == year,
                 Payment.status == "PAID")\
         .group_by("d").order_by("d").all()

        return jsonify([{"label": int(d[0]), "revenue": int(d[1]/100)} for d in data])

    elif mode == "month":
        data = db.session.query(
            func.extract("month", Order.created_date).label("m"),
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(Payment, Payment.order_id == Order.order_id)\
         .filter(Order.restaurant_id == restaurant_id,
                 func.extract("year", Order.created_date) == year,
                 Payment.status == "PAID")\
         .group_by("m").order_by("m").all()

        return jsonify([{"label": int(d[0]), "revenue": int(d[1]/100)} for d in data])


@app.route("/owner")
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

# ==================MENU=====================
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
    user = User.query.get(user_id)
    restaurant = user.restaurant_owner.restaurant

    categories = get_categories_by_owner_id(user_id)
    return render_template("owner/menu.html", dishes=dishes, categories=categories, restaurant = restaurant)


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

# =============== ORDER ===============
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
    restaurant = user.restaurant_owner.restaurant
    return render_template("owner/manage_orders.html",
                           pending_orders=pending_orders,
                           approved_orders=approved_orders,
                           cancelled_orders=cancelled_orders,
                           completed_orders=completed_orders,
                           res_id=res_id,
                           restaurant=restaurant
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



