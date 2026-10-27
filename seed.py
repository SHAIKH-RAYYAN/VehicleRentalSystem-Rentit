"""
Run this once to create tables and populate the DB with sample data.

    python seed.py

Satisfies the "minimum 10 entries" requirement for Users, Vehicles, and Bookings.
Uses raw SQL (via db.py) - no ORM.
"""
import os
from datetime import date, timedelta

import config
import db
from models import User

VEHICLES = [
    ("Swift Dzire",   "Maruti",  1500, "available"),
    ("Honda City",    "Honda",   1800, "available"),
    ("Toyota Innova", "Toyota",  2800, "available"),
    ("Hyundai Creta", "Hyundai", 2500, "booked"),
    ("Royal Enfield Classic 350", "Royal Enfield", 700, "available"),
    ("Honda Activa",  "Honda",   400, "available"),
    ("Mahindra Bolero", "Mahindra", 2200, "maintenance"),
    ("Tata Ace",      "Tata",    1900, "available"),
    ("Force Traveller", "Force", 3200, "available"),
    ("KTM Duke 200",  "KTM",     900, "available"),
    ("Maruti Ertiga", "Maruti",  2100, "available"),
    ("Kia Seltos",    "Kia",     2600, "available"),
]

USERS = [
    ("Admin User",     "admin@rental.com",    "admin123", "admin"),
    ("Rayyan Shaikh",  "rayyan@example.com",  "pass123",  "customer"),
    ("Aditi Sharma",   "aditi@example.com",   "pass123",  "customer"),
    ("Rohan Verma",    "rohan@example.com",   "pass123",  "customer"),
    ("Sneha Patil",    "sneha@example.com",   "pass123",  "customer"),
    ("Karan Mehta",    "karan@example.com",   "pass123",  "customer"),
    ("Priya Nair",     "priya@example.com",   "pass123",  "customer"),
    ("Arjun Reddy",    "arjun@example.com",   "pass123",  "customer"),
    ("Neha Joshi",     "neha@example.com",    "pass123",  "customer"),
    ("Vikram Singh",   "vikram@example.com",  "pass123",  "customer"),
    ("Meera Iyer",     "meera@example.com",   "pass123",  "customer"),
]


def seed():
    # Start fresh
    if os.path.exists(config.DATABASE_PATH):
        os.remove(config.DATABASE_PATH)
    db.init_db()

    # --- Users ---
    user_ids = []
    for name, email, password, role in USERS:
        uid = db.create_user(name, email, User.hash_password(password), role=role)
        user_ids.append((uid, role))

    # --- Vehicles ---
    for name, brand, price, status in VEHICLES:
        db.add_vehicle(name, brand, price, status)
    vehicles = db.get_all_vehicles()

    # --- Bookings (10 across customers) ---
    customers = [uid for uid, role in user_ids if role == "customer"]
    booking_count = 0
    for i in range(10):
        user_id = customers[i % len(customers)]
        vehicle = vehicles[i % len(vehicles)]
        start = date.today() - timedelta(days=10 - i)
        end = start + timedelta(days=2 + (i % 4))
        days = (end - start).days
        total = days * vehicle["rent_per_day"]
        status = "approved" if i % 3 else "pending"

        db.create_booking(
            user_id=user_id,
            vehicle_id=vehicle["vehicle_id"],
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            total_price=total,
            status=status,
        )
        booking_count += 1

    print(f"Seeded: {len(user_ids)} users, {len(vehicles)} vehicles, {booking_count} bookings.")


if __name__ == "__main__":
    seed()
