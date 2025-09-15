# OrderFood/services/google_service.py
from secrets import token_urlsafe

from flask import Blueprint, url_for, session, redirect, flash, request, current_app
from OrderFood import db, oauth
from OrderFood.models import User, Customer

google_auth_bp = Blueprint("google_auth", __name__)

def _role_to_str(r):
    return getattr(r, "value", r)

def _after_login_redirect():
    # ưu tiên ?next=..., fallback về trang chủ
    nxt = request.args.get("next") or session.pop("next", None)
    try:
        return redirect(nxt) if nxt else redirect(url_for("index"))
    except Exception:
        return redirect(url_for("index"))

@google_auth_bp.route("/login/google")
def login_google():
    # lưu next nếu có
    if request.args.get("next"):
        session["next"] = request.args.get("next")

    redirect_uri = url_for("google_auth.google_callback", _external=True)
    nonce = token_urlsafe(16)
    session["oidc_nonce"] = nonce
    return oauth.google.authorize_redirect(
        redirect_uri,
        nonce=nonce,
        prompt="consent",
    )

@google_auth_bp.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    nonce = session.pop("oidc_nonce", None)
    userinfo = oauth.google.parse_id_token(token, nonce=nonce)

    if not userinfo or "email" not in userinfo:
        flash("Không lấy được thông tin Google", "danger")
        return redirect(url_for("login"))

    email = userinfo["email"].lower()
    display_name = userinfo.get("name") or userinfo.get("given_name") or email.split("@")[0]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            name=display_name,
            avatar=userinfo.get("picture"),
            role="CUSTOMER",  # mặc định khách hàng
        )
        db.session.add(user)
        db.session.commit()
    else:
        if not user.name and display_name:
            user.name = display_name
            db.session.commit()

    # ======= NEW: tạo Customer nếu thiếu =======
    try:
        # chỉ tạo nếu user là CUSTOMER và chưa có profile
        role_str = (getattr(user.role, "value", user.role) or "").upper()
        if role_str == "CUSTOMER":
            if not Customer.query.filter_by(user_id=user.user_id).first():
                db.session.add(Customer(user_id=user.user_id))
                db.session.commit()
    except Exception as ex:
        current_app.logger.exception("Failed to ensure Customer profile: %s", ex)
        # không chặn login, nhưng có thể cảnh báo nếu bạn muốn

    # set session đăng nhập
    session["user_id"] = user.user_id
    session["user_email"] = user.email
    session["user_name"] = user.name or display_name or user.email
    session["role"] = (getattr(user.role, "value", user.role) or "").lower()

    flash("Đăng nhập bằng Google thành công!", "success")
    return _after_login_redirect()

