# dao.py
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from OrderFood.models import db, User, Customer, RestaurantOwner, Restaurant, Dish, Category, Cart, CartItem, StatusCart

ENUM_UPPERCASE = True  # True nếu DB là 'CUSTOMER','RESTAURANT_OWNER'

# --- User & Owner ---
def _norm_role(role: str) -> str:
    r = (role or "customer").strip().lower()
    return "CUSTOMER" if (ENUM_UPPERCASE and r == "customer") else \
           "RESTAURANT_OWNER" if ENUM_UPPERCASE else r

def get_user_by_email(email: str):
    return User.query.filter(User.email == email).first()

def get_user_by_id(user_id):
    return User.query.get(user_id)

def create_user(name, email, phone, hashed_password, role: str):
    u = User(name=name, email=email, phone=phone, password=hashed_password, role=_norm_role(role))
    try:
        db.session.add(u)
        db.session.commit()
        if role.upper() == "RESTAURANT_OWNER":
            owner = RestaurantOwner(user_id=u.user_id, tax=None)
            db.session.add(owner)
            db.session.commit()
        return u
    except IntegrityError:
        db.session.rollback()
        return None

def load_menu_owner(owner_id: int):
    owner = RestaurantOwner.query.get(owner_id)
    if not owner or not owner.restaurant:
        return []
    restaurant_id = owner.restaurant.restaurant_id
    return Dish.query.filter_by(res_id=restaurant_id).all()

def get_categories_by_owner_id(owner_id: int):
    restaurant = Restaurant.query.filter_by(res_owner_id=owner_id).first()
    if not restaurant:
        return []
    return Category.query.filter_by(res_id=restaurant.restaurant_id).all()

def get_dishes_by_name(owner_id, keyword: str):
    dishes = load_menu_owner(owner_id)
    if not keyword:
        return []
    keyword = keyword.strip().lower()
    return [dish for dish in dishes if keyword in (dish.name or "").lower()]

# --- Restaurant ---
def get_restaurant_by_id(restaurant_id: int):
    return Restaurant.query.get(restaurant_id)

def restaurant_detail(restaurant_id: int):
    return Dish.query.filter_by(res_id=restaurant_id).all()

def get_restaurants_by_name(name: str = None):
    if not name:
        return []
    name = name.strip()
    restaurants = Restaurant.query.filter(func.lower(Restaurant.name).like(f"%{name.lower()}%")).all()
    for r in restaurants:
        r.stars = get_star_display(r.rating_point or 0)
    return restaurants

def get_restaurants_by_dishes_name(dishes_name: str = None):
    if not dishes_name:
        return []
    dishes = Dish.query.options(joinedload(Dish.restaurant)).filter(
        func.lower(Dish.name).like(f"%{dishes_name.strip().lower()}%")
    ).all()
    restaurants = list({dish.restaurant.restaurant_id: dish.restaurant for dish in dishes if dish.restaurant}.values())
    for r in restaurants:
        r.stars = get_star_display(r.rating_point or 0)
    return restaurants

def get_all_restaurants_ordered_by_rating(descending=True):
    if descending:
        return Restaurant.query.order_by(Restaurant.rating.desc()).all()
    return Restaurant.query.order_by(Restaurant.rating.asc()).all()

# --- Rating / UI ---
def get_star_display(rating: float):
    if not rating:
        rating = 0
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    empty = 5 - full - half
    return {"full": full, "half": half, "empty": empty}

# --- Cart ---
def get_active_cart(user_id, restaurant_id):
    return Cart.query.filter_by(cus_id=user_id, res_id=restaurant_id, status=StatusCart.ACTIVE).first()

def add_cart_item(cart, dish_id, quantity=1, note=""):
    cart_item = CartItem.query.filter_by(cart_id=cart.cart_id, dish_id=dish_id).first()
    if cart_item:
        cart_item.quantity += quantity
        cart_item.note = note
    else:
        cart_item = CartItem(cart_id=cart.cart_id, dish_id=dish_id, quantity=quantity, note=note)
        db.session.add(cart_item)
    db.session.commit()
    return cart_item

def count_cart_items(cart):
    if not cart or not cart.items:
        return 0
    return sum(item.quantity for item in cart.items)
