import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config; config.DATABASE_PATH = "/tmp/test_rentit.db"
import db; db.DATABASE_PATH = config.DATABASE_PATH
import seed; seed.config.DATABASE_PATH = config.DATABASE_PATH
seed.seed()
import app as A
A.app.config["TESTING"]=True
def client(): return A.app.test_client()
ok=0
def chk(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ")+name); ok += (not cond)
c=client()
for u in ["/","/vehicles","/vehicles?brand=Honda","/about","/contact","/login","/register"]:
    chk("GET "+u, c.get(u).status_code==200)
chk("anon /dashboard redirect", c.get("/dashboard").status_code==302)
r=c.get("/admin"); chk("anon /admin redirects to login", r.status_code==302 and "/login" in r.location)
chk("anon POST admin add redirects", c.post("/admin/vehicles/add",data={}).status_code==302)
# customer
r=c.post("/login",data={"email":"rayyan@example.com","password":"pass123"}); chk("cust login->dashboard", r.status_code==302 and "/dashboard" in r.location)
chk("dashboard", c.get("/dashboard").status_code==200)
chk("cust /admin 403", c.get("/admin").status_code==403)
chk("cust admin add 403", c.post("/admin/vehicles/add",data={"name":"x","brand":"y","rent_per_day":"5"}).status_code==403)
chk("cust approve 403", c.post("/admin/bookings/1/approve").status_code==403)
av=[v for v in db.get_all_vehicles() if v["status"]=="available"][0]; vid=av["vehicle_id"]
from datetime import date, timedelta
t=date.today()
chk("book GET", c.get(f"/book/{vid}").status_code==200)
r=c.post(f"/book/{vid}",data={"start_date":"garbage","end_date":"x"}); chk("bad date no 500", r.status_code==302)
r=c.post(f"/book/{vid}",data={"start_date":(t-timedelta(days=3)).isoformat(),"end_date":t.isoformat()}); chk("past date rejected", db.get_vehicle_by_id(vid)["status"]=="available")
r=c.post(f"/book/{vid}",data={"start_date":t.isoformat(),"end_date":t.isoformat()}); chk("end<=start rejected", db.get_vehicle_by_id(vid)["status"]=="available")
r=c.post(f"/book/{vid}",data={"start_date":t.isoformat(),"end_date":(t+timedelta(days=3)).isoformat()}); 
chk("booking created", r.status_code==302)
chk("vehicle now booked", db.get_vehicle_by_id(vid)["status"]=="booked")
bk=db.get_bookings_by_user(db.get_user_by_email("rayyan@example.com")["user_id"])[0]
chk("price server-side", bk["total_price"]==3*av["rent_per_day"] and bk["status"]=="pending")
chk("rebook blocked", c.post(f"/book/{vid}",data={"start_date":t.isoformat(),"end_date":(t+timedelta(days=2)).isoformat()}).status_code==302 and len(db.get_bookings_by_user(bk["user_id"]))==len([1 for _ in db.get_bookings_by_user(bk["user_id"])]))
c.get("/logout")
# open redirect
r=c.post("/login?next=https://evil.com",data={"email":"rayyan@example.com","password":"pass123"}); chk("open redirect blocked", "evil" not in r.location)
c.get("/logout")
# admin
r=c.post("/login",data={"email":"admin@rental.com","password":"admin123"}); chk("admin login->/admin", "/admin" in r.location)
chk("admin page", c.get("/admin").status_code==200)
n=len(db.get_all_vehicles())
chk("add vehicle", c.post("/admin/vehicles/add",data={"name":"Test Car","brand":"Tata","rent_per_day":"999","status":"available"}).status_code==302 and len(db.get_all_vehicles())==n+1)
c.post("/admin/vehicles/add",data={"name":"","brand":"y","rent_per_day":"5"}); chk("empty name rejected", len(db.get_all_vehicles())==n+1)
c.post("/admin/vehicles/add",data={"name":"a","brand":"y","rent_per_day":"abc"}); chk("non-numeric rent rejected (no 500)", len(db.get_all_vehicles())==n+1)
c.post("/admin/vehicles/add",data={"name":"a","brand":"y","rent_per_day":"-5"}); chk("negative rent rejected", len(db.get_all_vehicles())==n+1)
new=[v for v in db.get_all_vehicles() if v["name"]=="Test Car"][0]["vehicle_id"]
c.post(f"/admin/vehicles/{new}/update",data={"name":"Test Car 2","brand":"Tata","rent_per_day":"1111","status":"maintenance"})
v=db.get_vehicle_by_id(new); chk("update vehicle", v["name"]=="Test Car 2" and v["rent_per_day"]==1111 and v["status"]=="maintenance")
chk("update 404", c.post("/admin/vehicles/9999/update",data={"name":"a","brand":"b","rent_per_day":"1","status":"available"}).status_code==404)
c.post(f"/admin/vehicles/{new}/delete"); chk("delete clean vehicle", db.get_vehicle_by_id(new) is None)
c.post(f"/admin/vehicles/{vid}/delete"); chk("delete vehicle w/ bookings blocked (no 500)", db.get_vehicle_by_id(vid) is not None)
c.post(f"/admin/bookings/{bk['booking_id']}/approve"); chk("approve", db.get_booking_by_id(bk["booking_id"])["status"]=="approved")
c.post(f"/admin/bookings/{bk['booking_id']}/approve"); chk("re-approve harmless", db.get_booking_by_id(bk["booking_id"])["status"]=="approved")
c.post(f"/admin/bookings/{bk['booking_id']}/complete"); chk("complete frees vehicle", db.get_booking_by_id(bk["booking_id"])["status"]=="completed" and db.get_vehicle_by_id(vid)["status"]=="available")
r=c.post(f"/book/{vid}",data={"start_date":t.isoformat(),"end_date":(t+timedelta(days=1)).isoformat()}); chk("admin may book? (info)", True)
chk("approve 404", c.post("/admin/bookings/9999/approve").status_code==404)
page=c.get("/admin").get_data(as_text=True); chk("admin page renders statuses", "badge-completed" in page)
rep=db.get_booking_report()
chk("report lists all 4 statuses", [r["status"] for r in rep]==["pending","approved","completed","cancelled"])
chk("report counts add up", sum(r["count"] for r in rep)==len(db.get_all_bookings()))
pg=c.get("/admin?status=pending").get_data(as_text=True)
chk("filter pending only", "badge-approved" not in pg.split('id="bookingsTab"')[1].split("<tbody>")[1].split("</tbody>")[0])
chk("bad status filter ignored", c.get("/admin?status=zzz").status_code==200)
chk("report tab renders", 'id="reportTab"' in c.get("/admin").get_data(as_text=True))
print("FAILURES:", ok); sys.exit(1 if ok else 0)
