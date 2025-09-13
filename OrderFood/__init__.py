import os
from urllib.parse import quote

from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash
import cloudinary

from OrderFood.helper.NotiHelper import init_app as init_noti

# ================== Load .env ==================
load_dotenv()

# ================== Global extensions ==================
db = SQLAlchemy()
mail = Mail()
oauth = OAuth()

# ================== ENV & defaults ==================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-please-change-me")

SQLALCHEMY_DATABASE_URI = os.getenv(
    "SQLALCHEMY_DATABASE_URI",
    "mysql+pymysql://root:%s@localhost/orderfooddb?charset=utf8mb4" % quote("Admin@123"),
)
SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "false").lower() == "true"

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "orderFood@gmail.com")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Seed flags
SEED_DB = os.getenv("SEED_DB", "false").lower() == "true"
SEED_CLEAR = os.getenv("SEED_CLEAR", "false").lower() == "true"


def _init_cloudinary():
    """
    Cấu hình Cloudinary nếu đủ biến môi trường. Không hard-code secret ở code.
    """
    if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
        )


def _init_oauth(app: Flask):
    """
    Khởi tạo OAuth Google nếu có CLIENT_ID/SECRET.
    """
    oauth.init_app(app)
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        oauth.register(
            name="google",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def _seed_small_sample():
    """Seed nhẹ: 3 khách, 3 chủ quán, 2 admin, 3 nhà hàng, 5 món."""
    from sqlalchemy import text
    from OrderFood import models

    if SEED_CLEAR:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for tbl in [
            models.CartItem, models.Cart, models.Dish, models.Category,
            models.Restaurant, models.RestaurantOwner, models.Admin,
            models.Customer, models.User,
        ]:
            db.session.query(tbl).delete()
        db.session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.session.commit()

    pwd = generate_password_hash("123")

    # Users
    u1 = models.User(user_id=1, name='cus1', email='cus1@gmail.com', password=pwd, role='CUSTOMER')
    u2 = models.User(user_id=2, name='cus2', email='cus2@gmail.com', password=pwd, role='CUSTOMER')
    u3 = models.User(user_id=3, name='cus3', email='cus3@gmail.com', password=pwd, role='CUSTOMER')

    ro1 = models.User(user_id=4, name='ro1', email='ro1@gmail.com', password=pwd, role='RESTAURANT_OWNER',
                      phone='01346578989', avatar='')
    ro2 = models.User(user_id=5, name='ro2', email='ro2@gmail.com', password=pwd, role='RESTAURANT_OWNER',
                      phone='0134657589')
    ro3 = models.User(user_id=6, name='ro3', email='ro3@gmail.com', password=pwd, role='RESTAURANT_OWNER',
                      phone='0134657137')

    a1 = models.User(user_id=7, name="a1", email="a1@gmail.com", password=pwd, role="ADMIN")
    a2 = models.User(user_id=8, name="a2", email="a2@gmail.com", password=pwd, role="ADMIN")

    db.session.add_all([u1, u2, u3, ro1, ro2, ro3, a1, a2])
    db.session.commit()

    # Role tables
    db.session.add_all([
        models.Customer(user_id=u1.user_id),
        models.Customer(user_id=u2.user_id),
        models.Customer(user_id=u3.user_id),
        models.RestaurantOwner(user_id=ro1.user_id, tax='132165464654'),
        models.RestaurantOwner(user_id=ro2.user_id, tax='999999999'),
        models.RestaurantOwner(user_id=ro3.user_id, tax='465782135'),
        models.Admin(user_id=a1.user_id),
        models.Admin(user_id=a2.user_id),
    ])
    db.session.commit()

    # Restaurants
    res1 = models.Restaurant(
        restaurant_id=1, name='Nha hang 1', res_owner_id=ro1.user_id, status='PENDING',
        image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res3_uezgk3.jpg",
        by_admin_id=a1.user_id, address='Vinh Long', open_hour="08:00", close_hour="22:00", rating_point=4.2
    )
    res2 = models.Restaurant(
        restaurant_id=2, name='Nha hang 2', res_owner_id=ro2.user_id, status='PENDING',
        image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res2_gkskxx.jpg",
        by_admin_id=a2.user_id, address='Ho Chi Minh', open_hour="09:00", close_hour="21:30", rating_point=3.8
    )
    res3 = models.Restaurant(
        restaurant_id=3, name='Nha hang 3', res_owner_id=ro3.user_id, status='PENDING',
        image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res1_inrqfg.jpg",
        by_admin_id=a1.user_id, address='Da Lat', open_hour="07:30", close_hour="20:00", rating_point=4.5
    )
    db.session.add_all([res1, res2, res3])
    db.session.commit()

    # Dishes
    d1 = models.Dish(dish_id=1, res_id=1, name='Cơm tấm', is_available=True, price=10000, note="a",
                     image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_afjhjb.jpg")
    d2 = models.Dish(dish_id=2, res_id=1, name='Mì xào', is_available=True, price=10000, note="b",
                     image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_3_qo5lms.jpg")
    d3 = models.Dish(dish_id=3, res_id=2, name='Cơm tấm', is_available=True, price=10000, note="c",
                     image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_1_lfohho.jpg")
    d4 = models.Dish(dish_id=4, res_id=2, name='Mì xào', is_available=True, price=10000, note="d",
                     image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_2_btt5x7.jpg")
    d5 = models.Dish(dish_id=5, res_id=3, name='Trà sữa', is_available=True, price=5000, note="e",
                     image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_4_uazlee.jpg")
    db.session.add_all([d1, d2, d3, d4, d5])
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=SQLALCHEMY_DATABASE_URI,
        SQLALCHEMY_TRACK_MODIFICATIONS=SQLALCHEMY_TRACK_MODIFICATIONS,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_PORT=MAIL_PORT,
        MAIL_USE_TLS=MAIL_USE_TLS,
        MAIL_USE_SSL=MAIL_USE_SSL,
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_DEFAULT_SENDER=MAIL_DEFAULT_SENDER,
    )

    # Init extensions
    db.init_app(app)
    mail.init_app(app)
    _init_cloudinary()
    _init_oauth(app)

    # Đăng ký blueprint sau khi init extensions để tránh circular import
    from OrderFood import admin_service  # file: OrderFood/admin_service.py
    app.register_blueprint(admin_service.admin_bp)

    # Notifications
    init_noti(app)

    # Tạo bảng & seed (nếu bật)
    with app.app_context():
        from OrderFood import models  # đảm bảo models được import khi app context có sẵn
        db.create_all()
        if SEED_DB:
            _seed_small_sample()

    return app


# WSGI entrypoint nếu chạy `flask run` hoặc gunicorn
app = create_app()
