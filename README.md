# RentIt — Vehicle Rental System (100%)

Flask + raw SQLite (no ORM) + Jinja2 + Bootstrap 5. Server-rendered web pages, role-based access (customer / admin).

## Progress

| Milestone | Scope | Status |
|-----------|-------|--------|
| 30% | Home, About, Contact, Register, Login + DB connectivity | Done |
| 75% | Browse vehicles, customer dashboard, booking flow | Done |
| 100% | Admin panel: vehicle CRUD, booking approve/complete/cancel, access control | Done |

## Run (one command)

```bash
bash run.sh
```

Creates `.venv`, installs requirements, seeds the DB on first run, opens the browser at http://127.0.0.1:5000.

Manual: `pip install -r requirements.txt && python seed.py && python app.py`

## Run in GitHub Codespaces

1. Push this folder to a GitHub repo, then **Code → Codespaces → Create codespace on main**.
2. Wait for the setup to finish (it installs requirements and seeds the database automatically).
3. In the terminal run: `python app.py`
4. Click the **Open in Browser** pop-up (or the **Ports** tab → port 5000). Log in with the credentials below.

The database file is created inside the codespace; it is not committed (`*.db` is git-ignored). To reset the data: `python seed.py`.

## Logins (seed data)

- Admin: `admin@rental.com` / `admin123`
- Customer: `rayyan@example.com` / `pass123` (9 more customers, same password)

## Database (raw SQL in `db.py`, parameterized queries)

- **users** — user_id, name, email, password_hash, role
- **vehicles** — vehicle_id, name, brand, rent_per_day, status (available / booked / maintenance)
- **bookings** — booking_id, user_id (FK), vehicle_id (FK), start_date, end_date, total_price, status (pending / approved / completed / cancelled)

Seed: 11 users, 12 vehicles, 10 bookings.

## Pages (9)

Public: Home, Vehicles (brand filter), About, Contact · Auth: Login, Register · Customer: Dashboard, Book Vehicle · Admin: Admin Dashboard (Manage Vehicles / Manage Bookings / Booking Report)

## Booking Report

Admin → Booking Report tab: count, share and total value per status (pending, approved, completed, cancelled). Click a status card (or use the filter buttons on Manage Bookings) to list only those bookings. There is no "processing" status; "approved" is the in-progress state.

## Booking lifecycle

`pending` → admin **Approve** → `approved` → admin **Complete** → `completed` (vehicle back to available).
Admin **Cancel** from pending/approved → `cancelled` (vehicle released).
Price is computed server-side: `days × rent_per_day`.

## Security notes

- Passwords hashed (Werkzeug); SQL parameterized; `next=` redirects restricted to same-site paths.
- `/admin/*`: anonymous → redirected to login, customer → 403.
- Vehicles with booking history can't be deleted (set to Maintenance instead).
- Set `SECRET_KEY` env var for anything beyond a demo. Logout is a GET link and there is no CSRF protection — acceptable for a college demo, not for production.

## Known limitations (be ready to state these)

- No date-overlap check: a vehicle is simply marked `booked` once someone books it.
- Contact form is UI-only (doesn't store or send).
- No payments, no feedback table, no deployment — out of scope.

## Tests

`python tests/test_rentit.py` — 46 route/access/CRUD checks against a temp database.

**Never zip or commit `.venv` or `*.db`** (they're in `.gitignore`).
