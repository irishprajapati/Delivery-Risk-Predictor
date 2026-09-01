import json
import os
import sys
import time
import requests
import subprocess
from datetime import datetime
from sqlalchemy import text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from app.database import SessionLocal, engine, Base
from app.model import User, Customer, Rider, Item, Category, Order, Delivery, Prediction, RiderAreaPerformance, DeliveryLocation
from app.utils.security import get_password_hash, create_access_token

BASE_URL = "http://127.0.0.1:8001"
results = {"passed": [], "failed": [], "details": []}

def log_test(name, passed, detail=""):
    status_str = "PASS" if passed else "FAIL"
    results["details"].append({"name": name, "status": status_str, "detail": detail})
    if passed:
        results["passed"].append(name)
        print(f"  [PASS] {name}")
    else:
        results["failed"].append(name)
        print(f"  [FAIL] {name}: {detail}")

print("==================================================")
print("STARTING RIDER OPERATIONS TEST SUITE")
print("==================================================")

# 1. Clean and Setup Test Data
db = SessionLocal()
try:
    db.query(Prediction).delete()
    db.query(Delivery).delete()
    db.query(DeliveryLocation).delete()
    db.query(Order).delete()
    db.query(RiderAreaPerformance).delete()
    db.query(Rider).delete()
    db.query(Customer).delete()
    db.query(User).delete()
    db.query(Item).delete()
    db.query(Category).delete()
    db.commit()

    # Create Categories
    cat1 = Category(id=1, name="Electronics", risk_score=0.1)
    cat2 = Category(id=2, name="Fashion", risk_score=0.2)
    db.add_all([cat1, cat2])
    db.commit()

    # Create Users
    admin_user = User(username="admin", password=get_password_hash("admin123"), role="admin", is_active=True)
    db.add(admin_user)

    # Create Customers
    c1 = Customer(phone="9841878273", password_hash=get_password_hash("pass123"), is_verified=True, total_orders=5, successful_deliveries=4, failed_deliveries=1)
    db.add(c1)

    # Create Riders
    r1 = Rider(id=1, name="Rider Bikash", phone="9800000001", area="Lalitpur", is_active=True, max_orders_per_day=20, current_order_count=2, completed_orders=45, failed_deliveries=3, current_latitude=27.6710, current_longitude=85.3380)
    r2 = Rider(id=2, name="Rider Ramesh", phone="9800000002", area="Kathmandu", is_active=True, max_orders_per_day=20, current_order_count=1, completed_orders=30, failed_deliveries=5, current_latitude=27.7172, current_longitude=85.3240)
    r3 = Rider(id=3, name="Rider Inactive", phone="9800000003", area="Bhaktapur", is_active=False, max_orders_per_day=20, current_order_count=0, completed_orders=10, failed_deliveries=1, current_latitude=27.6710, current_longitude=85.4298)
    db.add_all([r1, r2, r3])

    # Rider 1 User Account
    r1_user = User(username="9800000001", password=get_password_hash("rider123"), role="rider", is_active=True)
    r2_user = User(username="9800000002", password=get_password_hash("rider123"), role="rider", is_active=True)
    db.add_all([r1_user, r2_user])

    # Create Catalog Items
    item1 = Item(id=1, name="Wireless Earbuds", category_id=cat1.id, price=2500.0)
    item2 = Item(id=2, name="Winter Jacket", category_id=cat2.id, price=4500.0)
    db.add_all([item1, item2])
    db.commit()

    # Pre-create test Orders and Deliveries
    # Order 1: Assigned to Rider 1 (Lalitpur)
    order1 = Order(id=101, customer_id=c1.id, item_id=item1.id, quantity=1, total_price=2500.0, is_cod=True, prepaid_amount=0.0, address="Patan Durbar Square, Lalitpur", latitude=27.6744, longitude=85.3240, status="assigned", risk_level="LOW", risk_score=0.15)
    db.add(order1)
    db.commit()

    del1 = Delivery(id=201, order_id=order1.id, rider_id=r1.id, status="assigned", attempt_count=0, assigned_at=datetime.utcnow(), created_at=datetime.utcnow())
    db.add(del1)

    # Order 2: Assigned to Rider 2 (Kathmandu)
    order2 = Order(id=102, customer_id=c1.id, item_id=item2.id, quantity=1, total_price=4500.0, is_cod=False, prepaid_amount=4500.0, address="Thamel, Kathmandu", latitude=27.7150, longitude=85.3120, status="assigned", risk_level="HIGH", risk_score=0.75)
    db.add(order2)
    db.commit()

    del2 = Delivery(id=202, order_id=order2.id, rider_id=r2.id, status="assigned", attempt_count=0, assigned_at=datetime.utcnow(), created_at=datetime.utcnow())
    db.add(del2)

    # Order 3: Assigned to Rider 1 (High Risk)
    order3 = Order(id=103, customer_id=c1.id, item_id=item1.id, quantity=2, total_price=5000.0, is_cod=True, prepaid_amount=0.0, address="Jawalakhel, Lalitpur", latitude=27.6680, longitude=85.3160, status="assigned", risk_level="HIGH", risk_score=0.82)
    db.add(order3)
    db.commit()

    del3 = Delivery(id=203, order_id=order3.id, rider_id=r1.id, status="assigned", attempt_count=0, assigned_at=datetime.utcnow(), created_at=datetime.utcnow())
    db.add(del3)
    db.commit()

    print("✓ Test database seeded with Users, Customers, Riders, and Deliveries.")
finally:
    db.close()

# 2. Launch Test Server on Port 8001
server_process = subprocess.Popen(
    ["./venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

time.sleep(2.5)

try:
    # -------------------------------------------------------------
    # TEST 1: Rider Login (Valid Credentials)
    # -------------------------------------------------------------
    login_res = requests.post(f"{BASE_URL}/rider/login", json={"phone": "9800000001", "password": "rider123"})
    log_test(
        "1. Rider Login (Valid Phone + Password)",
        login_res.status_code == 200 and "access_token" in login_res.json() and login_res.json()["rider"]["name"] == "Rider Bikash",
        f"Status: {login_res.status_code}, Body: {login_res.text[:100]}"
    )
    rider1_token = login_res.json().get("access_token")

    # -------------------------------------------------------------
    # TEST 2: Rider Login (Invalid Password)
    # -------------------------------------------------------------
    bad_login_res = requests.post(f"{BASE_URL}/rider/login", json={"phone": "9800000001", "password": "wrongpassword"})
    log_test(
        "2. Rider Login (Invalid Password Rejection)",
        bad_login_res.status_code == 401,
        f"Status: {bad_login_res.status_code}"
    )

    # -------------------------------------------------------------
    # TEST 3: Rider Login (Inactive Rider Rejection)
    # -------------------------------------------------------------
    inactive_login_res = requests.post(f"{BASE_URL}/rider/login", json={"phone": "9800000003", "password": "rider123"})
    log_test(
        "3. Inactive Rider Login Rejection",
        inactive_login_res.status_code == 403,
        f"Status: {inactive_login_res.status_code}"
    )

    # -------------------------------------------------------------
    # TEST 4: Customer Token Blocked from Rider Profile (RBAC)
    # -------------------------------------------------------------
    cust_login_res = requests.post(f"{BASE_URL}/customer/login", params={"phone": "9841878273", "password": "pass123"})
    cust_token = cust_login_res.json().get("access_token")

    cust_on_rider_res = requests.get(f"{BASE_URL}/rider/profile", headers={"Authorization": f"Bearer {cust_token}"})
    log_test(
        "4. RBAC: Customer Token Blocked from Rider API",
        cust_on_rider_res.status_code == 403,
        f"Status: {cust_on_rider_res.status_code}"
    )

    # -------------------------------------------------------------
    # TEST 5: Rider Profile API
    # -------------------------------------------------------------
    prof_res = requests.get(f"{BASE_URL}/rider/profile", headers={"Authorization": f"Bearer {rider1_token}"})
    prof_data = prof_res.json()
    log_test(
        "5. Rider Profile API (GET /rider/profile)",
        prof_res.status_code == 200 and prof_data["name"] == "Rider Bikash" and prof_data["remaining_capacity"] == 18,
        f"Status: {prof_res.status_code}, Remaining: {prof_data.get('remaining_capacity')}"
    )

    # -------------------------------------------------------------
    # TEST 6: Rider Deliveries List API (Ownership Scoped)
    # -------------------------------------------------------------
    del_list_res = requests.get(f"{BASE_URL}/rider/deliveries", headers={"Authorization": f"Bearer {rider1_token}"})
    del_list = del_list_res.json()
    # Rider 1 has Order 101 and Order 103 (Total 2)
    log_test(
        "6. Rider Deliveries List (Scoping & Count)",
        del_list_res.status_code == 200 and del_list["total"] == 2 and len(del_list["items"]) == 2,
        f"Total items: {del_list.get('total')}"
    )

    # -------------------------------------------------------------
    # TEST 7: Rider Deliveries Ordering (High Risk Priority)
    # -------------------------------------------------------------
    items = del_list.get("items", [])
    high_risk_first = len(items) >= 2 and items[0]["risk"] == "HIGH"
    log_test(
        "7. Rider Deliveries Ordering (High Risk Prioritized)",
        high_risk_first,
        f"First Item Risk: {items[0]['risk'] if items else 'None'}"
    )

    # -------------------------------------------------------------
    # TEST 8: Rider Delivery Detail API (Owned Delivery)
    # -------------------------------------------------------------
    del_detail_res = requests.get(f"{BASE_URL}/rider/deliveries/201", headers={"Authorization": f"Bearer {rider1_token}"})
    del_detail = del_detail_res.json()
    log_test(
        "8. Rider Delivery Detail (GET /rider/deliveries/201)",
        del_detail_res.status_code == 200 and del_detail["delivery_id"] == 201 and "location" in del_detail,
        f"Status: {del_detail_res.status_code}"
    )

    # -------------------------------------------------------------
    # TEST 9: Cross-Rider Security (Rider 1 cannot inspect Rider 2's delivery)
    # -------------------------------------------------------------
    cross_res = requests.get(f"{BASE_URL}/rider/deliveries/202", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "9. Security: Rider A Cannot Inspect Rider B's Delivery",
        cross_res.status_code == 404,
        f"Status: {cross_res.status_code} (Expected 404)"
    )

    # -------------------------------------------------------------
    # TEST 10: Cross-Rider Security (Rider 1 cannot operate Rider 2's delivery)
    # -------------------------------------------------------------
    cross_pickup_res = requests.post(f"{BASE_URL}/rider/deliveries/202/pickup", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "10. Security: Rider A Cannot Advance Rider B's Delivery",
        cross_pickup_res.status_code == 404,
        f"Status: {cross_pickup_res.status_code} (Expected 404)"
    )

    # -------------------------------------------------------------
    # TEST 11: Rider Normal Lifecycle Transition: Pick Up Package
    # -------------------------------------------------------------
    pickup_res = requests.post(f"{BASE_URL}/rider/deliveries/201/pickup", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "11. Rider Action: Pick Up Package (assigned -> picked_up)",
        pickup_res.status_code == 200 and pickup_res.json()["status"] == "picked_up",
        f"Status: {pickup_res.status_code}, Body: {pickup_res.text[:100]}"
    )

    # -------------------------------------------------------------
    # TEST 12: State Machine Rejection: Cannot complete picked_up delivery directly
    # -------------------------------------------------------------
    bad_complete_res = requests.post(f"{BASE_URL}/rider/deliveries/201/complete", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "12. State Machine Rejection: Cannot complete picked_up delivery directly",
        bad_complete_res.status_code == 409,
        f"Status: {bad_complete_res.status_code} (Expected 409 Conflict)"
    )

    # -------------------------------------------------------------
    # TEST 13: Rider Normal Lifecycle Transition: Start Transit (Out for Delivery)
    # -------------------------------------------------------------
    start_res = requests.post(f"{BASE_URL}/rider/deliveries/201/start", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "13. Rider Action: Start Transit (picked_up -> out_for_delivery)",
        start_res.status_code == 200 and start_res.json()["status"] == "out_for_delivery",
        f"Status: {start_res.status_code}"
    )

    # -------------------------------------------------------------
    # TEST 14: State Machine Rejection: Cannot pick up already out_for_delivery package
    # -------------------------------------------------------------
    bad_pickup_res = requests.post(f"{BASE_URL}/rider/deliveries/201/pickup", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "14. State Machine Rejection: Cannot pick up already out_for_delivery package",
        bad_pickup_res.status_code == 409,
        f"Status: {bad_pickup_res.status_code} (Expected 409 Conflict)"
    )

    # -------------------------------------------------------------
    # TEST 15: Rider Normal Lifecycle Transition: Mark Delivered (Complete)
    # -------------------------------------------------------------
    complete_res = requests.post(f"{BASE_URL}/rider/deliveries/201/complete", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "15. Rider Action: Mark Delivered (out_for_delivery -> delivered)",
        complete_res.status_code == 200 and complete_res.json()["status"] == "delivered",
        f"Status: {complete_res.status_code}"
    )

    # Verify workload release in profile
    prof2_res = requests.get(f"{BASE_URL}/rider/profile", headers={"Authorization": f"Bearer {rider1_token}"})
    log_test(
        "16. Rider Workload Released on Completion (current_order_count decremented)",
        prof2_res.status_code == 200 and prof2_res.json()["current_order_count"] == 1,
        f"Workload: {prof2_res.json().get('current_order_count')}"
    )

    # -------------------------------------------------------------
    # TEST 17: Structured Failure: Unreachable Reason (Order 203)
    # -------------------------------------------------------------
    # Pick up delivery 203 first
    requests.post(f"{BASE_URL}/rider/deliveries/203/pickup", headers={"Authorization": f"Bearer {rider1_token}"})
    requests.post(f"{BASE_URL}/rider/deliveries/203/start", headers={"Authorization": f"Bearer {rider1_token}"})

    # Report failure with CUSTOMER_UNAVAILABLE -> mapped to unreachable
    fail_unreach_res = requests.post(
        f"{BASE_URL}/rider/deliveries/203/fail",
        json={"reason_code": "CUSTOMER_UNAVAILABLE", "notes": "Called 3 times, phone switched off at gate"},
        headers={"Authorization": f"Bearer {rider1_token}"}
    )
    log_test(
        "17. Structured Failure: CUSTOMER_UNAVAILABLE mapped to unreachable",
        fail_unreach_res.status_code == 200 and fail_unreach_res.json()["status"] == "unreachable",
        f"Status: {fail_unreach_res.status_code}, Result Status: {fail_unreach_res.json().get('status')}"
    )

    # -------------------------------------------------------------
    # TEST 18: Structured Failure: Hard Failure with Required Notes (Rider 2 on Delivery 202)
    # -------------------------------------------------------------
    # Login Rider 2
    r2_login = requests.post(f"{BASE_URL}/rider/login", json={"phone": "9800000002", "password": "rider123"})
    rider2_token = r2_login.json().get("access_token")

    requests.post(f"{BASE_URL}/rider/deliveries/202/pickup", headers={"Authorization": f"Bearer {rider2_token}"})

    # Test missing required notes for WRONG_ADDRESS
    bad_fail_res = requests.post(
        f"{BASE_URL}/rider/deliveries/202/fail",
        json={"reason_code": "WRONG_ADDRESS", "notes": ""},
        headers={"Authorization": f"Bearer {rider2_token}"}
    )
    log_test(
        "18. Failure Validation: Missing Required Notes Rejected (422)",
        bad_fail_res.status_code == 422,
        f"Status: {bad_fail_res.status_code}"
    )

    # Test valid fail with notes
    good_fail_res = requests.post(
        f"{BASE_URL}/rider/deliveries/202/fail",
        json={"reason_code": "WRONG_ADDRESS", "notes": "Customer shifted to Pokhara"},
        headers={"Authorization": f"Bearer {rider2_token}"}
    )
    log_test(
        "19. Structured Failure: WRONG_ADDRESS with Notes Recorded as failed",
        good_fail_res.status_code == 200 and good_fail_res.json()["status"] == "failed" and "Customer shifted" in good_fail_res.json()["failure_reason"],
        f"Reason: {good_fail_res.json().get('failure_reason')}"
    )

    # -------------------------------------------------------------
    # TEST 20: Controlled Failure Reasons List API
    # -------------------------------------------------------------
    reasons_res = requests.get(f"{BASE_URL}/rider/failure-reasons")
    reasons_data = reasons_res.json()
    log_test(
        "20. Failure Reasons API (GET /rider/failure-reasons)",
        reasons_res.status_code == 200 and len(reasons_data) >= 10,
        f"Reasons count: {len(reasons_data)}"
    )

    # -------------------------------------------------------------
    # TEST 21: Full End-to-End: Customer Checkout -> Auto Dispatch -> Rider Operation
    # -------------------------------------------------------------
    order_payload = {
        "item_id": 1,
        "quantity": 1,
        "payment_method": "cod",
        "prepaid_amount": 0.0,
        "address": "Kumaripati, Lalitpur",
        "latitude": 27.6710,
        "longitude": 85.3180
    }
    checkout_res = requests.post(f"{BASE_URL}/place-order", json=order_payload, headers={"Authorization": f"Bearer {cust_token}"})
    checkout_data = checkout_res.json()
    new_order_id = checkout_data.get("order_id")
    new_delivery_id = checkout_data.get("delivery_id")

    # Fetch delivery from DB to check assigned rider
    time.sleep(0.5)
    db_chk = SessionLocal()
    deliv_chk = db_chk.query(Delivery).filter(Delivery.id == new_delivery_id).first()
    assigned_rider_id = deliv_chk.rider_id if deliv_chk else None
    db_chk.close()

    log_test(
        "21. End-to-End: Customer Checkout Automatically Dispatched to Best Rider",
        checkout_res.status_code in {200, 201} and new_delivery_id is not None and assigned_rider_id is not None,
        f"Order: {new_order_id}, Delivery: {new_delivery_id}, Rider: {assigned_rider_id}"
    )

    # Authenticate the assigned rider
    assigned_rider_token = rider1_token if assigned_rider_id == 1 else rider2_token

    # Rider performs pickup
    e2e_pickup = requests.post(f"{BASE_URL}/rider/deliveries/{new_delivery_id}/pickup", headers={"Authorization": f"Bearer {assigned_rider_token}"})
    # Rider starts transit
    e2e_start = requests.post(f"{BASE_URL}/rider/deliveries/{new_delivery_id}/start", headers={"Authorization": f"Bearer {assigned_rider_token}"})
    # Rider completes delivery
    e2e_complete = requests.post(f"{BASE_URL}/rider/deliveries/{new_delivery_id}/complete", headers={"Authorization": f"Bearer {assigned_rider_token}"})

    log_test(
        "22. End-to-End: Assigned Rider Completes Order via Rider APIs",
        e2e_pickup.status_code == 200 and e2e_start.status_code == 200 and e2e_complete.status_code == 200 and e2e_complete.json()["status"] == "delivered",
        f"Final Status: {e2e_complete.json().get('status') if e2e_complete.status_code == 200 else e2e_complete.status_code}"
    )

    # -------------------------------------------------------------
    # TEST 23: Admin Operations Dashboard Reflects Completed Delivery
    # -------------------------------------------------------------
    admin_login_res = requests.post(f"{BASE_URL}/admin/login", params={"username": "admin", "password": "admin123"})
    admin_token = admin_login_res.json().get("access_token")

    admin_dash_res = requests.get(f"{BASE_URL}/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    admin_dash = admin_dash_res.json()
    log_test(
        "23. Admin Operations Dashboard Reflects Metrics & Fleet Breakdown",
        admin_dash_res.status_code == 200 and admin_dash.get("delivered", 0) >= 2,
        f"Delivered count: {admin_dash.get('delivered')}"
    )

finally:
    server_process.terminate()
    server_process.wait()

print("==================================================")
print(f"RIDER OPERATIONS SUITE SUMMARY: {len(results['passed'])} PASSED, {len(results['failed'])} FAILED out of {len(results['details'])} TOTAL TESTS")
print("==================================================")

with open("rider_audit_results.json", "w") as f:
    json.dump(results, f, indent=2)

sys.exit(0 if len(results['failed']) == 0 else 1)
