

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from dotenv import load_dotenv
import cloudinary
from authlib.integrations.flask_client import OAuth

import os



load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

CLOUDINARY_CLOUD_NAME= os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY= os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET= os.getenv("CLOUDINARY_API_SECRET")

oauth = OAuth()
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-please-change-me")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:%s@localhost/orderfooddb?charset=utf8mb4' % quote('Admin@123')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(app)

    # Cấu hình Cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )

    # Google OAuth (OpenID Connect)
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    with app.app_context():
        from OrderFood import models  # noqa: F401
        db.create_all()  # Tạo tất cả bảng từ model

    return app

app = create_app()
