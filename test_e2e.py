"""
Full booking lifecycle end-to-end test.
"""
import os
import sys
import uvicorn
import threading
import time
import requests
import sqlite3
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8123"

passed = 0
failed = 0


def start_server():
    def run():
        uvicorn.run("app.main:app", host="127.0.0.1", port=8123, log_level="error")

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(3)
    print("Server started")
    return t


def check(name, ok):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")


def ensure_user(org, username, password):
    """Register or login a user. Returns (user_info, tokens)."""
    r = requests.post(f"{BASE}/auth/register", json={"org_name": org, "username": username, "password": password}, timeout=5)
    if r.status_code == 201:
        print(f"  [SETUP] Registered new user {username}")
        user = r.json()
        r2 = requests.post(f"{BASE}/auth/login", json={"org_name": org, "username": username, "password": password}, timeout=5)
        return user, r2.json()
    elif r.status_code == 409:
        print(f"  [SETUP] User {username} already exists, logging in")
        r2 = requests.post(f"{BASE}/auth/login", json={"org_name": org, "username": username, "password": password}, timeout=5)
        # Fetch user info from DB
        db_path = "cowork.db"
        if not os.path.exists(db_path):
            db_path = "test.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.execute("SELECT id, role FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            conn.close()
            if row:
                return {"user_id": row[0], "role": row[1]}, r2.json()
        return {"user_id": 0, "role": "member"}, r2.json()
    else:
        print(f"  [SETUP] Unexpected status {r.status_code} for {username}: {r.json()}")
        return None, None


def main():
    global passed, failed
    start_server()

    # 1. Health
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        check("health", r.status_code == 200 and r.json() == {"status": "ok"})
    except Exception as e:
        print(f"Server not running: {e}")
        sys.exit(1)

    # 2. Ensure alice exists as admin
    alice, alice_tokens = ensure_user("acme", "alice", "pass123")
    check("alice registered/logged in", alice is not None and alice_tokens is not None)
    if alice is None:
        sys.exit(1)

    # 3. Ensure bob exists as member
    bob, bob_tokens = ensure_user("acme", "bob", "pass456")
    check("bob registered/logged in", bob is not None and bob_tokens is not None)

    # 4. Promote alice to admin if needed
    if alice.get("role") != "admin":
        db_path = "cowork.db" if os.path.exists("cowork.db") else "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (alice["user_id"],))
        conn.commit()
        conn.close()
        print("  [INFO] Promoted alice to admin via DB")
        _, alice_tokens = ensure_user("acme", "alice", "pass123")

    alice_h = {"Authorization": f"Bearer {alice_tokens['access_token']}"}
    bob_h = {"Authorization": f"Bearer {bob_tokens['access_token']}"}

    # 5. Create room
    r = requests.post(f"{BASE}/rooms", json={"name": "Conference A", "capacity": 10, "hourly_rate_cents": 2000}, headers=alice_h, timeout=5)
    check("create room", r.status_code == 201)
    room = r.json()
    room_id = room["id"]

    # 6. Availability
    tomorrow = datetime.utcnow() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y-%m-%d")
    r = requests.get(f"{BASE}/rooms/{room_id}/availability", params={"date": date_str}, headers=alice_h, timeout=5)
    check("availability", r.status_code == 200)

    # 7. Create booking (2 hours)
    start_iso = tomorrow.replace(hour=9, minute=0).isoformat()
    end_iso = tomorrow.replace(hour=11, minute=0).isoformat()
    r = requests.post(f"{BASE}/bookings", json={"room_id": room_id, "start_time": start_iso, "end_time": end_iso}, headers=alice_h, timeout=5)
    check("create booking", r.status_code == 201 and r.json().get("status") == "confirmed")
    booking = r.json()
    check("reference code starts with CW-", booking.get("reference_code", "").startswith("CW-"))
    check("price 4000c (2h x 2000c)", booking.get("price_cents") == 4000)

    # 8. List bookings
    r = requests.get(f"{BASE}/bookings", headers=alice_h, timeout=5)
    check("list bookings returns data", r.status_code == 200 and r.json().get("total", 0) >= 1)

    # 9. Get booking detail
    r = requests.get(f"{BASE}/bookings/{booking['id']}", headers=alice_h, timeout=5)
    get_ok = r.status_code == 200 and r.json().get("start_time") != r.json().get("created_at")
    check("get booking (start_time != created_at)", get_ok)

    # 10. Cancel booking (same day = 0% refund)
    r = requests.post(f"{BASE}/bookings/{booking['id']}/cancel", headers=alice_h, timeout=5)
    check("cancel (0% refund)", r.status_code == 200 and r.json().get("refund_percent") == 0 and r.json().get("refund_amount_cents") == 0)

    # 11. Double cancel (409)
    r = requests.post(f"{BASE}/bookings/{booking['id']}/cancel", headers=alice_h, timeout=5)
    print(f"    [DEBUG] double cancel: {r.status_code} {r.json()}")
    check("double cancel => 409", r.status_code == 409 and r.json().get("code") == "ALREADY_CANCELLED")

    # 12. Duplicate username (409)
    r = requests.post(f"{BASE}/auth/register", json={"org_name": "acme", "username": "alice", "password": "x"}, timeout=5)
    print(f"    [DEBUG] duplicate user: {r.status_code} {r.json()}")
    check("duplicate username => 409", r.status_code == 409 and r.json().get("code") == "USERNAME_TAKEN")

    # 13. Token refresh (single-use enforcement)
    r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": alice_tokens["refresh_token"]}, timeout=5)
    check("refresh token works", r.status_code == 200)
    r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": alice_tokens["refresh_token"]}, timeout=5)
    check("old refresh rejected => 401", r.status_code == 401)

    # 14. Back-to-back bookings (allowed)
    future_day = datetime.utcnow() + timedelta(days=2)
    s1 = future_day.replace(hour=9, minute=0).isoformat()
    e1 = future_day.replace(hour=11, minute=0).isoformat()
    s2 = future_day.replace(hour=11, minute=0).isoformat()
    e2 = future_day.replace(hour=13, minute=0).isoformat()
    r1 = requests.post(f"{BASE}/bookings", json={"room_id": room_id, "start_time": s1, "end_time": e1}, headers=alice_h, timeout=5)
    check("back-to-back booking 1", r1.status_code == 201)
    r2 = requests.post(f"{BASE}/bookings", json={"room_id": room_id, "start_time": s2, "end_time": e2}, headers=alice_h, timeout=5)
    check("back-to-back booking 2 (allowed)", r2.status_code == 201)

    # 15. Overlapping booking (409)
    ov_start = future_day.replace(hour=10, minute=30).isoformat()
    ov_end = future_day.replace(hour=12, minute=30).isoformat()
    r = requests.post(f"{BASE}/bookings", json={"room_id": room_id, "start_time": ov_start, "end_time": ov_end}, headers=alice_h, timeout=5)
    print(f"    [DEBUG] overlap: {r.status_code} {r.json()}")
    check("overlap => 409", r.status_code == 409 and r.json().get("code") == "ROOM_CONFLICT")

    # 16. Room stats (live from DB)
    r = requests.get(f"{BASE}/rooms/{room_id}/stats", headers=alice_h, timeout=5)
    check("room stats 200", r.status_code == 200)
    if r.status_code == 200:
        s = r.json()
        check("stats: 2 confirmed", s["total_confirmed_bookings"] == 2)
        check("stats: 8000 revenue", s["total_revenue_cents"] == 8000)

    # 17. 100% refund tier (>= 48h)
    d5 = datetime.utcnow() + timedelta(days=5)
    r = requests.post(f"{BASE}/bookings", json={"room_id": room_id, "start_time": d5.replace(hour=10).isoformat(), "end_time": d5.replace(hour=11).isoformat()}, headers=alice_h, timeout=5)
    if r.status_code == 201:
        b = r.json()
        r = requests.post(f"{BASE}/bookings/{b['id']}/cancel", headers=alice_h, timeout=5)
        check("100% refund (>= 48h)", r.status_code == 200 and r.json()["refund_percent"] == 100 and r.json()["refund_amount_cents"] == b["price_cents"])

    # 18. 50% refund tier (24-47h) with round-half-up
    mid = (datetime.utcnow() + timedelta(hours=30)).replace(minute=0, second=0)
    r = requests.post(f"{BASE}/bookings", json={"room_id": room_id, "start_time": mid.isoformat(), "end_time": mid.replace(hour=mid.hour+1).isoformat()}, headers=alice_h, timeout=5)
    if r.status_code == 201:
        b = r.json()
        expected = (b["price_cents"] * 50 + 50) // 100
        r = requests.post(f"{BASE}/bookings/{b['id']}/cancel", headers=alice_h, timeout=5)
        check("50% refund (round half up)", r.status_code == 200 and r.json()["refund_percent"] == 50 and r.json()["refund_amount_cents"] == expected)

    # 19. Member restrictions
    r = requests.get(f"{BASE}/bookings/{booking['id']}", headers=bob_h, timeout=5)
    check("member blocked from other's booking", r.status_code == 404)
    r = requests.get(f"{BASE}/bookings", headers=bob_h, timeout=5)
    check("member sees 0 own bookings", r.status_code == 200 and r.json()["total"] == 0)

    print()
    print("=" * 60)
    total = passed + failed
    print(f"  RESULTS: {passed}/{total} passed ({failed} failed)")
    if failed == 0:
        print("  ALL TESTS PASSED!")
    else:
        print(f"  {failed} test(s) FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
