from sqlalchemy import Column, Integer, String
from OrderFood import db, app


class User(db.Model):
    __tablename__ ='user'


if __name__ == '__main__':
    with app.app_context():
        db.create_all()