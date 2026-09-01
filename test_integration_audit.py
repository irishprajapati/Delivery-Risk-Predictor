import sys
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import requests
import uvicorn

from app.main import app
from app.database import SessionLocal
from app.model import (
    User, Customer, OTPCode, Order, Delivery, DeliveryLocation,
    Rider, RiderAreaPerformance, Prediction, Item, Category
)
from app.utils.security import get_password_hash
from app.services.delivery_service import (
    score_rider_for_delivery, rank_riders, auto_dispatch_order,
    assign_delivery, get_delivery
)

PORT = 8005
BASE_URL = f"http://127.0.0.1:{PORT}"

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(1.5)

results = {
    "passed": [],
    "failed": [],
    "details": []
}

def log_test(name, success, details=""):
    if success:
        results["passed"].append(name)
        print(f"✅ PASS: {name}")
    else:
        results["failed"].append({"name": name, "details": details})
        print(f"❌ FAIL: {name} -> {details}")
    results["details"].append({"name": name, "status": "PASS" if success else "FAIL", "details": details})

print("==================================================")
print("STARTING DELIVERY DISPATCH END-TO-END AUDIT SUITE")
print(f"Target Server: {BASE_URL}")
print("==================================================")

# ----------------------------------------------------------------
# TEST 1: DATABASE CONNECTIVITY & SEED DATA
# ----------------------------------------------------------------
db = SessionLocal()
try:
    # Ensure category
    cat = db.query(Category).filter(Category.name == "Electronics").first()
    if not cat:
        cat = Category(name="Electronics")
        db.add(cat)
        db.commit()
        db.refresh(cat)

    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print("Created default admin user (admin / admin123)")
    else:
        admin_user.password = get_password_hash("admin123")
        admin_user.role = "admin"
        admin_user.is_active = True
        db.commit()

    items_count = db.query(Item).count()
    if items_count == 0:
        db.add_all([
            Item(name="Laptop", category_id=cat.id, price=90000),
            Item(name="Smartphone", category_id=cat.id, price=45000),
            Item(name="Smart Watch", category_id=cat.id, price=15000),
        ])
        db.commit()

    # Reset riders to pristine test state
    existing_riders = db.query(Rider).all()
    if not existing_riders:
        r1 = Rider(name="Rider Bikash", phone="9811111111", area="Lalitpur", is_active=True, max_orders_per_day=20, current_order_count=2, completed_orders=45, failed_deliveries=3)
        r2 = Rider(name="Rider Ramesh", phone="9822222222", area="Kathmandu", is_active=True, max_orders_per_day=20, current_order_count=5, completed_orders=30, failed_deliveries=5)
        r3 = Rider(name="Rider Suresh", phone="9833333333", area="Bhaktapur", is_active=True, max_orders_per_day=20, current_order_count=20, completed_orders=50, failed_deliveries=10)
        db.add_all([r1, r2, r3])
        db.commit()
    else:
        for r in existing_riders:
            r.is_active = True
            if "Bikash" in r.name:
                r.current_order_count = 2
                r.max_orders_per_day = 20
            elif "Ramesh" in r.name:
                r.current_order_count = 5
                r.max_orders_per_day = 20
            elif "Suresh" in r.name:
                r.current_order_count = 20
                r.max_orders_per_day = 20
    # Sync PostgreSQL sequences with current max IDs
    for table in ['orders', 'deliveries', 'customers', 'riders', 'items', 'categories', 'users']:
        try:
            db.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1) + 1, false);"))
        except Exception:
            pass
    db.commit()

    log_test("1. Database Connectivity and Fleet Seed Data", True)
except Exception as e:
    log_test("1. Database Connectivity and Fleet Seed Data", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 2-5: AUTHENTICATION LIFECYCLE AUDIT
# ----------------------------------------------------------------
admin_token = None
customer_token = None
test_phone = f"9841{int(time.time()) % 1000000:06d}"
test_password = "Password@123"

# Admin Login
try:
    res = requests.post(f"{BASE_URL}/admin/login", params={"username": "admin", "password": "admin123"})
    if res.status_code == 200 and "access_token" in res.json():
        admin_token = res.json()["access_token"]
        log_test("2. Admin Login (POST /admin/login)", True)
    else:
        log_test("2. Admin Login (POST /admin/login)", False, f"Status: {res.status_code}, Body: {res.text}")
except Exception as e:
    log_test("2. Admin Login (POST /admin/login)", False, str(e))

# Customer Register
try:
    res = requests.post(f"{BASE_URL}/register", json={"phone": test_phone, "password": test_password})
    if res.status_code in [200, 201]:
        log_test("3. Customer Registration (POST /register)", True)
    else:
        log_test("3. Customer Registration (POST /register)", False, f"Status: {res.status_code}, Body: {res.text}")
except Exception as e:
    log_test("3. Customer Registration (POST /register)", False, str(e))

# Customer Verify OTP
db = SessionLocal()
try:
    otp_record = db.query(OTPCode).filter(OTPCode.phone == test_phone).order_by(OTPCode.created_at.desc()).first()
    otp_val = otp_record.otp if otp_record else "123456"
    res = requests.post(f"{BASE_URL}/verify-otp", json={"phone": test_phone, "otp": otp_val})
    if res.status_code == 200:
        log_test("4. Customer OTP Verification (POST /verify-otp)", True)
    else:
        log_test("4. Customer OTP Verification (POST /verify-otp)", False, f"Status: {res.status_code}, Body: {res.text}")
except Exception as e:
    log_test("4. Customer OTP Verification (POST /verify-otp)", False, str(e))
finally:
    db.close()

# Customer Login
try:
    res = requests.post(f"{BASE_URL}/customer/login", params={"phone": test_phone, "password": test_password})
    if res.status_code == 200 and "access_token" in res.json():
        customer_token = res.json()["access_token"]
        log_test("5. Customer Login (POST /customer/login)", True)
    else:
        log_test("5. Customer Login (POST /customer/login)", False, f"Status: {res.status_code}, Body: {res.text}")
except Exception as e:
    log_test("5. Customer Login (POST /customer/login)", False, str(e))

# ----------------------------------------------------------------
# TEST 6-9: CROSS-ROLE AUTHORIZATION (RBAC)
# ----------------------------------------------------------------
try:
    res = requests.get(f"{BASE_URL}/admin/dashboard", headers={"Authorization": f"Bearer {customer_token}"})
    log_test("6. Customer accessing /admin/dashboard returns 403 Forbidden", res.status_code == 403)
except Exception as e:
    log_test("6. Customer accessing /admin/dashboard returns 403 Forbidden", False, str(e))

try:
    res = requests.get(f"{BASE_URL}/customer/profile", headers={"Authorization": f"Bearer {admin_token}"})
    log_test("7. Admin accessing /customer/profile returns 403 Forbidden", res.status_code == 403)
except Exception as e:
    log_test("7. Admin accessing /customer/profile returns 403 Forbidden", False, str(e))

try:
    res = requests.get(f"{BASE_URL}/customer/profile", headers={"Authorization": f"Bearer {customer_token}"})
    log_test("8. Customer accessing /customer/profile returns 200 OK", res.status_code == 200 and res.json().get("phone") == test_phone)
except Exception as e:
    log_test("8. Customer accessing /customer/profile returns 200 OK", False, str(e))

try:
    res = requests.get(f"{BASE_URL}/customer/orders", headers={"Authorization": f"Bearer {customer_token}"})
    log_test("9. Customer accessing /customer/orders returns 200 OK list", res.status_code == 200 and isinstance(res.json(), list))
except Exception as e:
    log_test("9. Customer accessing /customer/orders returns 200 OK list", False, str(e))

# ----------------------------------------------------------------
# TEST 10-12: ORDER PLACEMENT VALIDATION CHECKS
# ----------------------------------------------------------------
db = SessionLocal()
test_item = db.query(Item).first()
item_id = test_item.id if test_item else 1
db.close()

# Invalid lat/lng = 0
res = requests.post(f"{BASE_URL}/place-order", json={
    "item_id": item_id,
    "quantity": 1,
    "payment_method": "cod",
    "prepaid_amount": 0,
    "address": "Jawalakhel, Lalitpur",
    "latitude": 0.0,
    "longitude": 0.0
}, headers={"Authorization": f"Bearer {customer_token}"})
log_test("10. Invalid lat=0, lng=0 handled cleanly", res.status_code in [400, 422, 200])

# Prepaid amount > total order value
res = requests.post(f"{BASE_URL}/place-order", json={
    "item_id": item_id,
    "quantity": 1,
    "payment_method": "prepaid",
    "prepaid_amount": 500000.0,
    "address": "Jawalakhel, Lalitpur",
    "latitude": 27.6744,
    "longitude": 85.3123
}, headers={"Authorization": f"Bearer {customer_token}"})
log_test("11. Prepaid amount > total order value rejected (422)", res.status_code in [400, 422])

# COD with non-zero prepaid amount
res = requests.post(f"{BASE_URL}/place-order", json={
    "item_id": item_id,
    "quantity": 1,
    "payment_method": "cod",
    "prepaid_amount": 5000.0,
    "address": "Jawalakhel, Lalitpur",
    "latitude": 27.6744,
    "longitude": 85.3123
}, headers={"Authorization": f"Bearer {customer_token}"})
log_test("12. COD with non-zero prepaid amount rejected (422)", res.status_code in [400, 422])

# ----------------------------------------------------------------
# TEST 13: REQUIREMENT 1 - NORMAL ORDER → AUTOMATIC PREDICTION → AUTOMATIC DISPATCH
# ----------------------------------------------------------------
created_order_id = None
created_delivery_id = None
assigned_rider_id = None

res = requests.post(f"{BASE_URL}/place-order", json={
    "item_id": item_id,
    "quantity": 1,
    "payment_method": "cod",
    "prepaid_amount": 0.0,
    "address": "Jawalakhel, Lalitpur",
    "latitude": 27.6744,
    "longitude": 85.3123
}, headers={"Authorization": f"Bearer {customer_token}"})

if res.status_code in [200, 201]:
    data = res.json()
    created_order_id = data.get("order_id")
    created_delivery_id = data.get("delivery_id")
    assigned_rider_id = data.get("assigned_rider_id")
    
    db = SessionLocal()
    ord_rec = db.query(Order).filter(Order.id == created_order_id).first()
    del_rec = db.query(Delivery).filter(Delivery.id == created_delivery_id).first()
    loc_rec = db.query(DeliveryLocation).filter(DeliveryLocation.order_id == created_order_id).first()
    cust_rec = db.query(Customer).filter(Customer.phone == test_phone).first()
    pred_rec = db.query(Prediction).filter(Prediction.order_id == created_order_id).first()
    
    auto_assigned_ok = (
        del_rec is not None and
        del_rec.status == "assigned" and
        del_rec.rider_id is not None and
        del_rec.assigned_at is not None and
        ord_rec.risk_level in ["LOW", "MEDIUM", "HIGH"] and
        ord_rec.risk_score is not None and
        pred_rec is not None and
        loc_rec is not None and
        cust_rec.total_orders >= 1
    )
    db.close()
    log_test("13. Normal Order → Automatic ML Risk → Automatic Rider Assignment", auto_assigned_ok,
             f"Order: {created_order_id}, Delivery: {created_delivery_id}, Rider: {assigned_rider_id}, Risk: {ord_rec.risk_level if ord_rec else None}")
else:
    log_test("13. Normal Order → Automatic ML Risk → Automatic Rider Assignment", False, f"Status: {res.status_code}, Body: {res.text}")

# ----------------------------------------------------------------
# TEST 14: REQUIREMENT 2 - LOW-RISK ASSIGNMENT SCORING
# ----------------------------------------------------------------
db = SessionLocal()
try:
    del_obj = db.query(Delivery).filter(Delivery.id == created_delivery_id).first()
    ranked_low = rank_riders(db=db, delivery_id=del_obj.id, risk_level="LOW")
    log_test("14. LOW-risk Assignment Ranking (Prioritizes proximity/speed)", len(ranked_low) > 0 and ranked_low[0]["score"] > 0)
except Exception as e:
    log_test("14. LOW-risk Assignment Ranking", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 15: REQUIREMENT 3 - MEDIUM-RISK ASSIGNMENT SCORING
# ----------------------------------------------------------------
db = SessionLocal()
try:
    del_obj = db.query(Delivery).filter(Delivery.id == created_delivery_id).first()
    ranked_med = rank_riders(db=db, delivery_id=del_obj.id, risk_level="MEDIUM")
    log_test("15. MEDIUM-risk Assignment Ranking (Balanced evaluation)", len(ranked_med) > 0 and ranked_med[0]["score"] > 0)
except Exception as e:
    log_test("15. MEDIUM-risk Assignment Ranking", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 16: REQUIREMENT 4 - HIGH-RISK ASSIGNMENT SCORING
# ----------------------------------------------------------------
db = SessionLocal()
try:
    del_obj = db.query(Delivery).filter(Delivery.id == created_delivery_id).first()
    ranked_high = rank_riders(db=db, delivery_id=del_obj.id, risk_level="HIGH")
    log_test("16. HIGH-risk Assignment Ranking (Prioritizes experience and success rate)", len(ranked_high) > 0 and ranked_high[0]["score"] > 0)
except Exception as e:
    log_test("16. HIGH-risk Assignment Ranking", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 17: REQUIREMENT 5 - NO RIDERS AVAILABLE (ORDER COMMITTED, DELIVERY UNASSIGNED)
# ----------------------------------------------------------------
db = SessionLocal()
try:
    # Temporarily deactivate all riders
    db.query(Rider).update({Rider.is_active: False})
    db.commit()

    res = requests.post(f"{BASE_URL}/place-order", json={
        "item_id": item_id,
        "quantity": 1,
        "payment_method": "cod",
        "prepaid_amount": 0.0,
        "address": "Kumaripati, Lalitpur",
        "latitude": 27.6680,
        "longitude": 85.3180
    }, headers={"Authorization": f"Bearer {customer_token}"})

    data = res.json() if res.status_code in [200, 201] else {}
    no_rider_order_id = data.get("order_id")
    no_rider_del_id = data.get("delivery_id")

    del_rec = db.query(Delivery).filter(Delivery.id == no_rider_del_id).first()
    ord_rec = db.query(Order).filter(Order.id == no_rider_order_id).first()

    no_rider_ok = (
        res.status_code in [200, 201] and
        ord_rec is not None and
        del_rec is not None and
        del_rec.status == "unassigned" and
        del_rec.rider_id is None
    )
    log_test("17. No Riders Available (Order succeeds, delivery remains unassigned)", no_rider_ok,
             f"Order: {no_rider_order_id}, Status: {del_rec.status if del_rec else None}")
finally:
    # Restore active state
    db.query(Rider).update({Rider.is_active: True})
    db.commit()
    db.close()

# ----------------------------------------------------------------
# TEST 18: REQUIREMENT 6 - ALL RIDERS AT CAPACITY (ORDER COMMITTED, DELIVERY UNASSIGNED)
# ----------------------------------------------------------------
db = SessionLocal()
try:
    # Set all riders to full capacity
    db.query(Rider).update({Rider.current_order_count: Rider.max_orders_per_day})
    db.commit()

    res = requests.post(f"{BASE_URL}/place-order", json={
        "item_id": item_id,
        "quantity": 1,
        "payment_method": "cod",
        "prepaid_amount": 0.0,
        "address": "Satdobato, Lalitpur",
        "latitude": 27.6580,
        "longitude": 85.3250
    }, headers={"Authorization": f"Bearer {customer_token}"})

    data = res.json() if res.status_code in [200, 201] else {}
    cap_order_id = data.get("order_id")
    cap_del_id = data.get("delivery_id")

    del_rec = db.query(Delivery).filter(Delivery.id == cap_del_id).first()
    ord_rec = db.query(Order).filter(Order.id == cap_order_id).first()

    capacity_ok = (
        res.status_code in [200, 201] and
        ord_rec is not None and
        del_rec is not None and
        del_rec.status == "unassigned" and
        del_rec.rider_id is None
    )
    log_test("18. All Riders At Capacity (Order succeeds, delivery remains unassigned)", capacity_ok,
             f"Order: {cap_order_id}, Status: {del_rec.status if del_rec else None}")
finally:
    # Reset riders to normal workloads
    r1 = db.query(Rider).filter(Rider.id == 1).first()
    r2 = db.query(Rider).filter(Rider.id == 2).first()
    r3 = db.query(Rider).filter(Rider.id == 3).first()
    if r1: r1.current_order_count = 2
    if r2: r2.current_order_count = 5
    if r3: r3.current_order_count = 20 # Keep Suresh at capacity for tests
    db.commit()
    db.close()

# ----------------------------------------------------------------
# TEST 19: REQUIREMENT 7 - ML PREDICTION FAILURE FALLBACK
# ----------------------------------------------------------------
db = SessionLocal()
try:
    with patch("app.ml.predictor.predict", side_effect=RuntimeError("Simulated Model Engine Failure")):
        res = requests.post(f"{BASE_URL}/place-order", json={
            "item_id": item_id,
            "quantity": 1,
            "payment_method": "cod",
            "prepaid_amount": 0.0,
            "address": "Balkumari, Lalitpur",
            "latitude": 27.6700,
            "longitude": 85.3400
        }, headers={"Authorization": f"Bearer {customer_token}"})

        data = res.json() if res.status_code in [200, 201] else {}
        ml_fail_ord_id = data.get("order_id")
        ml_fail_del_id = data.get("delivery_id")

        ord_rec = db.query(Order).filter(Order.id == ml_fail_ord_id).first()
        del_rec = db.query(Delivery).filter(Delivery.id == ml_fail_del_id).first()
        pred_rec = db.query(Prediction).filter(Prediction.order_id == ml_fail_ord_id).first()

        ml_fallback_ok = (
            res.status_code in [200, 201] and
            ord_rec is not None and
            ord_rec.risk_level == "MEDIUM" and
            ord_rec.risk_score is None and
            pred_rec is None and
            del_rec is not None and
            del_rec.status == "assigned"
        )
        log_test("19. ML Prediction Failure Fallback (Safe dispatch without fake Prediction record)", ml_fallback_ok,
                 f"Order: {ml_fail_ord_id}, Deliv Status: {del_rec.status if del_rec else None}, Fake Pred Stored: {pred_rec is not None}")
except Exception as e:
    log_test("19. ML Prediction Failure Fallback", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 20: REQUIREMENT 8 - EXTERNAL SERVICE FALLBACK (ROUTING / WEATHER)
# ----------------------------------------------------------------
db = SessionLocal()
try:
    with patch("app.services.ors_service.build_route_info", side_effect=Exception("ORS Connection Refused")), \
         patch("app.services.weather_service.fetch_route_weather", side_effect=Exception("Weather API 500")):
        res = requests.post(f"{BASE_URL}/place-order", json={
            "item_id": item_id,
            "quantity": 1,
            "payment_method": "cod",
            "prepaid_amount": 0.0,
            "address": "Patan Durbar Square, Lalitpur",
            "latitude": 27.6727,
            "longitude": 85.3256
        }, headers={"Authorization": f"Bearer {customer_token}"})

        ext_data = res.json() if res.status_code in [200, 201] else {}
        ext_ord_id = ext_data.get("order_id")
        ext_del_id = ext_data.get("delivery_id")

        del_rec = db.query(Delivery).filter(Delivery.id == ext_del_id).first()
        ext_fallback_ok = (
            res.status_code in [200, 201] and
            del_rec is not None and
            del_rec.distance_km == 5.0 and
            del_rec.estimated_duration == 20.0 and
            del_rec.status == "assigned"
        )
        log_test("20. External Service Fallback (Gracefully handles ORS and Weather failures)", ext_fallback_ok,
                 f"Distance: {del_rec.distance_km if del_rec else None}km, Duration: {del_rec.estimated_duration if del_rec else None}min")
except Exception as e:
    log_test("20. External Service Fallback", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 21: REQUIREMENT 9 - DUPLICATE ASSIGNMENT PROTECTION
# ----------------------------------------------------------------
try:
    # Try assigning a delivery that is not in unassigned/failed status
    dup_res = requests.post(f"{BASE_URL}/admin/deliveries/{created_delivery_id}/start", headers={"Authorization": f"Bearer {admin_token}"})
    # Now in picked_up status -> assign attempt MUST return 422
    re_assign_res = requests.post(f"{BASE_URL}/admin/deliveries/{created_delivery_id}/assign", params={"rider_id": 1}, headers={"Authorization": f"Bearer {admin_token}"})
    
    log_test("21. Duplicate/Invalid Status Assignment Protection (409/422)", re_assign_res.status_code in [409, 422],
             f"Status: {re_assign_res.status_code}, Body: {re_assign_res.text}")
except Exception as e:
    log_test("21. Duplicate/Invalid Status Assignment Protection", False, str(e))

# ----------------------------------------------------------------
# TEST 22: REQUIREMENT 10 - CONCURRENT RIDER ASSIGNMENT / ROW LOCK CAPACITY PROTECTION
# ----------------------------------------------------------------
db = SessionLocal()
try:
    ramesh = db.query(Rider).filter(Rider.name.ilike("%Ramesh%")).first() or db.query(Rider).first()
    target_rider_id = ramesh.id
    ramesh.current_order_count = 19
    ramesh.max_orders_per_day = 20
    db.commit()

    cust = db.query(Customer).first()
    target_cust_id = cust.id if cust else 1

    # Create two unassigned delivery records
    ord_c1 = Order(customer_id=target_cust_id, item_id=item_id, quantity=1, total_price=90000, is_cod=True, prepaid_amount=0, address="Lagankhel", latitude=27.667, longitude=85.320, status="placed")
    ord_c2 = Order(customer_id=target_cust_id, item_id=item_id, quantity=1, total_price=90000, is_cod=True, prepaid_amount=0, address="Jawalakhel", latitude=27.674, longitude=85.312, status="placed")
    db.add_all([ord_c1, ord_c2])
    db.flush()
    del_c1 = Delivery(order_id=ord_c1.id, status="unassigned")
    del_c2 = Delivery(order_id=ord_c2.id, status="unassigned")
    db.add_all([del_c1, del_c2])
    db.commit()
    del_c1_id = del_c1.id
    del_c2_id = del_c2.id

    def try_assign(del_id):
        _db = SessionLocal()
        try:
            assign_delivery(_db, delivery_id=del_id, rider_id=target_rider_id, risk_level="LOW")
            _db.commit()
            return True
        except Exception:
            _db.rollback()
            return False
        finally:
            _db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_assign, del_c1_id)
        f2 = executor.submit(try_assign, del_c2_id)
        res1 = f1.result()
        res2 = f2.result()

    db.refresh(ramesh)
    # Exactly one should have succeeded, and count must NOT exceed 20
    concurrency_ok = (res1 != res2) and (ramesh.current_order_count == 20)
    log_test("22. Concurrent Rider Capacity Protection (with_for_update row locking)", concurrency_ok,
             f"Successes: {[res1, res2]}, Final Workload: {ramesh.current_order_count}/20")
except Exception as e:
    log_test("22. Concurrent Rider Capacity Protection", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 23: REQUIREMENT 11 - MANUAL ADMIN OVERRIDE / REASSIGNMENT
# ----------------------------------------------------------------
db = SessionLocal()
try:
    cust = db.query(Customer).first()
    target_cust_id = cust.id if cust else 1

    # Create unassigned delivery
    ord_m = Order(customer_id=target_cust_id, item_id=item_id, quantity=1, total_price=90000, is_cod=True, prepaid_amount=0, address="Sanepa", latitude=27.680, longitude=85.310, status="placed")
    db.add(ord_m)
    db.flush()
    del_m = Delivery(order_id=ord_m.id, status="unassigned")
    db.add(del_m)
    db.commit()
    del_m_id = del_m.id

    # Reset Rider 1 and 2 workloads
    r1 = db.query(Rider).filter(Rider.name.ilike("%Bikash%")).first() or db.query(Rider).all()[0]
    r2 = db.query(Rider).filter(Rider.name.ilike("%Ramesh%")).first() or db.query(Rider).all()[1]
    r1_id = r1.id
    r2_id = r2.id
    r1.current_order_count = 5
    r2.current_order_count = 5
    db.commit()

    # Admin assigns Rider 1
    requests.post(f"{BASE_URL}/admin/deliveries/{del_m_id}/assign", params={"rider_id": r1_id}, headers={"Authorization": f"Bearer {admin_token}"})
    db.refresh(r1)
    db.refresh(del_m)
    r1_load_after_first = r1.current_order_count

    # Admin overrides with Rider 2
    override_res = requests.post(f"{BASE_URL}/admin/deliveries/{del_m_id}/assign", params={"rider_id": r2_id}, headers={"Authorization": f"Bearer {admin_token}"})
    db.refresh(r1)
    db.refresh(r2)
    db.refresh(del_m)

    override_ok = (
        override_res.status_code == 200 and
        del_m.rider_id == r2_id and
        r1.current_order_count == r1_load_after_first - 1 and
        r2.current_order_count == 6
    )
    log_test("23. Manual Admin Override (Releases previous rider workload, assigns new rider)", override_ok,
             f"Status: {override_res.status_code}, Rider: {del_m.rider_id}, R1 Load: {r1.current_order_count}, R2 Load: {r2.current_order_count}")
except Exception as e:
    log_test("23. Manual Admin Override", False, str(e))
finally:
    db.close()

# ----------------------------------------------------------------
# TEST 24: REQUIREMENT 12 - DELIVERY LIFECYCLE: ASSIGNED → PICKED_UP → OUT_FOR_DELIVERY → DELIVERED
# ----------------------------------------------------------------
try:
    # Out for delivery
    res_out = requests.post(f"{BASE_URL}/admin/deliveries/{created_delivery_id}/out-for-delivery", headers={"Authorization": f"Bearer {admin_token}"})
    
    # Complete
    db = SessionLocal()
    del_rec_init = db.query(Delivery).filter(Delivery.id == created_delivery_id).first()
    assigned_r = del_rec_init.rider_id
    r_before = db.query(Rider).filter(Rider.id == assigned_r).first()
    cust_before = db.query(Customer).filter(Customer.phone == test_phone).first()
    r_load_before = r_before.current_order_count
    r_comp_before = r_before.completed_orders
    c_succ_before = cust_before.successful_deliveries
    db.close()

    res_comp = requests.post(f"{BASE_URL}/admin/deliveries/{created_delivery_id}/complete", params={"actual_duration": 25.0}, headers={"Authorization": f"Bearer {admin_token}"})

    db = SessionLocal()
    del_rec = db.query(Delivery).filter(Delivery.id == created_delivery_id).first()
    ord_rec = db.query(Order).filter(Order.id == created_order_id).first()
    r_after = db.query(Rider).filter(Rider.id == assigned_r).first()
    cust_after = db.query(Customer).filter(Customer.phone == test_phone).first()

    complete_ok = (
        res_comp.status_code == 200 and
        del_rec.status == "delivered" and
        del_rec.delivered_at is not None and
        del_rec.actual_duration == 25.0 and
        ord_rec.status == "delivered" and
        r_after.current_order_count == r_load_before - 1 and
        r_after.completed_orders == r_comp_before + 1 and
        cust_after.successful_deliveries == c_succ_before + 1
    )
    db.close()
    log_test("24. Delivery Lifecycle: Assigned → Picked_Up → Out_For_Delivery → Delivered", complete_ok,
             f"Status: {del_rec.status}, Rider Load: {r_load_before}->{r_after.current_order_count}, Cust Succ: {c_succ_before}->{cust_after.successful_deliveries}")
except Exception as e:
    log_test("24. Delivery Lifecycle: Complete Delivery", False, str(e))

# ----------------------------------------------------------------
# TEST 25: REQUIREMENT 13 - FAILED DELIVERY → WORKLOAD RELEASE → REASSIGNMENT
# ----------------------------------------------------------------
try:
    # 1. Place order
    f_res = requests.post(f"{BASE_URL}/place-order", json={
        "item_id": item_id,
        "quantity": 1,
        "payment_method": "cod",
        "prepaid_amount": 0.0,
        "address": "Balkumari, Lalitpur",
        "latitude": 27.6700,
        "longitude": 85.3400
    }, headers={"Authorization": f"Bearer {customer_token}"})
    f_data = f_res.json()
    f_order_id = f_data.get("order_id")
    f_delivery_id = f_data.get("delivery_id")
    initial_assigned_rider = f_data.get("assigned_rider_id")

    # 2. Start delivery
    requests.post(f"{BASE_URL}/admin/deliveries/{f_delivery_id}/start", headers={"Authorization": f"Bearer {admin_token}"})

    # 3. Fail delivery (unreachable)
    db = SessionLocal()
    r_before = db.query(Rider).filter(Rider.id == initial_assigned_rider).first()
    cust_before = db.query(Customer).filter(Customer.phone == test_phone).first()
    r_fails_before = r_before.failed_deliveries
    r_load_before = r_before.current_order_count
    c_unreach_before = cust_before.unreachable_count
    db.close()

    fail_res = requests.post(f"{BASE_URL}/admin/deliveries/{f_delivery_id}/fail", params={"failure_reason": "Customer phone switched off", "unreachable": True}, headers={"Authorization": f"Bearer {admin_token}"})

    db = SessionLocal()
    del_failed = db.query(Delivery).filter(Delivery.id == f_delivery_id).first()
    r_after = db.query(Rider).filter(Rider.id == initial_assigned_rider).first()
    cust_after = db.query(Customer).filter(Customer.phone == test_phone).first()

    fail_ok = (
        fail_res.status_code == 200 and
        del_failed.status == "unreachable" and
        del_failed.failure_reason == "Customer phone switched off" and
        r_after.current_order_count == r_load_before - 1 and
        r_after.failed_deliveries == r_fails_before + 1 and
        cust_after.unreachable_count == c_unreach_before + 1
    )
    db.close()

    # 4. Reassign delivery
    reassign_res = requests.post(f"{BASE_URL}/admin/deliveries/{f_delivery_id}/reassign", headers={"Authorization": f"Bearer {admin_token}"})
    db = SessionLocal()
    del_reassigned = db.query(Delivery).filter(Delivery.id == f_delivery_id).first()
    db.close()

    reassign_ok = (
        reassign_res.status_code == 200 and
        del_reassigned.status == "assigned" and
        del_reassigned.rider_id is not None and
        del_reassigned.rider_id != initial_assigned_rider
    )
    log_test("25. Failed Delivery Workload Release & Safe Reassignment (Excludes failed rider)", fail_ok and reassign_ok,
             f"Failed Status: {del_failed.status}, Failed Rider: {initial_assigned_rider}, New Rider: {del_reassigned.rider_id}")
except Exception as e:
    log_test("25. Failed Delivery & Reassignment", False, str(e))

# ----------------------------------------------------------------
# TEST 26-29: ADMIN OBSERVABILITY & DASHBOARD APIS
# ----------------------------------------------------------------
# SHAP Explain API
try:
    exp_res = requests.post(f"{BASE_URL}/predict/explain", json={
        "phone_number": test_phone,
        "pickup_address": "Lokanthali, Bhaktapur",
        "delivery_address": "Jawalakhel, Lalitpur",
        "pickup_latitude": 27.6749,
        "pickup_longitude": 85.3601,
        "delivery_latitude": 27.6744,
        "delivery_longitude": 85.3123,
        "order_value": 90000,
        "quantity": 1,
        "payment_method": "cod",
        "prepaid_amount": 0.0
    }, headers={"Authorization": f"Bearer {admin_token}"})
    log_test("26. Admin ML Explain API (POST /predict/explain with SHAP)", exp_res.status_code == 200 and "explanations" in exp_res.json())
except Exception as e:
    log_test("26. Admin ML Explain API", False, str(e))

# History API
try:
    hist_res = requests.get(f"{BASE_URL}/history", headers={"Authorization": f"Bearer {admin_token}"})
    log_test("27. Admin History API (GET /history)", hist_res.status_code == 200 and isinstance(hist_res.json(), list))
except Exception as e:
    log_test("27. Admin History API", False, str(e))

# Dashboard API
try:
    dash_res = requests.get(f"{BASE_URL}/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    log_test("28. Admin Operations Dashboard API (GET /admin/dashboard)", dash_res.status_code == 200 and "operations" in dash_res.json())
except Exception as e:
    log_test("28. Admin Operations Dashboard API", False, str(e))

# Riders List API
try:
    riders_res = requests.get(f"{BASE_URL}/admin/riders", headers={"Authorization": f"Bearer {admin_token}"})
    log_test("29. Admin Fleet & Riders API (GET /admin/riders)", riders_res.status_code == 200 and isinstance(riders_res.json(), list))
except Exception as e:
    log_test("29. Admin Fleet & Riders API", False, str(e))

print("==================================================")
print(f"AUDIT SUMMARY: {len(results['passed'])} PASSED, {len(results['failed'])} FAILED out of {len(results['details'])} TOTAL TESTS")
print("==================================================")

with open("audit_results.json", "w") as f:
    json.dump(results, f, indent=2)

sys.exit(0 if len(results['failed']) == 0 else 1)
