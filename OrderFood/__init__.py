
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-please-change-me")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:%s@localhost/orderfoobdb?charset=utf8mb4' %quote('Admin@123')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(app)
    with app.app_context():
        from OrderFood import models  # noqa: F401

    return app

app = create_app()

