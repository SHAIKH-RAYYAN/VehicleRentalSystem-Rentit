from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

import db


class User(UserMixin):
    """
    Thin wrapper around a sqlite3.Row from the users table so Flask-Login
    can work with it. No ORM - this just adapts a raw SQL row to the
    interface Flask-Login expects (get_id, is_authenticated, etc. via UserMixin).
    """

    def __init__(self, row):
        self.user_id = row["user_id"]
        self.name = row["name"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.role = row["role"]

    def get_id(self):
        return str(self.user_id)

    def is_admin(self):
        return self.role == "admin"

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    @staticmethod
    def load(user_id):
        row = db.get_user_by_id(user_id)
        return User(row) if row else None

    @staticmethod
    def find_by_email(email):
        row = db.get_user_by_email(email)
        return User(row) if row else None
