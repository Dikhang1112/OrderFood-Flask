# OrderFood/models.py
from datetime import timedelta, datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo

from sqlalchemy import Enum as SAEnum, String, Index
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from OrderFood import db
from flask_login import UserMixin


# =========================
# ENUMS
# =========================
class Role(Enum):
    CUSTOMER = "CUSTOMER"
    RESTAURANT_OWNER = "RESTAURANT_OWNER"
    ADMIN = "ADMIN"


class StatusRes(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StatusCart(Enum):
    ACTIVE = "ACTIVE"
    SAVED = "SAVED"
    CHECKOUT = "CHECKOUT"


class StatusOrder(Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    ACCEPTED = "ACCEPTED"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"


class StatusPayment(Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELED = "CANCELED"
    REFUND = "REFUND"


class StatusRefund(Enum):
    REQUESTED = "REQUESTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# =========================
# USER + ROLES
# =========================
class User(db.Model, UserMixin):
    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    avatar = db.Column(db.String(255))  # lưu URL từ Cloudinary
    phone = db.Column(db.String(20))

    role = db.Column(SAEnum(Role, name="role_enum"), nullable=False, default=Role.CUSTOMER)

    customer = db.relationship("Customer", uselist=False, back_populates="user", cascade="all, delete-orphan")
    restaurant_owner = db.relationship("RestaurantOwner", uselist=False, back_populates="user",
                                       cascade="all, delete-orphan")
    admin = db.relationship("Admin", uselist=False, back_populates="user", cascade="all, delete-orphan")

    @property
    def id(self):
        return self.user_id


class RestaurantOwner(db.Model):
    __tablename__ = "restaurant_owner"

    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    tax = db.Column(db.String(50))

    user = db.relationship("User", back_populates="restaurant_owner")
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

    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True, autoincrement=True)
    user = db.relationship("User", back_populates="customer")


class Admin(db.Model):
    __tablename__ = "admin"

    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True, autoincrement=True)
    user = db.relationship("User", back_populates="admin")

    # 1 admin có thể duyệt nhiều restaurant
    restaurants_approved = db.relationship("Restaurant", back_populates="approved_by")


# =========================
# RESTAURANT
# =========================
class Restaurant(db.Model):
    __tablename__ = "restaurant"

    restaurant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)

    # 1 chủ chỉ có 1 nhà hàng
    res_owner_id = db.Column(
        db.Integer,
        db.ForeignKey("restaurant_owner.user_id"),
        nullable=False,
        unique=True,
    )

    open_hour = db.Column(db.String(20))
    close_hour = db.Column(db.String(20))
    status = db.Column(SAEnum(StatusRes, name="status_res_enum"), nullable=False, default=StatusRes.PENDING)
    image = db.Column(String(255))
    # null khi chưa duyệt
    by_admin_id = db.Column(db.Integer, db.ForeignKey("admin.user_id"), nullable=True)
    address = db.Column(db.String(255))
    rating_point = db.Column(db.Float, default=0.0)

    owner = db.relationship("RestaurantOwner", back_populates="restaurant")
    approved_by = db.relationship("Admin", back_populates="restaurants_approved")


# =========================
# DISH
# =========================
class Dish(db.Model):
    __tablename__ = "dish"
    dish_id      = db.Column(db.Integer, primary_key=True,autoincrement=True)
    res_id       = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.category_id"), nullable=True)
    name         = db.Column(db.String(150), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    image = db.Column(db.String(255))  # lưu URL từ Cloudinary
    restaurant = db.relationship("Restaurant", backref=db.backref("dishes", cascade="all, delete-orphan"))

# =========================
# CATEGORY
# =========================

class Category(db.Model):
    __tablename__ = "category"

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name        = db.Column(db.String(100), nullable=False)

    # mỗi category chỉ thuộc về 1 restaurant
    res_id      = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    restaurant  = db.relationship("Restaurant", backref=db.backref("categories", cascade="all, delete-orphan"))

    # 1 category có nhiều dish
    dishes      = db.relationship("Dish", backref="category", cascade="all, delete-orphan")


# =========================
# CART + CART ITEM
# =========================
class Cart(db.Model):
    __tablename__ = "cart"

    cart_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cus_id = db.Column(db.Integer, db.ForeignKey("customer.user_id"), nullable=False)
    res_id = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    status = db.Column(SAEnum(StatusCart, name="status_cart_enum"), nullable=False, default=StatusCart.ACTIVE)

    __table_args__ = (
        Index('ix_cart_customer_restaurant', 'cus_id', 'res_id'),
    )

    customer = db.relationship("Customer", backref=db.backref("carts", cascade="all, delete-orphan"))
    restaurant = db.relationship("Restaurant", backref=db.backref("carts", cascade="all, delete-orphan"))


class CartItem(db.Model):
    __tablename__ = "cart_item"

    cart_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.cart_id"), nullable=False, index=True)
    dish_id = db.Column(db.Integer, db.ForeignKey("dish.dish_id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    cart = db.relationship("Cart", backref=db.backref("items", cascade="all, delete-orphan"))
    dish = db.relationship("Dish", backref=db.backref("cart_items", cascade="all, delete-orphan"))

    __table_args__ = (
        UniqueConstraint("cart_id", "dish_id", name="uq_cart_item_unique_dish"),
    )


# =========================
# ORDER + NOTIFICATION + RATING
# =========================
class Order(db.Model):
    __tablename__ = "order"

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.user_id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurant.restaurant_id"), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.cart_id"), nullable=False, unique=True)

    status = db.Column(SAEnum(StatusOrder, name="status_order_enum"), nullable=False, default=StatusOrder.PENDING)
    total_price = db.Column(db.Float, nullable=False)

    delivery_id = db.Column(db.Integer, db.ForeignKey("admin.user_id"), nullable=True)  # nếu có

    waiting_time = db.Column(db.Integer, nullable=False, default=10)  # đơn vị: phút

    created_date =  db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    )
    canceled_by = db.Column(SAEnum(Role, name="order_canceled_by_enum"), nullable=True)


    customer = db.relationship("Customer", backref=db.backref("orders", cascade="all, delete-orphan"))
    restaurant = db.relationship("Restaurant", backref=db.backref("orders", cascade="all, delete-orphan"))
    cart = db.relationship("Cart", backref=db.backref("order", uselist=False))
    admin = db.relationship("Admin", backref=db.backref("orders", cascade="all, delete-orphan"))

    @property
    def expire_time(self):
        """Thời điểm hết hạn = created_date + waiting_time (phút), UTC-aware."""
        cdt = self.created_date
        if not cdt:
            return None
        if cdt.tzinfo is None:
            cdt = cdt.replace(tzinfo=timezone.utc)
        return cdt + timedelta(minutes=int(self.waiting_time or 0))

    @property
    def is_expired(self):
        et = self.expire_time
        if not et:
            return False
        return datetime.now(timezone.utc) >= et




class Notification(db.Model):
    __tablename__ = "notification"

    noti_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.order_id"), nullable=False)

    # target
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.user_id"), nullable=True)
    owner_id    = db.Column(db.Integer, db.ForeignKey("restaurant_owner.user_id"), nullable=True)

    message   = db.Column(db.String(255), nullable=False)

    is_read   = db.Column(db.Boolean, default=False)
    create_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")))

    order = db.relationship("Order", backref=db.backref("notifications", cascade="all, delete-orphan"))

    __table_args__ = (
        db.Index("idx_noti_cus_unread", "customer_id", "is_read"),
        db.Index("idx_noti_owner_unread", "owner_id", "is_read"),
    )

class OrderRating(db.Model):
    __tablename__ = "order_rating"

    orating_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.order_id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.user_id"), nullable=False)

    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.String(255))

    order = db.relationship("Order", backref=db.backref("ratings", cascade="all, delete-orphan"))
    customer = db.relationship("Customer", backref=db.backref("ratings", cascade="all, delete-orphan"))


# =========================
# PAYMENT + REFUND
# =========================
class Payment(db.Model):
    __tablename__ = "payment"

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.order_id"), nullable=False, unique=True)
    txn_ref = db.Column(db.String(64), nullable=False, unique=True, index=True)  # VNPay vnp_TxnRef
    amount = db.Column(db.Integer, nullable=False)  # số tiền gửi sang VNPay (VND * 100)
    status = db.Column(SAEnum(StatusPayment, name="status_payment_enum"),
                       nullable=False, default=StatusPayment.PENDING)
    created_at =  db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    )




    order = db.relationship("Order", backref=db.backref("payment", uselist=False))


class Refund(db.Model):
    __tablename__ = "refund"

    refund_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payment.payment_id"), nullable=False)

    status = db.Column(SAEnum(StatusRefund, name="status_refund_enum"),
                       nullable=False, default=StatusRefund.REQUESTED)
    reason = db.Column(db.String(255))



    created_at =  db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    )
    completed_at = db.Column(db.DateTime)

    payment = db.relationship("Payment", backref=db.backref("refunds", cascade="all, delete-orphan"))
