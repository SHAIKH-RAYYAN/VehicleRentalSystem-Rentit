# Demo walkthrough (~6 minutes)

1. **Start**: `bash run.sh` → browser opens. Mention: Flask app, raw SQLite, no ORM.
2. **Home / Vehicles / About / Contact**: navigation, brand filter on Vehicles.
3. **Register** a new user → **Login**. Explain hashed passwords + Flask-Login session.
4. **Book**: pick an available vehicle → choose dates → total = days × rent (server-side) → lands on Dashboard as `pending`; vehicle now shows `booked` on Vehicles.
5. **Logout** → try `/admin` → redirected to login (access control). Log in as a customer → `/admin` → 403.
6. **Admin login** (`admin@rental.com` / `admin123`) → Admin Dashboard.
   - Manage Vehicles: add, edit (inline), delete. Try deleting a vehicle with bookings → blocked with a message.
   - Manage Bookings: Approve the pending booking → Complete it → vehicle returns to available. Show Cancel.
7. **Back as customer**: Dashboard shows updated status.
8. **Show code**: `db.py` (raw parameterized SQL), `app.py` routes + `admin_required`, `models.py`.

## Likely viva questions
- *Why Flask?* Lightweight, server-rendered pages, easy to explain; Jinja2 templates for the UI.
- *Why no ORM?* To show actual SQL for the DB-connectivity requirement.
- *SQL injection?* All queries use `?` placeholders.
- *Weakness?* No booking-date overlap check, no CSRF, contact form is UI-only.
