#!/usr/bin/env python3
"""
System test suite for the FastAPI /predict endpoint.

Usage:
    1. Start the API:  uvicorn app.main:app --reload
    2. Set credentials (optional):
         export TEST_USERNAME=admin
         export TEST_PASSWORD=your_password
    3. Run:  python test_system.py

Requires: requests
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import requests

BASE_URL = os.getenv("TEST_API_URL", "http://127.0.0.1:8000")
PREDICT_URL = f"{BASE_URL}/predict"
LOGIN_URL = f"{BASE_URL}/login"
PERF_THRESHOLD_MS = 2000

USERNAME = os.getenv("TEST_USERNAME", "db")
PASSWORD = os.getenv("TEST_PASSWORD", "123456")


@dataclass
class TestCase:
    test_id: str
    category: str
    description: str
    payload: dict[str, Any]
    expected: dict[str, Any]
    send_raw_json: str | None = None


@dataclass
class TestResult:
    test_id: str
    category: str
    payload_summary: str
    expected_summary: str
    actual_summary: str
    status: str
    response_ms: float
    perf_status: str
    functional_pass: bool
    perf_pass: bool
    raw_response: Any = field(default=None)


# 12 realistic system test cases covering all required scenarios
TEST_CASES: list[TestCase] = [
    # --- Valid valley deliveries (Kathmandu / Lalitpur / Bhaktapur) ---
    TestCase(
        test_id="TC01",
        category="Valid Location",
        description="Kathmandu → Baneshwor, low-value prepaid, clear weather",
        payload={
            "pickup_address": "Thamel, Kathmandu",
            "delivery_address": "Baneshwor, Kathmandu",
            "order_value": 150,
            "payment_method": "prepaid",
            "phone_number": "9811111101",
        },
        expected={
            "status_code": 200,
            "pickup_district": "kathmandu",
            "delivery_district": "kathmandu",
            "risk": "LOW",
        },
    ),
    TestCase(
        test_id="TC02",
        category="Valid Location",
        description="Kathmandu → Patan (Lalitpur), medium order, prepaid",
        payload={
            "pickup_address": "Koteshwor, Kathmandu",
            "delivery_address": "Patan, Lalitpur",
            "order_value": 800,
            "payment_method": "prepaid",
            "phone_number": "9811111102",
        },
        expected={
            "status_code": 200,
            "pickup_district": "kathmandu",
            "delivery_district": "lalitpur",
            "risk_in": ["MEDIUM", "HIGH"],
        },
    ),
    TestCase(
        test_id="TC03",
        category="Valid Location",
        description="Bhaktapur → Thimi sub-area delivery",
        payload={
            "pickup_address": "Durbar Square, Bhaktapur",
            "delivery_address": "Thimi, Bhaktapur",
            "order_value": 1200,
            "payment_method": "online",
            "phone_number": "9811111103",
        },
        expected={
            "status_code": 200,
            "pickup_district": "bhaktapur",
            "delivery_district": "bhaktapur",
            "risk_in": ["LOW", "MEDIUM", "HIGH"],
        },
    ),
    TestCase(
        test_id="TC04",
        category="Valid Location",
        description="Cross-district: Kalanki (Kathmandu) → Jawalakhel (Lalitpur)",
        payload={
            "pickup_address": "Kalanki, Kathmandu",
            "delivery_address": "Jawalakhel, Lalitpur",
            "order_value": 650,
            "payment_method": "cod",
            "phone_number": "9811111104",
        },
        expected={
            "status_code": 200,
            "delivery_district": "lalitpur",
            "risk_in": ["LOW", "MEDIUM", "HIGH"],
        },
    ),
    TestCase(
        test_id="TC04B",
        category="Valid Location",
        description="Lokanthali → Dhapakhel with live route weather",
        payload={
            "pickup_address": "Lokanthali, Bhaktapur",
            "delivery_address": "Dhapakhel, Lalitpur",
            "order_value": 1200,
            "payment_method": "prepaid",
            "phone_number": "9811111116",
        },
        expected={
            "status_code": 200,
            "pickup_district": "bhaktapur",
            "delivery_district": "lalitpur",
            "has_weather_fields": True,
            "weather_risk_in": ["LOW", "MEDIUM", "HIGH"],
        },
    ),
    # --- Order value extremes ---
    TestCase(
        test_id="TC05",
        category="Order Value",
        description="High order value (4500) with COD and rainy weather",
        payload={
            "pickup_address": "Thamel, Kathmandu",
            "delivery_address": "Baneshwor, Kathmandu",
            "order_value": 4500,
            "payment_method": "cod",
            "phone_number": "9811111105",
        },
        expected={
            "status_code": 200,
            "risk_in": ["MEDIUM", "HIGH"],
        },
    ),
    TestCase(
        test_id="TC06",
        category="Order Value",
        description="Low order value (100) prepaid in Kathmandu",
        payload={
            "pickup_address": "Baneshwor, Kathmandu",
            "delivery_address": "Thamel, Kathmandu",
            "order_value": 100,
            "payment_method": "prepaid",
            "phone_number": "9811111106",
        },
        expected={
            "status_code": 200,
            "risk": "LOW",
        },
    ),
    # --- Payment method: COD vs prepaid ---
    TestCase(
        test_id="TC07",
        category="Payment Method",
        description="COD payment with foggy weather in Bhaktapur",
        payload={
            "pickup_address": "Kathmandu",
            "delivery_address": "Suryabinayak, Bhaktapur",
            "order_value": 3000,
            "payment_method": "cash",
            "phone_number": "9811111107",
        },
        expected={
            "status_code": 200,
            "delivery_district": "bhaktapur",
            "risk_in": ["LOW", "MEDIUM", "HIGH"],
        },
    ),
    TestCase(
        test_id="TC08",
        category="Payment Method",
        description="Prepaid (online) high-value Lalitpur delivery",
        payload={
            "pickup_address": "Kathmandu",
            "delivery_address": "Patan Durbar Square, Lalitpur",
            "order_value": 2500,
            "payment_method": "online",
            "phone_number": "9811111108",
        },
        expected={
            "status_code": 200,
            "delivery_district": "lalitpur",
            "risk_in": ["LOW", "MEDIUM", "HIGH"],
        },
    ),
    # --- Invalid locations ---
    TestCase(
        test_id="TC09",
        category="Invalid Location",
        description="Delivery address outside valley (Delhi, India)",
        payload={
            "pickup_address": "Thamel, Kathmandu",
            "delivery_address": "Connaught Place, New Delhi, India",
            "order_value": 500,
            "payment_method": "prepaid",
            "phone_number": "9811111109",
        },
        expected={
            "status_code": 400,
            "detail_contains": "Service limited to Kathmandu Valley only",
        },
    ),
    TestCase(
        test_id="TC10",
        category="Invalid Location",
        description="Random text pickup address (no valley keyword)",
        payload={
            "pickup_address": "xyz random place nowhere",
            "delivery_address": "Baneshwor, Kathmandu",
            "order_value": 500,
            "payment_method": "prepaid",
            "phone_number": "9811111110",
        },
        expected={
            "status_code": 400,
            "detail_contains": "Service limited to Kathmandu Valley only",
        },
    ),
    # --- Empty / invalid fields ---
    TestCase(
        test_id="TC11",
        category="Empty / Invalid Fields",
        description="Empty pickup address",
        payload={
            "pickup_address": "",
            "delivery_address": "Baneshwor, Kathmandu",
            "order_value": 500,
            "payment_method": "prepaid",
            "phone_number": "9811111111",
        },
        expected={"status_code": 422},
    ),
    TestCase(
        test_id="TC12",
        category="Invalid Data Type",
        description="order_value sent as string instead of number",
        payload={},
        send_raw_json=(
            '{"pickup_address":"Kathmandu","delivery_address":"Bhaktapur",'
            '"order_value":"not_a_number","payment_method":"prepaid",'
            '"phone_number":"9811111115"}'
        ),
        expected={"status_code": 422},
    ),
]


def login() -> str:
    response = requests.post(
        LOGIN_URL,
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Login failed ({response.status_code}): {response.text}\n"
            f"Set TEST_USERNAME and TEST_PASSWORD env vars."
        )
    return response.json()["access_token"]


def truncate(text: str, max_len: int = 40) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def payload_summary(test: TestCase) -> str:
    if test.send_raw_json:
        return truncate(test.send_raw_json.replace('"', "'"))
    parts = [
        f"pickup={test.payload.get('pickup_address', '')[:15]}",
        f"value={test.payload.get('order_value')}",
        f"pay={test.payload.get('payment_method')}",
    ]
    return truncate(", ".join(str(p) for p in parts))


def summarize_expected(expected: dict[str, Any]) -> str:
    parts = [f"HTTP {expected['status_code']}"]
    if "detail_contains" in expected:
        parts.append("valley error")
    if "risk" in expected:
        parts.append(f"risk={expected['risk']}")
    if "risk_in" in expected:
        parts.append(f"risk∈{expected['risk_in']}")
    if "pickup_district" in expected:
        parts.append(f"pickup={expected['pickup_district']}")
    if "delivery_district" in expected:
        parts.append(f"delivery={expected['delivery_district']}")
    return truncate(" | ".join(parts), 45)


def summarize_response(status_code: int, body: Any) -> str:
    if isinstance(body, dict):
        if "detail" in body:
            detail = body["detail"]
            if isinstance(detail, list):
                return truncate(f"{status_code} | validation error")
            return truncate(f"{status_code} | {detail}")
        if "risk" in body:
            return truncate(
                f"{status_code} | risk={body.get('risk')} "
                f"pred={body.get('prediction')} "
                f"prob={body.get('probability', 0):.2f}"
            )
    return truncate(f"{status_code} | {str(body)[:60]}")


def evaluate_response(body: Any, expected: dict[str, Any], status_code: int) -> bool:
    if status_code != expected.get("status_code"):
        return False

    if "detail_contains" in expected:
        detail = body.get("detail", "") if isinstance(body, dict) else str(body)
        if isinstance(detail, list):
            detail = json.dumps(detail)
        if expected["detail_contains"] not in str(detail):
            return False

    if not isinstance(body, dict):
        return True

    for key in ("pickup_district", "delivery_district", "risk"):
        if key in expected and body.get(key) != expected[key]:
            return False

    if "risk_in" in expected and body.get("risk") not in expected["risk_in"]:
        return False

    if expected.get("has_weather_fields"):
        for field in (
            "pickup_weather",
            "midpoint_weather",
            "delivery_weather",
            "weather_risk",
            "weather_risk_message",
        ):
            if field not in body:
                return False
        for field in ("pickup_weather", "midpoint_weather", "delivery_weather"):
            if body.get(field) not in {"RAIN", "CLOUDY", "CLEAR"}:
                return False

    if "weather_risk_in" in expected and body.get("weather_risk") not in expected["weather_risk_in"]:
        return False

    return True


def run_test_case(test: TestCase, token: str) -> TestResult:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    start = time.perf_counter()
    try:
        if test.send_raw_json:
            response = requests.post(
                PREDICT_URL,
                data=test.send_raw_json,
                headers=headers,
                timeout=PERF_THRESHOLD_MS / 1000 + 5,
            )
        else:
            response = requests.post(
                PREDICT_URL,
                json=test.payload,
                headers=headers,
                timeout=PERF_THRESHOLD_MS / 1000 + 5,
            )
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return TestResult(
            test_id=test.test_id,
            category=test.category,
            payload_summary=payload_summary(test),
            expected_summary=summarize_expected(test.expected),
            actual_summary=f"ERROR: {exc}",
            status="FAIL",
            response_ms=elapsed_ms,
            perf_status="PASS" if elapsed_ms < PERF_THRESHOLD_MS else "FAIL",
            functional_pass=False,
            perf_pass=elapsed_ms < PERF_THRESHOLD_MS,
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    try:
        body = response.json()
    except ValueError:
        body = response.text

    functional_ok = evaluate_response(body, test.expected, response.status_code)
    perf_ok = elapsed_ms < PERF_THRESHOLD_MS

    return TestResult(
        test_id=test.test_id,
        category=test.category,
        payload_summary=payload_summary(test),
        expected_summary=summarize_expected(test.expected),
        actual_summary=summarize_response(response.status_code, body),
        status="PASS" if functional_ok else "FAIL",
        response_ms=elapsed_ms,
        perf_status="PASS" if perf_ok else "FAIL",
        functional_pass=functional_ok,
        perf_pass=perf_ok,
        raw_response=body,
    )


def print_table(headers: list[str], rows: list[list[str]], widths: list[int]) -> None:
    def fmt_row(row: list[str]) -> str:
        return "".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    separator = "-" * sum(widths)
    print(fmt_row(headers))
    print(separator)
    for row in rows:
        print(fmt_row(row))
    print(separator)


def print_results_table(results: list[TestResult]) -> None:
    rows = [
        [
            r.test_id,
            r.payload_summary,
            r.expected_summary,
            r.actual_summary,
            r.status,
            f"{r.response_ms:.0f}",
            r.perf_status,
        ]
        for r in results
    ]

    print("\n=== TEST RESULTS ===\n")
    print_table(
        ["Test ID", "Input Payload", "Expected Result", "Actual Response", "Status", "Time(ms)", "Perf"],
        rows,
        widths=[8, 42, 46, 46, 8, 10, 6],
    )


def print_category_summary(results: list[TestResult]) -> None:
    categories: dict[str, list[TestResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    rows = []
    total_all = passed_all = 0
    for category in sorted(categories):
        items = categories[category]
        total = len(items)
        passed = sum(1 for r in items if r.functional_pass)
        failed = total - passed
        rate = (passed / total * 100) if total else 0.0
        rows.append([category, str(total), str(passed), str(failed), f"{rate:.1f}%"])
        total_all += total
        passed_all += passed

    overall_rate = (passed_all / total_all * 100) if total_all else 0.0
    rows.append(
        ["OVERALL", str(total_all), str(passed_all), str(total_all - passed_all), f"{overall_rate:.1f}%"]
    )

    print("\n=== SUMMARY BY CATEGORY ===\n")
    print_table(
        ["Category", "Total", "Passed", "Failed", "Pass Rate"],
        rows,
        widths=[24, 8, 8, 8, 12],
    )


def print_performance_summary(results: list[TestResult]) -> None:
    times = [r.response_ms for r in results]
    avg_ms = sum(times) / len(times) if times else 0
    perf_passed = sum(1 for r in results if r.perf_pass)

    print("\n=== PERFORMANCE SUMMARY ===\n")
    print(f"  Threshold (< {PERF_THRESHOLD_MS} ms) : PASS/FAIL per test above")
    print(f"  Average response time               : {avg_ms:.1f} ms")
    print(f"  Min response time                   : {min(times):.1f} ms")
    print(f"  Max response time                   : {max(times):.1f} ms")
    print(f"  Performance PASS                    : {perf_passed}/{len(results)}")


def check_server_reachable() -> bool:
    try:
        response = requests.get(BASE_URL, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def main() -> int:
    print("=" * 72)
    print("  DELIVERY PREDICTION API — SYSTEM TEST SUITE")
    print("=" * 72)
    print(f"  Target : {PREDICT_URL}")
    print(f"  Cases  : {len(TEST_CASES)}")
    print(f"  Perf   : PASS if response < {PERF_THRESHOLD_MS} ms")
    print()

    if not check_server_reachable():
        print("ERROR: API server is not reachable at", BASE_URL)
        print("Start it with: uvicorn app.main:app --reload")
        return 1

    try:
        token = login()
        print(f"  Auth   : OK (user={USERNAME})")
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("\nRunning tests...\n")
    results = [run_test_case(tc, token) for tc in TEST_CASES]

    print_results_table(results)
    print_category_summary(results)
    print_performance_summary(results)

    total = len(results)
    passed = sum(1 for r in results if r.functional_pass)
    failed = total - passed
    pass_rate = passed / total * 100 if total else 0

    print("\n=== OVERALL FUNCTIONAL RESULT ===\n")
    print(f"  Total test cases : {total}")
    print(f"  Passed           : {passed}")
    print(f"  Failed           : {failed}")
    print(f"  Pass rate        : {pass_rate:.1f}%")
    print()

    if failed:
        print("Failed tests:")
        for r in results:
            if not r.functional_pass:
                print(f"  - {r.test_id}: expected={r.expected_summary}, actual={r.actual_summary}")
        return 1

    print("All functional tests PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
