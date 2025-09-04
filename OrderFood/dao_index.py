from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from OrderFood.models import db, User, Dish, RestaurantOwner, Restaurant

ENUM_UPPERCASE = True  # True nếu DB dùng 'CUSTOMER','RESTAURANT_OWNER'

def _norm_role(role: str) -> str:
    r = (role or "customer").strip().lower()
    return "CUSTOMER" if (ENUM_UPPERCASE and r == "customer") else \
           "RESTAURANT_OWNER" if ENUM_UPPERCASE else r

def get_user_by_email(email: str):
    return User.query.filter(User.email == email).first()

def create_user(name, email, phone, hashed_password, role: str):
    u = User(name=name, email=email, phone=phone,
             password=hashed_password, role=_norm_role(role))
    try:
        db.session.add(u)
        db.session.commit()
        return u
    except IntegrityError:
        db.session.rollback()
        return None

ENUM_UPPERCASE = True  # True nếu DB dùng 'CUSTOMER','RESTAURANT_OWNER'

def _norm_role(role: str) -> str:
    r = (role or "customer").strip().lower()
    return "CUSTOMER" if (ENUM_UPPERCASE and r == "customer") else \
           "RESTAURANT_OWNER" if ENUM_UPPERCASE else r

def get_user_by_email(email: str):
    return User.query.filter(User.email == email).first()

def create_user(name, email, phone, hashed_password, role: str):
    u = User(name=name, email=email, phone=phone, password=hashed_password, role=role)
    db.session.add(u)
    db.session.commit()
    return u

def load_menu_owner(owner_id: int):
    owner = RestaurantOwner.query.get(owner_id)
    if not owner or not owner.restaurant:
        return []  # chưa có nhà hàng

    restaurant_id = owner.restaurant.restaurant_id
    dishes = Dish.query.filter_by(res_id=restaurant_id).all()
    return dishes

def restaurant_detail(restaurant_id: int):
    return Dish.query.filter_by(res_id=restaurant_id).all()


def get_restaurant_by_id(restaurant_id: int):
    return Restaurant.query.get(restaurant_id)

def get_restaurants_by_name(name: str = None):
    if not name:
        return []
    name = name.strip()
    return Restaurant.query.filter(func.lower(Restaurant.name).like(f"%{name.lower()}%")).all()
    # return Restaurant.query.filter(func.lower(Restaurant.name).like(f"%{name.lower()}%"))




def get_restaurants_by_dishes_name(dishes_name: str = None):
    dishes = Dish.query.options(joinedload(Dish.restaurant)).filter(
        func.lower(Dish.name).like(f"%{dishes_name.lower()}%")).all()
    restaurants = list({dish.restaurant.restaurant_id: dish.restaurant for dish in dishes if dish.restaurant}.values())
    return restaurants

