from flask import Blueprint, jsonify, request
from sqlalchemy import func
from datetime import datetime
from zoneinfo import ZoneInfo

from OrderFood import db
from OrderFood.models import Order, Dish, CartItem, Payment

bp_stats = Blueprint("stats", __name__)

# =============================
# API doanh thu tổng (ngày / tháng)
# =============================
@bp_stats.route("/api/owner/<int:restaurant_id>/stats/revenue")
def revenue_summary(restaurant_id):
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    month = today.month
    year = today.year

    # Doanh thu ngày (tổng Order.total_price của đơn COMPLETED)
    day_total = db.session.query(func.coalesce(func.sum(Order.total_price), 0))\
        .filter(Order.restaurant_id == restaurant_id,
                func.date(Order.created_date) == today,
                Order.status == "COMPLETED").scalar()

    # Doanh thu tháng
    month_total = db.session.query(func.coalesce(func.sum(Order.total_price), 0))\
        .filter(Order.restaurant_id == restaurant_id,
                func.extract('month', Order.created_date) == month,
                func.extract('year', Order.created_date) == year,
                Order.status == "COMPLETED").scalar()

    return jsonify({
        "today": int(day_total),
        "month": int(month_total)
    })


# =============================
# API donut chart: số lượng món ăn
# =============================
@bp_stats.route("/api/owner/<int:restaurant_id>/stats/dishes")
def dish_stats(restaurant_id):
    mode = request.args.get("mode", "day")
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    month = today.month
    year = today.year

    query = db.session.query(
        Dish.name,
        func.sum(CartItem.quantity).label("qty")
    ).join(CartItem, CartItem.dish_id == Dish.dish_id) \
     .join(Order, Order.cart_id == CartItem.cart_id) \
     .filter(Order.restaurant_id == restaurant_id,
             Order.status == "COMPLETED")   # chỉ lấy đơn đã hoàn thành

    if mode == "day":
        query = query.filter(func.date(Order.created_date) == today)
    elif mode == "month":
        query = query.filter(func.extract("month", Order.created_date) == month,
                             func.extract("year", Order.created_date) == year)
    elif mode == "custom_month":
        selected_month = int(request.args.get("month", month))
        query = query.filter(func.extract("month", Order.created_date) == selected_month,
                             func.extract("year", Order.created_date) == year)
    elif mode == "quarter":
        selected_quarter = int(request.args.get("quarter", (month - 1) // 3 + 1))
        query = query.filter(func.extract("year", Order.created_date) == year,
                             func.extract("quarter", Order.created_date) == selected_quarter)

    data = query.group_by(Dish.name).all()

    return jsonify([{"dish": d[0], "quantity": int(d[1])} for d in data])



    data = query.group_by(Dish.name).all()

    return jsonify([{"dish": d[0], "quantity": int(d[1])} for d in data])

# =============================
# API line chart: doanh thu theo ngày/tháng
# =============================
@bp_stats.route("/api/owner/<int:restaurant_id>/stats/revenue_line")
def revenue_line(restaurant_id):
    mode = request.args.get("mode", "day")
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    month = today.month
    year = today.year

    if mode == "day":
        # ngày trong tháng hiện tại
        data = db.session.query(
            func.extract("day", Order.created_date).label("d"),
            func.coalesce(func.sum(Order.total_price), 0)
        ).filter(Order.restaurant_id == restaurant_id,
                 func.extract("month", Order.created_date) == month,
                 func.extract("year", Order.created_date) == year,
                 Order.status == "COMPLETED") \
         .group_by("d").order_by("d").all()
        return jsonify([{"label": int(d[0]), "revenue": int(d[1])} for d in data])

    elif mode == "month":
        # tất cả tháng trong năm hiện tại
        data = db.session.query(
            func.extract("month", Order.created_date).label("m"),
            func.coalesce(func.sum(Order.total_price), 0)
        ).filter(Order.restaurant_id == restaurant_id,
                 func.extract("year", Order.created_date) == year,
                 Order.status == "COMPLETED") \
         .group_by("m").order_by("m").all()
        return jsonify([{"label": f"Tháng {int(d[0])}", "revenue": int(d[1])} for d in data])

    elif mode == "custom_month":
        # ngày trong 1 tháng cụ thể
        selected_month = int(request.args.get("month", month))
        data = db.session.query(
            func.extract("day", Order.created_date).label("d"),
            func.coalesce(func.sum(Order.total_price), 0)
        ).filter(Order.restaurant_id == restaurant_id,
                 func.extract("month", Order.created_date) == selected_month,
                 func.extract("year", Order.created_date) == year,
                 Order.status == "COMPLETED") \
         .group_by("d").order_by("d").all()
        return jsonify([{"label": int(d[0]), "revenue": int(d[1])} for d in data])

    elif mode == "quarter":
        # doanh thu theo tháng trong quý
        selected_quarter = int(request.args.get("quarter", (month - 1) // 3 + 1))
        data = db.session.query(
            func.extract("month", Order.created_date).label("m"),
            func.coalesce(func.sum(Order.total_price), 0)
        ).filter(Order.restaurant_id == restaurant_id,
                 func.extract("year", Order.created_date) == year,
                 func.extract("quarter", Order.created_date) == selected_quarter,
                 Order.status == "COMPLETED") \
         .group_by("m").order_by("m").all()
        return jsonify([{"label": f"Tháng {int(d[0])}", "revenue": int(d[1])} for d in data])
