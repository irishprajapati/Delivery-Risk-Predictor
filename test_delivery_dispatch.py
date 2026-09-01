import os
import json
from pprint import pprint

import requests


BASE_URL = "http://127.0.0.1:8000"

# Put your current admin JWT in the environment instead of
# hardcoding it into the script.
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2Iiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzg2Nzg2ODEyfQ.B1OhGJhbG9SAEOY8gDW_lcAO3PW_Vg9hehSQirLRiMY"

# Change this only when you want to test a different ML risk.
RISK_LEVEL = "LOW"

TIMEOUT = 30


def headers():
    if not ADMIN_TOKEN:
        raise RuntimeError(
            "ADMIN_TOKEN is not set.\n"
            "Run:\n"
            "export ADMIN_TOKEN='your_admin_jwt_here'"
        )

    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {ADMIN_TOKEN}",
    }


def print_response(title, response):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    print(f"HTTP {response.status_code}")

    try:
        data = response.json()
        pprint(data, sort_dicts=False)
        return data

    except ValueError:
        print(response.text)
        return None


def get_admin_riders():
    response = requests.get(
        f"{BASE_URL}/admin/riders",
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        "1. CURRENT RIDERS",
        response,
    )


def get_rider_options(delivery_id):
    response = requests.get(
        f"{BASE_URL}/admin/deliveries/"
        f"{delivery_id}/rider-options",
        params={
            "risk_level": RISK_LEVEL,
        },
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        f"2. RIDER OPTIONS FOR DELIVERY {delivery_id}",
        response,
    )


def assign_rider(delivery_id):
    response = requests.post(
        f"{BASE_URL}/admin/deliveries/"
        f"{delivery_id}/assign",
        params={
            "risk_level": RISK_LEVEL,
        },
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        f"3. AUTOMATIC RIDER ASSIGNMENT "
        f"FOR DELIVERY {delivery_id}",
        response,
    )


def get_delivery(delivery_id):
    response = requests.get(
        f"{BASE_URL}/admin/deliveries/"
        f"{delivery_id}",
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        f"4. DELIVERY DETAILS {delivery_id}",
        response,
    )


def start_delivery(delivery_id):
    response = requests.post(
        f"{BASE_URL}/admin/deliveries/"
        f"{delivery_id}/start",
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        f"5. START DELIVERY {delivery_id}",
        response,
    )


def mark_out_for_delivery(delivery_id):
    response = requests.post(
        f"{BASE_URL}/admin/deliveries/"
        f"{delivery_id}/out-for-delivery",
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        f"6. OUT FOR DELIVERY {delivery_id}",
        response,
    )


def complete_delivery(
    delivery_id,
    actual_duration=25,
):
    response = requests.post(
        f"{BASE_URL}/admin/deliveries/"
        f"{delivery_id}/complete",
        params={
            "actual_duration": actual_duration,
        },
        headers=headers(),
        timeout=TIMEOUT,
    )

    return print_response(
        f"7. COMPLETE DELIVERY {delivery_id}",
        response,
    )


def find_latest_unassigned_delivery():
    """
    We don't have a dedicated GET /deliveries endpoint in the
    current API, so this function reads the PostgreSQL database
    directly.

    This keeps the test script from making you manually enter IDs.
    """

    from app.database import SessionLocal
    from app.model import Delivery

    db = SessionLocal()

    try:
        delivery = (
            db.query(Delivery)
            .filter(
                Delivery.status == "unassigned"
            )
            .order_by(
                Delivery.id.desc()
            )
            .first()
        )

        if delivery is None:
            return None

        return delivery.id

    finally:
        db.close()


def main():
    print("\n")
    print("=" * 80)
    print("DELIVERY DISPATCH INTEGRATION TEST")
    print("=" * 80)
    print(f"Base URL : {BASE_URL}")
    print(f"Risk     : {RISK_LEVEL}")

    # --------------------------------------------------------
    # 1. Riders
    # --------------------------------------------------------

    get_admin_riders()

    # --------------------------------------------------------
    # 2. Find clean delivery
    # --------------------------------------------------------

    delivery_id = find_latest_unassigned_delivery()

    if delivery_id is None:
        print("\nNo unassigned delivery found.")

        print(
            "\nCreate a new order first, then run this script again."
        )

        return

    print(
        f"\nSelected unassigned delivery: {delivery_id}"
    )

    # --------------------------------------------------------
    # 3. Candidate ranking
    # --------------------------------------------------------

    candidates = get_rider_options(
        delivery_id
    )

    if not candidates:
        print(
            "\nCould not retrieve rider candidates."
        )
        return

    candidate_count = candidates.get(
        "candidate_count",
        0,
    )

    if candidate_count == 0:
        print(
            "\nNo eligible riders were found."
        )

        print(
            "\nCheck that at least one rider is:"
            "\n  - active"
            "\n  - below capacity"
            "\n  - compatible with the delivery area"
        )

        return

    # --------------------------------------------------------
    # 4. Automatic assignment
    # --------------------------------------------------------

    assignment = assign_rider(
        delivery_id
    )

    if not assignment:
        print(
            "\nAssignment request failed."
        )
        return

    # --------------------------------------------------------
    # 5. Verify assignment
    # --------------------------------------------------------

    delivery = get_delivery(
        delivery_id
    )

    if not delivery:
        return

    # --------------------------------------------------------
    # 6. Start
    # --------------------------------------------------------

    started = start_delivery(
        delivery_id
    )

    if not started:
        return

    # --------------------------------------------------------
    # 7. Out for delivery
    # --------------------------------------------------------

    out_for_delivery = (
        mark_out_for_delivery(
            delivery_id
        )
    )

    if not out_for_delivery:
        return

    # --------------------------------------------------------
    # 8. Complete
    # --------------------------------------------------------

    complete = complete_delivery(
        delivery_id,
        actual_duration=25,
    )

    if not complete:
        return

    get_delivery(
        delivery_id
    )
    get_admin_riders()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(
        f"Delivery {delivery_id} was tested through "
        "automatic assignment and successful completion."
    )


if __name__ == "__main__":
    main()