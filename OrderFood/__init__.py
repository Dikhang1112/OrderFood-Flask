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
from apscheduler.schedulers.background import BackgroundScheduler
from atexit import register as atexit_register
from OrderFood.jobs import cancel_expired_orders

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

# ====== Seed/Clear flags ======
SEED_DB = os.getenv("SEED_DB", "false").lower() == "true"
SEED_CLEAR = os.getenv("SEED_CLEAR", "false").lower() == "true"
PRESERVE_TRANSACTIONS = os.getenv("PRESERVE_TRANSACTIONS", "true").lower() == "true"  # giữ Order/Payment/Cart

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-please-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS


    # Cloudinary (theo .env)
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )

    # Init extensions
    db.init_app(app)
    mail.init_app(app)

    # Admin blueprint + notifications
    from OrderFood import admin_service
    app.register_blueprint(admin_service.admin_bp)
    init_noti(app)

    # Google OAuth (OpenID Connect)
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # VNPay config
    app.config.update(
        VNP_TMN_CODE=os.getenv("VNP_TMN_CODE"),
        VNP_HASH_SECRET=os.getenv("VNP_HASH_SECRET"),
        VNP_PAY_URL=os.getenv("VNP_PAY_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"),
        VNP_RETURN_URL=os.getenv("VNP_RETURN_URL", "http://127.0.0.1:5000/vnpay_return"),
        VNP_IPN_URL=os.getenv("VNP_IPN_URL"),
    )

    with app.app_context():
        from OrderFood import models

        db.create_all()

        # --------- CLEAR DATA (chỉ khi bạn chủ động bật) ----------
        if SEED_CLEAR:
            if not PRESERVE_TRANSACTIONS:
                # Xoá theo thứ tự phụ thuộc để không vi phạm FK
                try:
                    db.session.query(models.Payment).delete()
                except Exception:
                    pass
                # Nếu có bảng OrderItem/OrderDetail thì xoá TRƯỚC Order
                # try: db.session.query(models.OrderItem).delete()
                # except Exception: pass

                db.session.query(models.Order).delete()
                db.session.query(models.CartItem).delete()
                db.session.query(models.Cart).delete()

                db.session.query(models.Dish).delete()
                db.session.query(models.Category).delete()
                db.session.query(models.Restaurant).delete()
                db.session.query(models.RestaurantOwner).delete()
                db.session.query(models.Admin).delete()
                db.session.query(models.Customer).delete()
                db.session.query(models.User).delete()
                db.session.commit()
            else:
                # Giữ nguyên dữ liệu giao dịch & user/customer/restaurant để không mất lịch sử
                pass

        # --------- SEED DATA (chỉ khi cần) ----------
        if SEED_DB:
            # Chỉ seed khi DB chưa có dữ liệu để tránh đè dữ liệu thật
            already_seeded = (models.Restaurant.query.count() > 0) or (models.User.query.count() > 0)
            if not already_seeded:
                password = generate_password_hash("123")

                # ========== CUSTOMERS ==========
                u1 = models.User(user_id=1, name="cus1", email="cus1@gmail.com", password=password, role="CUSTOMER")
                u2 = models.User(user_id=2, name="cus2", email="cus2@gmail.com", password=password, role="CUSTOMER")
                u3 = models.User(user_id=3, name="cus3", email="cus3@gmail.com", password=password, role="CUSTOMER")

                # ========== ADMINS ==========
                a1 = models.User(user_id=4, name="a1", email="a1@gmail.com", password=password, role="ADMIN")
                a2 = models.User(user_id=5, name="a2", email="a2@gmail.com", password=password, role="ADMIN")

                db.session.add_all([u1, u2, u3, a1, a2])
                db.session.commit()

                # Admin table
                ad1 = models.Admin(user_id=a1.user_id)
                ad2 = models.Admin(user_id=a2.user_id)
                db.session.add_all([ad1, ad2])
                db.session.commit()

                c1 = models.Customer(user_id=u1.user_id)
                c2 = models.Customer(user_id=u2.user_id)
                c3 = models.Customer(user_id=u3.user_id)
                db.session.add_all([c1, c2, c3])
                db.session.commit()

                # ========== RESTAURANT OWNERS + RESTAURANTS + CATEGORIES + DISHES ==========
                import random

                restaurant_names = [f"Nha hang {i}" for i in range(1, 51)]
                dish_names = ["Cơm tấm", "Mì xào", "Trà sữa", "Phở bò", "Bánh mì", "Hủ tiếu", "Gà rán"]
                category_names = ["Món chính", "Đồ uống", "Ăn vặt", "Tráng miệng", "Lẩu", "Cơm phần"]

                owners_to_add = []
                restaurants_to_add = []
                categories_to_add = []
                dishes_to_add = []

                next_user_id = 6  # sau admin
                next_restaurant_id = 1
                next_category_id = 1
                next_dish_id = 1

                for res_name in restaurant_names:
                    # User (RestaurantOwner)
                    ro_user = models.User(
                        user_id=next_user_id,
                        name=f"ro{next_user_id}",
                        email=f"ro{next_user_id}@gmail.com",
                        password=password,
                        role="RESTAURANT_OWNER",
                    )
                    db.session.add(ro_user)
                    db.session.flush()  # để lấy user_id

                    ro = models.RestaurantOwner(user_id=ro_user.user_id)
                    owners_to_add.append(ro)

                    res = models.Restaurant(
                        restaurant_id=next_restaurant_id,
                        name=res_name,
                        res_owner_id=ro.user_id,
                        status="PENDING",
                        image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res1_inrqfg.jpg",
                        by_admin_id=a1.user_id,
                        address=random.choice(["Ho Chi Minh", "Ha Noi", "Da Nang", "Can Tho", "Da Lat", "Vinh Long"]),
                        rating_point=round(random.uniform(1.0, 5.0), 1),
                    )
                    restaurants_to_add.append(res)

                    # Mỗi nhà hàng có 2 category riêng
                    chosen_cats = random.sample(category_names, k=2)
                    res_categories = []
                    for cat_name in chosen_cats:
                        cat = models.Category(
                            category_id=next_category_id,
                            name=cat_name,
                            res_id=next_restaurant_id
                        )
                        categories_to_add.append(cat)
                        res_categories.append(cat)
                        next_category_id += 1

                    # Mỗi category có 3 món ăn
                    for cat in res_categories:
                        for _ in range(3):
                            dish_name = random.choice(dish_names)
                            dish = models.Dish(
                                dish_id=next_dish_id,
                                res_id=next_restaurant_id,
                                category_id=cat.category_id,
                                name=dish_name,
                                is_available=True,
                                price=random.randint(20000, 100000),
                                note=f"Note {dish_name}",
                                image="https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_afjhjb.jpg",
                            )
                            dishes_to_add.append(dish)
                            next_dish_id += 1

                    next_user_id += 1
                    next_restaurant_id += 1

                # Lưu vào DB
                db.session.add_all(owners_to_add)
                db.session.add_all(restaurants_to_add)
                db.session.add_all(categories_to_add)
                db.session.add_all(dishes_to_add)
                db.session.commit()
            # nếu đã có dữ liệu: bỏ qua seeding để bảo toàn giao dịch
    scheduler = BackgroundScheduler(daemon=True)

    def _run_job():
        with app.app_context():
            cancel_expired_orders()

    scheduler.add_job(_run_job, "interval", seconds=60, id="cancel_expired_orders")
    scheduler.start()

    # Khi app shutdown thì stop scheduler
    atexit_register(lambda: scheduler.shutdown(wait=False))
    # ==========================================
    return app

app = create_app()