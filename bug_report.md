# Bug Report — CoWork Multi-Tenant Coworking Space Booking API

---

## Bug #1 — Start Time Grace Window

- **File:** `app/routers/bookings.py` line 65
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #2 — "start_time must be strictly in the future at request time — no grace window of any size"

**What the bug is:**

```python
if start <= now - timedelta(seconds=300):
```

The code allows `start_time` to be up to 300 seconds (5 minutes) in the past. The spec explicitly says "no grace window of any size."

**How to fix:** Change to `if start <= now:`

**✅ Fixed:** Changed `if start <= now - timedelta(seconds=300):` to `if start <= now:` in `create_booking`. This ensures no grace window — any start_time that is <= current time is rejected.

---

## Bug #2 — Missing Minimum Duration Check (< 1 hour)

- **File:** `app/routers/bookings.py` lines 71–75
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #2 — "Duration must be a whole number of hours, minimum 1"

**What the bug is:**

```python
if duration_hours > MAX_DURATION_HOURS:
    raise AppError(400, "INVALID_BOOKING_WINDOW", "duration out of range")
```

There is a check for maximum duration (8 hours) but **no check for minimum duration (1 hour)**. A 0-hour booking (start == end) or zero-duration would pass validation.

**How to fix:** Add `if duration_hours < MIN_DURATION_HOURS: raise AppError(...)`

**✅ Fixed:** Added `if duration_hours < MIN_DURATION_HOURS: raise AppError(400, "INVALID_BOOKING_WINDOW", "duration out of range")` right after the whole-number-of-hours check. Uses the already-defined `MIN_DURATION_HOURS = 1` constant.

---

## Bug #3 — Missing end_time > start_time Validation

- **File:** `app/routers/bookings.py` lines 67–75
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #2 — "end_time must be strictly after start_time"

**What the bug is:**
There is no explicit check that `end_time > start_time`. If a client sends `end_time` before `start_time`, the duration calculation yields a negative number of hours. A negative whole number (e.g., -2.0) passes the "whole number of hours" check, and then `-2 > 8` is False, so validation passes. This could create a booking with negative price.

**How to fix:** Add `if end <= start: raise AppError(400, "INVALID_BOOKING_WINDOW", "end_time must be after start_time")`

**✅ Fixed:** Added `if end <= start:` check immediately after the grace-window check and _before_ the duration calculation, so negative durations are caught early.

---

## Bug #4 — Booking List Sorted Descending Instead of Ascending

- **File:** `app/routers/bookings.py` line 99
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #11 — "Items are sorted by ascending start_time"

**What the bug is:**

```python
base.order_by(Booking.start_time.desc(), Booking.id.asc())
```

The list is sorted by `start_time DESC` (most recent first), but the spec requires ascending order (earliest first).

**How to fix:** Change `.desc()` to `.asc()`

**✅ Fixed:** Changed `Booking.start_time.desc()` to `Booking.start_time.asc()` in `list_bookings`.

---

## Bug #5 — Pagination Offset Wrong (`page * limit`)

- **File:** `app/routers/bookings.py` line 100
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #11 — "Page N with limit L returns items [(N−1)·L, N·L) of that ordering; sequential pages never skip or repeat items"

**What the bug is:**

```python
.offset(page * limit)
```

With `page=1` and `limit=10`, offset = 10, which skips the first 10 results. The correct formula is `(page - 1) * limit`.

**How to fix:** Change to `.offset((page - 1) * limit)`

**✅ Fixed:** Changed `.offset(page * limit)` to `.offset((page - 1) * limit)`. Page 1 now correctly offsets by 0.

---

## Bug #6 — Hardcoded limit(10) Instead of Using limit Parameter

- **File:** `app/routers/bookings.py` line 101
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #11 — "limit (int 1–100, default 10)"

**What the bug is:**

```python
.limit(10)
```

The query uses a hardcoded value of `10` instead of the `limit` parameter passed by the client. A client requesting `limit=5` would still receive 10 items.

**How to fix:** Change to `.limit(limit)`

**✅ Fixed:** Changed `.limit(10)` to `.limit(limit)`. The client-requested `limit` parameter is now properly used.

---

## Bug #7 — get_booking Overwrites start_time with created_at

- **File:** `app/routers/bookings.py` line 117
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #2 (data integrity) — The response must contain the correct booking start_time

**What the bug is:**

```python
response = serialize_booking(booking)
response["start_time"] = iso_utc(booking.created_at)
```

After serializing the booking (which correctly sets `start_time`), the code **overwrites** `start_time` with `created_at`. The response always shows the creation timestamp instead of the actual booking start time.

**How to fix:** Remove the line `response["start_time"] = iso_utc(booking.created_at)` — it already has the correct start_time from `serialize_booking`.

**✅ Fixed:** Removed the line `response["start_time"] = iso_utc(booking.created_at)` from `get_booking`. The serialized response already has the correct `start_time`.

---

## Bug #8 — Cancel Refund: < 24 Hours Gives 50% Instead of 0%

- **File:** `app/routers/bookings.py` lines 120–121
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #6 — "notice < 24 hours → 0% refund"

**What the bug is:**

```python
else:
    refund_percent = 50
```

When notice is less than 24 hours, the code assigns a 50% refund. The spec says 0% refund.

**How to fix:** Change `refund_percent = 50` to `refund_percent = 0`

**✅ Fixed:** Changed `else: refund_percent = 50` to `else: refund_percent = 0` in `cancel_booking`. Also changed the middle condition from `notice >= timedelta(hours=24)` to `notice_hours >= 24` for consistency.

---

## Bug #9 — Cancel Refund: ≥ 48 Hours Uses `>` Instead of `>=`

- **File:** `app/routers/bookings.py` line 118
- **Difficulty:** Easy (3 pts)
- **Rule Violated:** Rule #6 — "notice ≥ 48 hours → 100% refund"

**What the bug is:**

```python
if notice_hours > 48:
    refund_percent = 100
```

Exactly 48 hours of notice should qualify for 100% refund, but the strict `>` excludes it.

**How to fix:** Change to `if notice_hours >= 48:`

**✅ Fixed:** Changed `if notice_hours > 48:` to `if notice_hours >= 48:` in `cancel_booking`. Exactly 48 hours of notice now qualifies for a 100% refund.

---

## Bug #10 — Double-Booking Overlap Uses `<=` Instead of `<`

- **File:** `app/routers/bookings.py` line 47
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #3 — "Two confirmed bookings for the same room overlap iff existing.start_time < new.end_time AND new.start_time < existing.end_time. Back-to-back bookings are allowed."

**What the bug is:**

```python
if b.start_time <= end and start <= b.end_time:
```

Using `<=` instead of `<` on both comparisons means back-to-back bookings (one ending exactly when the next starts) are incorrectly flagged as conflicts. The spec explicitly states back-to-back bookings are allowed.

**How to fix:** Change both `<=` to `<`: `if b.start_time < end and start < b.end_time:`

**✅ Fixed:** Changed both `<=` to `<` in `_has_conflict`. Back-to-back bookings (one ending exactly when the next starts) are now correctly allowed.

---

## Bug #11 — Token Revocation Checks `sub` Instead of `jti`

- **File:** `app/auth.py` line 72
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #8 — "Logout immediately invalidates the presented access token for all further use" and "Refresh tokens are single-use"

**What the bug is:**

```python
if payload.get("sub") in _revoked_tokens:
```

The `_revoked_tokens` set stores **JTI** values (from `revoke_access_token` which does `_revoked_tokens.add(payload["jti"])`), but the check looks up **`sub`** (user ID). Since user IDs are never stored in `_revoked_tokens`, the revocation check always returns False, meaning revoked tokens can still be used.

**How to fix:** Change `payload.get("sub")` to `payload.get("jti")`

**✅ Fixed:** Changed `payload.get("sub")` to `payload.get("jti")` in `get_token_payload` in `auth.py`. Now the revoked-tokens set lookup correctly finds JTIs.

---

## Bug #12 — Access Token Lifetime Wrong (900 Minutes Instead of 900 Seconds)

- **File:** `app/auth.py` line 40
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #8 — "Access tokens: exp − iat = exactly 900 seconds"

**What the bug is:**

```python
lifetime = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
```

`ACCESS_TOKEN_EXPIRE_MINUTES = 15`, so the lifetime is `timedelta(minutes=900)` = 900 minutes = 15 hours. The spec requires exactly 900 seconds (15 minutes). The variable name already says "MINUTES" but the code multiplies by 60, effectively treating it as hours.

**How to fix:** Change to `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)` (or `timedelta(seconds=900)`)

**✅ Fixed:** Changed `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)` to `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)`. Access tokens now last 15 minutes (900 seconds) as specified.

---

## Bug #13 — get_booking Allows Members to See Any Organization Booking

- **File:** `app/routers/bookings.py` lines 109–114
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #10 — "Members may read and cancel only their own bookings (another member's booking id → 404 BOOKING_NOT_FOUND)"

**What the bug is:**

```python
booking = (
    db.query(Booking)
    .join(Room, Booking.room_id == Room.id)
    .filter(Booking.id == booking_id, Room.org_id == user.org_id)
    .first()
)
```

The query only filters by `org_id`. A member can view any booking in their organization, including bookings belonging to other members. The spec says members should only see their own bookings.

**How to fix:** Add a filter for non-admin users: if `user.role != "admin"`, also filter `Booking.user_id == user.id`

**✅ Fixed:** Added `if user.role != "admin" and booking.user_id != user.id: raise AppError(404, ...)` check in `get_booking`. Members now get 404 BOOKING_NOT_FOUND when trying to view another member's booking.

---

## Bug #14 — Registration Returns 201 with Existing User Data Instead of 409 USERNAME_TAKEN

- **File:** `app/routers/auth.py` lines 28-36
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #15 — "A duplicate username within the org → 409 USERNAME_TAKEN"

**What the bug is:**

```python
existing = (
    db.query(User)
    .filter(User.org_id == org.id, User.username == payload.username)
    .first()
)
if existing is not None:
    return {
        "user_id": existing.id,
        "org_id": org.id,
        "username": existing.username,
        "role": existing.role,
    }
```

When a username already exists within the org, the endpoint returns a 201 response (default status) with the existing user's data. The spec says it should return `409 USERNAME_TAKEN`.

**How to fix:** Add `raise AppError(409, "USERNAME_TAKEN", "Username already taken")` instead of returning the existing user data.

**✅ Fixed:** Replaced the `return {...}` of existing user data with `raise AppError(409, "USERNAME_TAKEN", "Username already taken in this organization")` in the register endpoint.

---

## Bug #15 — parse_input_datetime Strips Timezone Instead of Converting to UTC

- **File:** `app/timeutils.py` lines 24-30
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #1 — "Input datetimes carrying a UTC offset are converted to UTC before storage or comparison"

**What the bug is:**

```python
def parse_input_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)  # ❌ Just strips offset, doesn't convert
    return dt
```

When an input carries a UTC offset (e.g. `+05:00`), the code simply removes the timezone info without converting the wall-clock time to UTC. For example, `2024-01-01T10:00:00+05:00` is stored as `2024-01-01T10:00:00` UTC instead of `2024-01-01T05:00:00` UTC. This means the time is 5 hours off, potentially validating against the wrong time window.

**How to fix:** Change to `dt = dt.astimezone(timezone.utc).replace(tzinfo=None)`

**✅ Fixed:** Changed `dt.replace(tzinfo=None)` to `dt.astimezone(timezone.utc).replace(tzinfo=None)` in `parse_input_datetime`. Datetimes with UTC offsets are now properly converted to UTC before storage.

---

## Bug #16 — Refresh Token Not Invalidated After Use (Missing Single-Use Enforcement)

- **File:** `app/routers/auth.py` lines 58-69
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #8 — "Refresh tokens are single-use: POST /auth/refresh ... invalidates the presented refresh token (reuse → 401)"

**What the bug is:**

```python
@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise AppError(401, "UNAUTHORIZED", "Wrong token type")
    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if user is None:
        raise AppError(401, "UNAUTHORIZED", "Unknown user")
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "token_type": "bearer",
    }
```

The endpoint never stores or checks invalidated refresh token JTIs. A refresh token can be replayed any number of times. Every call returns new tokens without invalidating the presented one.

**How to fix:** After successfully using a refresh token, add its JTI to `_revoked_tokens` (or a separate storage), and check it before issuing new tokens.

**✅ Fixed:** The refresh endpoint now: 1) Checks if the refresh token's JTI is in `_revoked_tokens` before proceeding (reuse → 401), and 2) Calls `revoke_access_token(data)` after issuing new tokens to invalidate the old refresh token. Import added for `_revoked_tokens`.

---

## Bug #17 — Admin Cannot See All Org Bookings via GET /bookings

- **File:** `app/routers/bookings.py` line 96
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #10 — "Admins may read ... any booking in their org"

**What the bug is:**

```python
base = db.query(Booking).filter(Booking.user_id == user.id)
```

The list query filters by `user_id` unconditionally, so admins can only see their own bookings. The spec says admins should be able to see all bookings in their org. (Members should still see only their own.)

**How to fix:** Add a conditional: if `user.role != "admin"`, filter by `user_id`; otherwise filter by org via a Room join.

**✅ Fixed:** In `list_bookings`, added a conditional query: admins query via a Room join filtered by `org_id` to see all bookings in their org; members continue to filter by `user_id` to see only their own bookings.

---

## Bug #18 — Admin Export Can Leak Cross-Org Booking Data

- **File:** `app/services/export.py` lines 28-33 (`fetch_bookings_raw`)
- **Difficulty:** Hard (7 pts)
- **Rule Violated:** Rule #9 — Multi-tenancy: a user may only read data belonging to their own organization

**What the bug is:**

```python
def fetch_bookings_raw(db: Session, room_id: int) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.room_id == room_id)
        .order_by(Booking.id.asc())
        .all()
    )
```

When `GET /admin/export?room_id=X&include_all=true` is called, the `fetch_bookings_raw` function fetches all bookings for the given room_id **without joining with the Room table to verify organization ownership**. An admin could guess a room_id from another org and leak that org's booking data.

**How to fix:** Always apply an org filter by joining through the Room table, or filter in `generate_export` after the org check.

**✅ Fixed:** Modified `fetch_bookings_raw` to join with Room and filter by `org_id`. Updated the function signature to accept `org_id` and updated the caller in `generate_export` to pass it.

---

## Bug #19 — Refund Amount Calculation Truncates Instead of Rounding to Nearest Cent (Half Up)

- **File:** `app/services/refunds.py` lines 21-24
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #6 — "Refund amount = percentage of price_cents, rounded to the nearest cent with half-cents rounding up (e.g. 50% of 1001 = 501)"

**What the bug is:**

```python
def log_refund(db: Session, booking: Booking, percent: int) -> RefundLog:
    dollars = booking.price_cents / 100.0
    refund_dollars = dollars * (percent / 100.0)
    amount_cents = int(refund_dollars * 100)  # ❌ Truncates instead of rounding
```

The code converts to dollars, calculates refund, then converts back to cents with `int()`, which truncates. For 50% of 1001 cents: `int(5.005 * 100) = int(500.5) = 500`, but the spec says it should be `501` (rounded half up).

**How to fix:** Use a proper "round half up" calculation on cents directly: `amount_cents = (booking.price_cents * percent + 50) // 100`

**✅ Fixed:** Replaced the dollars-based truncation (`int(refund_dollars * 100)`) with direct cents calculation: `(booking.price_cents * percent + 50) // 100`. This correctly rounds half-cents up (e.g. 50% of 1001 = 501).

**Additional fix:** In `cancel_booking`, the response `refund_amount_cents` was previously calculated separately with Python's `round()` (banker's rounding), which could differ from the corrected `log_refund` calculation. Now the cancel endpoint captures the `RefundLog` entry from `log_refund()` and uses its `amount_cents`, ensuring the response amount always matches the stored RefundLog amount (as required by Rule #6).

---

## Bug #20 — Reference Code Generation Not Thread-Safe (Duplicate Codes Under Concurrency)

- **File:** `app/services/reference.py` lines 18-23
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #7 — "Every booking's reference_code is unique, including under concurrent creation."

**What the bug is:**

```python
def next_reference_code() -> str:
    current = _counter["value"]
    _format_pause()
    _counter["value"] = current + 1
    return f"CW-{current:06d}"
```

The counter read (`current = _counter["value"]`) and write (`_counter["value"] = current + 1`) are not atomic. Under concurrent booking creation, two threads could read the same counter value and generate identical reference codes. The `_format_pause()` sleep makes the race window even larger.

**How to fix:** Use a `threading.Lock` to protect the read-increment-write sequence.

**✅ Fixed:** Added `import threading` and a `_lock = threading.Lock()`. The entire read-increment-return sequence in `next_reference_code` is now wrapped in `with _lock:`.

---

## Bug #21 — Potential Deadlock in Notification Lock Ordering

- **File:** `app/services/notifications.py` lines 29-41
- **Difficulty:** Hard (7 pts)
- **Rule Violated:** Rule #16 — "No combination of concurrent valid requests may hang the service"

**What the bug is:**

```python
def notify_created(booking) -> None:
    with _email_lock:          # Acquires email_lock FIRST
        _send_email("created", booking)
        with _audit_lock:      # Then audit_lock
            _write_audit("created", booking)

def notify_cancelled(booking) -> None:
    with _audit_lock:          # Acquires audit_lock FIRST
        _write_audit("cancelled", booking)
        with _email_lock:      # Then email_lock
            _send_email("cancelled", booking)
```

The two notification functions acquire locks in opposite order. If `notify_created` holds `_email_lock` while `notify_cancelled` holds `_audit_lock`, both will wait for the other indefinitely → classic deadlock.

**How to fix:** Use consistent lock ordering (e.g., always acquire `_email_lock` before `_audit_lock`).

**✅ Fixed:** Reordered the lock acquisition in `notify_cancelled` to match `notify_created`: now acquires `_email_lock` first, then `_audit_lock`. Both notification functions now use consistent lock ordering, eliminating the deadlock risk.

---

## Bug #22 — Availability Query Misses Overnight Bookings

- **File:** `app/routers/rooms.py` (availability endpoint)
- **Difficulty:** Medium (5 pts)
- **Rule Violated:** Rule #3 — Availability must accurately reflect whether a room is busy for any given day

**What the bug is:**

```python
bookings = (
    db.query(Booking)
    .filter(
        Booking.room_id == room.id,
        Booking.status == "confirmed",
        Booking.start_time >= day_start,
        Booking.start_time < day_end,  # ❌ Only checks start_time
    )
    ...
)
```

The availability query only finds bookings that **start** on the given date. If a booking runs from 22:00 on Day 1 to 02:00 on Day 2 (a valid booking under the existing validation), querying availability for Day 2 would show the room as **available** from 00:00–02:00 when it's actually occupied.

**How to fix:** Use the standard interval-overlap formula: two intervals [A, B) and [C, D) overlap iff `A < D AND C < B`. Replace the `start_time`-only filter with:

```python
Booking.start_time < day_end,
Booking.end_time > day_start,
```

**✅ Fixed:** Changed from `Booking.start_time >= day_start, Booking.start_time < day_end` to `Booking.start_time < day_end, Booking.end_time > day_start` in the availability endpoint. Multi-day bookings that span across midnight are now correctly shown as busy on every overlapping day.

---

## Previously Unfixed Items (Now Resolved)

The following issues were listed as "unfixed" in earlier versions but have since been addressed:

- **Availability cache not invalidated on cancel** — ✅ Fixed: `cache.invalidate_availability(...)` is called in `cancel_booking` after setting status to cancelled.
- **Room stats drift from DB** — ✅ Fixed: `room_stats` endpoint now computes `total_confirmed_bookings` / `total_revenue_cents` live via DB queries (`func.count` / `func.sum`).
- **Rate limiter race condition** — ✅ Fixed: The trim-append-check sequence in `record_and_check` is now wrapped in `threading.Lock()`.
- **Double-booking race condition** — ✅ Fixed: Conflict check + quota check + insert in `create_booking` is wrapped in `_booking_lock`.
- **Double-cancel race condition** — ✅ Fixed: Status check + update in `cancel_booking` is wrapped in `_booking_lock` (same lock as creation).

Bug #23 — Concurrent Cancellation Creates Duplicate Refunds
File: app/routers/bookings.py — cancel_booking
Difficulty: Medium (5 pts)
Rule Violated: Rule #6 — Cancellation Refund Policy
What the bug is:

cancel_booking() loaded the Booking ORM object before acquiring \_booking_lock. Each concurrent request owned its own SQLAlchemy Session. Request B loaded its booking object while Request A's transaction was still in-flight, so B saw booking.status == "confirmed".

After Request A committed (creating a refund and changing the booking status), Request B entered the lock but still held a stale SQLAlchemy ORM object whose status remained "confirmed". It therefore proceeded to create a second RefundLog entry and returned HTTP 200, violating the requirement that a booking may only be refunded once.

How to fix:

Call:

db.refresh(booking)

immediately after acquiring \_booking_lock, before checking booking.status.

This forces SQLAlchemy to reload the latest committed state from the database before executing any cancellation logic.

✅ Fixed:

Added:

db.refresh(booking)

immediately after acquiring \_booking_lock in cancel_booking. If another request has already cancelled the booking, the refreshed object now contains status == "cancelled" and the endpoint correctly raises:

409 ALREADY_CANCELLED

instead of issuing another refund.

Result
Exactly one RefundLog per booking
Concurrent cancellations now return 409 ALREADY_CANCELLED
Rule #6 fully satisfied
Bug #24 — Usage Report Cache Not Invalidated After Booking Creation
File: app/routers/bookings.py — create_booking
Difficulty: Easy (3 pts)
Rule Violated: Rule #12 — Usage Report
What the bug is:

After successfully creating a booking, the endpoint invalidated the availability cache:

cache.invalidate_availability(...)

but did not invalidate the usage report cache.

As a result, responses from:

GET /admin/usage-report

continued serving stale cached data until either the cache TTL expired or a later cancellation invalidated the report cache.

How to fix:

After the booking commit, add:

cache.invalidate_report(room.org_id)

alongside the existing availability cache invalidation.

The report cache is partitioned by organization, so the invalidation must use the room's organization ID.

✅ Fixed:

Added:

cache.invalidate_report(room.org_id)

immediately after the successful booking commit and alongside:

cache.invalidate_availability(...)

This ensures usage reports are refreshed immediately whenever a new booking is created.

Result
Usage reports immediately reflect newly created bookings
Report cache remains consistent with booking data
Rule #12 satisfied
Updated Summary of All Known Bugs (24 total)

# File Rule Severity

1 app/routers/bookings.py:65 #2 — Grace window Easy (3)
2 app/routers/bookings.py:71-75 #2 — Missing min duration Easy (3)
3 app/routers/bookings.py:67-75 #2 — Missing end>start check Easy (3)
4 app/routers/bookings.py:99 #11 — Descending sort Easy (3)
5 app/routers/bookings.py:100 #11 — Wrong offset Easy (3)
6 app/routers/bookings.py:101 #11 — Hardcoded limit Easy (3)
7 app/routers/bookings.py:117 #2 — start_time overwritten Easy (3)
8 app/routers/bookings.py:120-121 #6 — <24h gives 50% Easy (3)
9 app/routers/bookings.py:118 #6 — ≥48h uses > Easy (3)
10 app/routers/bookings.py:47 #3 — ≤ instead of < Medium (5)
11 app/auth.py:72 #8 — sub vs jti Medium (5)
12 app/auth.py:40 #8 — 900 min vs 900 sec Medium (5)
13 app/routers/bookings.py:109-114 #10 — Member sees any booking Medium (5)
14 app/routers/auth.py:28-36 #15 — 201 instead of 409 Medium (5)
15 app/timeutils.py:24-30 #1 — tzinfo stripped w/o conversion Medium (5)
16 app/routers/auth.py:58-69 #8 — Refresh not invalidated Medium (5)
17 app/routers/bookings.py:96 #10 — Admin can't see all bookings Medium (5)
18 app/services/export.py:28-33 #9 — Cross-org data leak Hard (7)
19 app/services/refunds.py:21-24 #6 — Refund rounding wrong Medium (5)
20 app/services/reference.py:18-23 #7 — Race condition in codes Medium (5)
21 app/services/notifications.py:29-41 #16 — Deadlock risk Hard (7)
22 app/routers/rooms.py (availability) #3 — Overnight booking visibility Medium (5)
23 app/routers/bookings.py (cancel_booking) #6 — Concurrent cancellation creates duplicate refunds Medium (5)
24 app/routers/bookings.py (create_booking) #12 — Usage report cache not invalidated Easy (3)
