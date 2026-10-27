import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-this")
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "vehicle_rental.db"))
