"""
Raw SQL data access layer. No ORM - every query here is hand-written SQL
via the stdlib sqlite3 module, using parameterized queries (? placeholders)
to avoid SQL injection.
"""
import sqlite3
from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row   # lets us access columns by name: row["email"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer'
        );

        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            rent_per_day REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'available'
        );

        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def create_user(name, email, password_hash, role="customer"):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, role),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

def get_all_vehicles(brand=None):
    conn = get_connection()
    if brand:
        rows = conn.execute(
            "SELECT * FROM vehicles WHERE brand = ? ORDER BY vehicle_id", (brand,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM vehicles ORDER BY vehicle_id").fetchall()
    conn.close()
    return rows


def get_vehicle_by_id(vehicle_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone()
    conn.close()
    return row


def get_distinct_brands():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT brand FROM vehicles ORDER BY brand").fetchall()
    conn.close()
    return [row["brand"] for row in rows]


def get_available_vehicles(limit=None):
    conn = get_connection()
    query = "SELECT * FROM vehicles WHERE status = 'available' ORDER BY vehicle_id"
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def add_vehicle(name, brand, rent_per_day, status="available"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO vehicles (name, brand, rent_per_day, status) VALUES (?, ?, ?, ?)",
        (name, brand, rent_per_day, status),
    )
    conn.commit()
    conn.close()


def update_vehicle(vehicle_id, name, brand, rent_per_day, status):
    conn = get_connection()
    conn.execute(
        "UPDATE vehicles SET name = ?, brand = ?, rent_per_day = ?, status = ? WHERE vehicle_id = ?",
        (name, brand, rent_per_day, status, vehicle_id),
    )
    conn.commit()
    conn.close()


def delete_vehicle(vehicle_id):
    conn = get_connection()
    conn.execute("DELETE FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
    conn.commit()
    conn.close()


def vehicle_has_bookings(vehicle_id):
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM bookings WHERE vehicle_id = ? LIMIT 1", (vehicle_id,)).fetchone()
    conn.close()
    return row is not None


def set_vehicle_status(vehicle_id, status):
    conn = get_connection()
    conn.execute("UPDATE vehicles SET status = ? WHERE vehicle_id = ?", (status, vehicle_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

def create_booking(user_id, vehicle_id, start_date, end_date, total_price, status="pending"):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO bookings (user_id, vehicle_id, start_date, end_date, total_price, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, vehicle_id, start_date, end_date, total_price, status),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_bookings_by_user(user_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT bookings.*, vehicles.name AS vehicle_name
           FROM bookings
           JOIN vehicles ON vehicles.vehicle_id = bookings.vehicle_id
           WHERE bookings.user_id = ?
           ORDER BY bookings.booking_id DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_bookings():
    conn = get_connection()
    rows = conn.execute(
        """SELECT bookings.*, vehicles.name AS vehicle_name, users.name AS customer_name
           FROM bookings
           JOIN vehicles ON vehicles.vehicle_id = bookings.vehicle_id
           JOIN users ON users.user_id = bookings.user_id
           ORDER BY bookings.booking_id DESC"""
    ).fetchall()
    conn.close()
    return rows


BOOKING_STATUSES = ("pending", "approved", "completed", "cancelled")


def get_booking_report():
    """Booking count and total value per status (every status listed, zero if none)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n, COALESCE(SUM(total_price), 0) AS value "
        "FROM bookings GROUP BY status"
    ).fetchall()
    conn.close()
    found = {r["status"]: (r["n"], r["value"]) for r in rows}
    return [
        {"status": st, "count": found.get(st, (0, 0))[0], "value": found.get(st, (0, 0))[1]}
        for st in BOOKING_STATUSES
    ]


def get_booking_by_id(booking_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    conn.close()
    return row


def set_booking_status(booking_id, status):
    conn = get_connection()
    conn.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", (status, booking_id))
    conn.commit()
    conn.close()


def approve_booking(booking_id):
    set_booking_status(booking_id, "approved")
