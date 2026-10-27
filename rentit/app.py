from datetime import date, datetime
from functools import wraps

from urllib.parse import urlparse

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

import config
import db
from models import User

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.load(user_id)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()   # anonymous -> redirect to login
        if not current_user.is_admin():
            abort(403)                            # logged in but not admin
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    featured = db.get_available_vehicles(limit=4)
    return render_template("home.html", vehicles=featured)


@app.route("/vehicles")
def vehicles():
    q_brand = request.args.get("brand")
    all_vehicles = db.get_all_vehicles(brand=q_brand)
    brands = db.get_distinct_brands()
    return render_template("vehicles.html", vehicles=all_vehicles, brands=brands, selected_brand=q_brand)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if db.get_user_by_email(email):
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("register"))

        db.create_user(name, email, User.hash_password(password))
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.find_by_email(email)

        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            # only allow same-site relative redirects (prevents open redirect)
            if next_page and (urlparse(next_page).netloc or not next_page.startswith("/")):
                next_page = None
            if user.is_admin():
                return redirect(next_page or url_for("admin_dashboard"))
            return redirect(next_page or url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Customer dashboard (merged: profile + my bookings + entry point to booking)
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    bookings = db.get_bookings_by_user(current_user.user_id)
    return render_template("dashboard.html", bookings=bookings)


@app.route("/book/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def book(vehicle_id):
    vehicle = db.get_vehicle_by_id(vehicle_id)
    if vehicle is None:
        abort(404)

    if vehicle["status"] != "available":
        flash("This vehicle is not available right now.", "warning")
        return redirect(url_for("vehicles"))

    if request.method == "POST":
        try:
            start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            flash("Please enter valid dates.", "danger")
            return redirect(url_for("book", vehicle_id=vehicle_id))

        if start_date < date.today():
            flash("Start date cannot be in the past.", "danger")
            return redirect(url_for("book", vehicle_id=vehicle_id))

        if end_date <= start_date:
            flash("End date must be after start date.", "danger")
            return redirect(url_for("book", vehicle_id=vehicle_id))

        days = (end_date - start_date).days
        total_price = days * vehicle["rent_per_day"]

        db.create_booking(
            user_id=current_user.user_id,
            vehicle_id=vehicle["vehicle_id"],
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_price=total_price,
        )
        db.set_vehicle_status(vehicle["vehicle_id"], "booked")

        flash(f"Booking submitted. Total: ₹{total_price:.2f}", "success")
        return redirect(url_for("dashboard"))

    return render_template("book.html", vehicle=vehicle)


# ---------------------------------------------------------------------------
# Admin dashboard (manage vehicles + manage bookings, tabbed on one page)
# ---------------------------------------------------------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    all_vehicles = db.get_all_vehicles()
    status_filter = request.args.get("status")
    if status_filter not in db.BOOKING_STATUSES:
        status_filter = None
    all_bookings = db.get_all_bookings()
    shown = [b for b in all_bookings if status_filter in (None, b["status"])]
    return render_template(
        "admin_dashboard.html",
        vehicles=all_vehicles,
        bookings=shown,
        report=db.get_booking_report(),
        total_bookings=len(all_bookings),
        status_filter=status_filter,
    )


VALID_VEHICLE_STATUS = {"available", "booked", "maintenance"}


def _read_vehicle_form():
    """Validate admin vehicle form. Returns (data, error)."""
    name = request.form.get("name", "").strip()
    brand = request.form.get("brand", "").strip()
    status = request.form.get("status", "available")
    try:
        rent = float(request.form.get("rent_per_day", ""))
    except ValueError:
        return None, "Rent per day must be a number."
    if not name or not brand:
        return None, "Name and brand are required."
    if rent <= 0:
        return None, "Rent per day must be greater than zero."
    if status not in VALID_VEHICLE_STATUS:
        return None, "Invalid status."
    return dict(name=name, brand=brand, rent_per_day=rent, status=status), None


@app.route("/admin/vehicles/add", methods=["POST"])
@admin_required
def admin_add_vehicle():
    data, err = _read_vehicle_form()
    if err:
        flash(err, "danger")
        return redirect(url_for("admin_dashboard"))
    db.add_vehicle(**data)
    flash("Vehicle added.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/vehicles/<int:vehicle_id>/update", methods=["POST"])
@admin_required
def admin_update_vehicle(vehicle_id):
    if db.get_vehicle_by_id(vehicle_id) is None:
        abort(404)
    data, err = _read_vehicle_form()
    if err:
        flash(err, "danger")
        return redirect(url_for("admin_dashboard"))
    db.update_vehicle(vehicle_id, **data)
    flash("Vehicle updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/vehicles/<int:vehicle_id>/delete", methods=["POST"])
@admin_required
def admin_delete_vehicle(vehicle_id):
    if db.get_vehicle_by_id(vehicle_id) is None:
        abort(404)
    if db.vehicle_has_bookings(vehicle_id):
        flash("Can't delete a vehicle that has booking history. Set it to Maintenance instead.", "warning")
    else:
        db.delete_vehicle(vehicle_id)
        flash("Vehicle removed.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/bookings/<int:booking_id>/approve", methods=["POST"])
@admin_required
def admin_approve_booking(booking_id):
    booking = db.get_booking_by_id(booking_id)
    if booking is None:
        abort(404)
    if booking["status"] != "pending":
        flash("Only pending bookings can be approved.", "warning")
    else:
        db.set_booking_status(booking_id, "approved")
        flash("Booking approved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/bookings/<int:booking_id>/cancel", methods=["POST"])
@admin_required
def admin_cancel_booking(booking_id):
    booking = db.get_booking_by_id(booking_id)
    if booking is None:
        abort(404)
    if booking["status"] not in ("pending", "approved"):
        flash("This booking can't be cancelled.", "warning")
    else:
        db.set_booking_status(booking_id, "cancelled")
        db.set_vehicle_status(booking["vehicle_id"], "available")   # free the vehicle
        flash("Booking cancelled and vehicle released.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/bookings/<int:booking_id>/complete", methods=["POST"])
@admin_required
def admin_complete_booking(booking_id):
    booking = db.get_booking_by_id(booking_id)
    if booking is None:
        abort(404)
    if booking["status"] != "approved":
        flash("Only approved bookings can be completed.", "warning")
    else:
        db.set_booking_status(booking_id, "completed")
        db.set_vehicle_status(booking["vehicle_id"], "available")   # vehicle returned
        flash("Booking completed; vehicle is available again.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    import os
    db.init_db()
    # Defaults suit local use. In GitHub Codespaces the devcontainer sets
    # FLASK_HOST=0.0.0.0 so the forwarded port can reach the server.
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )
