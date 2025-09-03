import cloudinary
import werkzeug
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
import os
from werkzeug.security import generate_password_hash


db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-please-change-me")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:%s@localhost/orderfoobdb?charset=utf8mb4' %quote('Admin@123')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    cloudinary.config(cloud_name='dlwjqml4p',
                      api_key='265111814635295',
                      api_secret='5G5OpHo38qsK_si-A49j4eAjpOA')
    db.init_app(app)
    with app.app_context():
        from OrderFood import models

        db.create_all()# noqa: F401


        db.session.query(models.CartItem).delete()
        db.session.query(models.Cart).delete()
        db.session.query(models.Dish).delete()
        db.session.query(models.Restaurant).delete()
        db.session.query(models.RestaurantOwner).delete()
        db.session.query(models.Admin).delete()
        db.session.query(models.User).delete()
        db.session.commit()



        password = '123'
        password = generate_password_hash(password)

        u1 =models.User(user_id = 1, name = 'cus1', email = 'cus1@gmail.com', password = password, role='CUSTOMER')
        u2 =models.User(user_id = 2, name = 'cus2', email = 'cus2@gmail.com', password = password, role='CUSTOMER')
        u3 =models.User(user_id = 3, name = 'cus3', email = 'cus3@gmail.com', password = password, role='CUSTOMER')

        ro1 =models.User(user_id = 4, name = 'ro1', email = 'ro1@gmail.com', password = password, role='RESTAURANT_OWNER')
        ro2 =models.User(user_id = 5, name = 'ro2', email = 'ro2@gmail.com', password = password, role='RESTAURANT_OWNER')
        ro3 =models.User(user_id = 6, name = 'ro3', email = 'ro3@gmail.com', password = password, role='RESTAURANT_OWNER')

        a1 = models.User(user_id=7, name='a1', email='a1@gmail.com', password=password, role='ADMIN')
        a2 = models.User(user_id=8, name='a2', email='a2@gmail.com', password=password, role='ADMIN')

        db.session.add_all([u1, u2, u3, ro1, ro2, ro3, a1, a2])
        db.session.commit()

        owner1 = models.RestaurantOwner(user_id = ro1.user_id)
        owner2 = models.RestaurantOwner(user_id = ro2.user_id)
        owner3 = models.RestaurantOwner(user_id = ro3.user_id)

        db.session.add_all([owner1, owner2, owner3])
        db.session.commit()

        ad1 = models.Admin(user_id = a1.user_id)
        ad2 = models.Admin(user_id = a2.user_id)

        db.session.add_all([ad1, ad2])
        db.session.commit()

        res1 = models.Restaurant(restaurant_id = 1, name='res1', res_owner_id = owner1.user_id, status = 'APPROVED', image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res3_uezgk3.jpg", by_admin_id = a1.user_id)
        res2 = models.Restaurant(restaurant_id = 2, name='res2', res_owner_id = owner2.user_id, status = 'APPROVED', image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res2_gkskxx.jpg", by_admin_id = a2.user_id)
        res3 = models.Restaurant(restaurant_id = 3, name='res3', res_owner_id = owner3.user_id, status = 'APPROVED', image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870362/res1_inrqfg.jpg", by_admin_id = a1.user_id)

        db.session.add_all([res1, res2, res3])
        db.session.commit()

        d1 = models.Dish(dish_id=1,res_id = res1.restaurant_id, name='Cơm tấm', is_available = True, price = 10000, note ="a", image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_afjhjb.jpg")
        d2 = models.Dish(dish_id=2,res_id = res1.restaurant_id, name='Mì xào', is_available = True, price = 10000, note ="b", image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_3_qo5lms.jpg")
        d3 = models.Dish(dish_id=3,res_id = res2.restaurant_id, name='cơm tấm', is_available = True, price = 10000, note ="c", image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_1_lfohho.jpg")
        d4 = models.Dish(dish_id=4,res_id = res2.restaurant_id, name='mì xào', is_available = True, price = 10000, note ="d", image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_2_btt5x7.jpg")
        d5 = models.Dish(dish_id=5,res_id = res3.restaurant_id, name='trà sữa', is_available = True, price = 5000, note ="e", image = "https://res.cloudinary.com/dlwjqml4p/image/upload/v1756870282/download_4_uazlee.jpg")

        db.session.add_all([d1,d2,d3,d4,d5])
        db.session.commit()

    return app

app = create_app()

