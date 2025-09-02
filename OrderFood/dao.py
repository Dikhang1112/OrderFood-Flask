
from sqlalchemy.exc import IntegrityError
from OrderFood.models import db, User

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
