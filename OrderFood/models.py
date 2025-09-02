
# OrderFood/models.py
from enum import Enum
from sqlalchemy import UniqueConstraint
from sqlalchemy import Enum as SAEnum
from OrderFood import db


# =========================
# ENUMS
# =========================
class Role(Enum):
    CUSTOMER = "CUSTOMER"
    RESTAURANT_OWNER = "RESTAURANT_OWNER"
    ADMIN = "ADMIN"

class StatusRes(Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class StatusCart(Enum):
    ACTIVE   = "ACTIVE"
    SAVED    = "SAVED"
    CHECKOUT = "CHECKOUT"

class StatusOrder(Enum):
    PENDING   = "PENDING"
    PAID      = "PAID"
    CANCELED  = "CANCELED"
    COMPLETED = "COMPLETED"

class StatusPayment(Enum):
    PENDING  = "PENDING"
    PAID     = "PAID"
    CANCELED = "CANCELED"
    REFUND   = "REFUND"

class StatusRefund(Enum):
    REQUESTED  = "REQUESTED"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"


# =========================
# USER + ROLES
# =========================
class User(db.Model):
    __tablename__ = "user"

    user_id  = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone    = db.Column(db.String(20))

    role     = db.Column(SAEnum(Role, name="role_enum"), nullable=False, default=Role.CUSTOMER)

    customer          = db.relationship("Customer",        uselist=False, back_populates="user", cascade="all, delete-orphan")
    restaurant_owner  = db.relationship("RestaurantOwner", uselist=False, back_populates="user", cascade="all, delete-orphan")
    admin             = db.relationship("Admin",           uselist=False, back_populates="user", cascade="all, delete-orphan")


class RestaurantOwner(db.Model):
    __tablename__ = "restaurant_owner"

    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    tax     = db.Column(db.String(50))

    user  = db.relationship("User", back_populates="restaurant_owner")
    # 1 owner -> 1 restaurant
    restaurant = db.relationship(
        "Restaurant",
        uselist=False,
        back_populates="owner",
        cascade="all, delete-orphan",
        single_parent=True,
    )


class Customer(db.Model):
    __tablename__ = "customer"

    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    user    = db.relationship("User", back_populates="customer")


class Admin(db.Model):
    __tablename__ = "admin"

    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    user    = db.relationship("User", back_populates="admin")

    # 1 admin có thể duyệt nhiều restaurant
    restaurants_approved = db.relationship("Restaurant", back_populates="approved_by")


# =========================
# RESTAURANT
# =========================
class Restaurant(db.Model):
    __tablename__ = "restaurant"

    restaurant_id = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(150), nullable=False)

    # 1 chủ chỉ có 1 nhà hàng
    res_owner_id  = db.Column(
        db.Integer,
        db.ForeignKey("restaurant_owner.user_id"),
        nullable=False,
        unique=True,
    )

    open_hour  = db.Column(db.String(20))
    close_hour = db.Column(db.String(20))
    status     = db.Column(SAEnum(StatusRes, name="status_res_enum"), nullable=False, default=StatusRes.PENDING)

    # null khi chưa duyệt
    by_admin_id  = db.Column(db.Integer, db.ForeignKey("admin.user_id"), nullable=True)
    address      = db.Column(db.String(255))
    rating_point = db.Column(db.Float, default=0.0)

    owner       = db.relationship("RestaurantOwner", back_populates="restaurant")
    approved_by = db.relationship("Admin", back_populates="restaurants_approved")


# =========================
# DISH
# =========================
class Dish(db.Model):
    __tablename__ = "dish"

    dish_id      = db.Column(db.Integer, primary_key=True)
    res_id       = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    name         = db.Column(db.String(150), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    price        = db.Column(db.Float, nullable=False)
    note         = db.Column(db.String(255))

    restaurant = db.relationship("Restaurant", backref=db.backref("dishes", cascade="all, delete-orphan"))


# =========================
# CART + CART ITEM
# =========================
class Cart(db.Model):
    __tablename__ = "cart"

    cart_id = db.Column(db.Integer, primary_key=True)

    cus_id  = db.Column(db.Integer, db.ForeignKey("customer.user_id"),   nullable=False)
    res_id  = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    status  = db.Column(SAEnum(StatusCart, name="status_cart_enum"), nullable=False, default=StatusCart.ACTIVE)

    is_open = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("cus_id", "res_id", "is_open", name="uq_cart_open_per_customer_restaurant"),
    )

    customer   = db.relationship("Customer",   backref=db.backref("carts", cascade="all, delete-orphan"))
    restaurant = db.relationship("Restaurant", backref=db.backref("carts", cascade="all, delete-orphan"))


class CartItem(db.Model):
    __tablename__ = "cart_item"

    cart_item_id = db.Column(db.Integer, primary_key=True)
    cart_id      = db.Column(db.Integer, db.ForeignKey("cart.cart_id"), nullable=False)
    dish_id      = db.Column(db.Integer, db.ForeignKey("dish.dish_id"), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=1)

    cart = db.relationship("Cart", backref=db.backref("items", cascade="all, delete-orphan"))
    dish = db.relationship("Dish", backref=db.backref("cart_items", cascade="all, delete-orphan"))

    __table_args__ = (
        UniqueConstraint("cart_id", "dish_id", name="uq_cart_item_unique_dish"),
    )


# =========================
# ORDER + NOTIFICATION + RATING
# =========================
class Order(db.Model):
    __tablename__ = "order"   # cân nhắc đổi thành "orders" để tránh xung đột keyword

    order_id      = db.Column(db.Integer, primary_key=True)
    customer_id   = db.Column(db.Integer, db.ForeignKey("customer.user_id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    cart_id       = db.Column(db.Integer, db.ForeignKey("cart.cart_id"), nullable=False)

    status        = db.Column(SAEnum(StatusOrder, name="status_order_enum"), nullable=False, default=StatusOrder.PENDING)
    total_price   = db.Column(db.Float, nullable=False)

    delivery_id   = db.Column(db.Integer, db.ForeignKey("admin.user_id"), nullable=True)  # nếu có

    waiting_time  = db.Column(db.DateTime)        # do admin set
    created_date  = db.Column(db.DateTime, nullable=False)

    customer   = db.relationship("Customer",   backref=db.backref("orders", cascade="all, delete-orphan"))
    restaurant = db.relationship("Restaurant", backref=db.backref("orders", cascade="all, delete-orphan"))
    cart       = db.relationship("Cart",       backref=db.backref("order", uselist=False))
    admin      = db.relationship("Admin",      backref=db.backref("orders", cascade="all, delete-orphan"))


class Notification(db.Model):
    __tablename__ = "notification"

    noti_id   = db.Column(db.Integer, primary_key=True)
    order_id  = db.Column(db.Integer, db.ForeignKey("order.order_id"), nullable=False)

    message   = db.Column(db.String(255), nullable=False)
    create_at = db.Column(db.DateTime, nullable=False)
    is_read   = db.Column(db.Boolean, default=False)

    order = db.relationship("Order", backref=db.backref("notifications", cascade="all, delete-orphan"))


class OrderRating(db.Model):
    __tablename__ = "order_rating"

    orating_id  = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey("order.order_id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.user_id"), nullable=False)

    rating   = db.Column(db.Integer, nullable=False)  # 1-5
    comment  = db.Column(db.String(255))

    order    = db.relationship("Order",    backref=db.backref("ratings", cascade="all, delete-orphan"))
    customer = db.relationship("Customer", backref=db.backref("ratings", cascade="all, delete-orphan"))


# =========================
# PAYMENT + REFUND
# =========================
class Payment(db.Model):
    __tablename__ = "payment"

    payment_id = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("order.order_id"), nullable=False)

    status     = db.Column(SAEnum(StatusPayment, name="status_payment_enum"),
                           nullable=False, default=StatusPayment.PENDING)

    order = db.relationship("Order", backref=db.backref("payment", uselist=False))


class Refund(db.Model):
    __tablename__ = "refund"

    refund_id    = db.Column(db.Integer, primary_key=True)
    payment_id   = db.Column(db.Integer, db.ForeignKey("payment.payment_id"), nullable=False)

    status       = db.Column(SAEnum(StatusRefund, name="status_refund_enum"),
                             nullable=False, default=StatusRefund.REQUESTED)
    reason       = db.Column(db.String(255))

    # dùng lại Role (CUSTOMER / RESTAURANT_OWNER / ADMIN)
    requested_by = db.Column(SAEnum(Role, name="request_by_enum"), nullable=False)

    created_at   = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)

    payment = db.relationship("Payment", backref=db.backref("refunds", cascade="all, delete-orphan"))


# =========================
# CREATE TABLES (optional)
# =========================
# if __name__ == "__main__":
#    with app.app_context():
#        db.create_all()
#        print("Created tables.")
