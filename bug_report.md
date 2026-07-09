# Bug Report

---

## Bug 1

### Title

Concurrent cancellation creates duplicate refunds

### File

app/routers/bookings.py — `cancel_booking`

### Business Rule

Rule 6 – Cancellation Refund Policy

### Root Cause

`cancel_booking()` loaded the `Booking` ORM object **before** acquiring `_booking_lock`. Each concurrent request owned its own SQLAlchemy Session. Request B loaded its booking object while Request A's transaction was still in-flight, so B saw `booking.status == "confirmed"`. After A committed (with a refund and status change), B entered the lock but held a stale ORM object whose `status` was still `"confirmed"`. B then proceeded to create a second `RefundLog` entry and return HTTP 200, violating the requirement for exactly one refund.

### Fix

`db.refresh(booking)` is called immediately after acquiring the lock, before checking `booking.status`. This forces a fresh SELECT from the database, ensuring the cancellation logic always operates on the latest committed state. If another request already cancelled the booking, the refreshed status will be `"cancelled"` and `409 ALREADY_CANCELLED` is raised.

### Result

- Exactly one `RefundLog` per booking
- Concurrent cancellations return `409 ALREADY_CANCELLED`
- Rule 6 satisfied

---

## Bug 2

### Title

Usage report cache not invalidated after booking creation

### File

app/routers/bookings.py — `create_booking`

### Business Rule

Rule 12 – Usage Report

### Root Cause

Booking creation invalidated the availability cache (`cache.invalidate_availability(...)`) after a successful commit, but did **not** invalidate the report cache (`cache.invalidate_report(...)`). The cached result served by `GET /admin/usage-report` therefore remained stale until TTL expiry or a cancellation.

### Fix

Added `cache.invalidate_report(room.org_id)` after the booking commit, alongside the existing `cache.invalidate_availability(...)` call. The invalidation uses the room's organization ID — the same key the report cache is partitioned by.

### Result

Usage reports immediately reflect newly created bookings after a successful commit.

---

## Summary

| # | File | Function | Lines Changed | Rule |
|---|------|----------|---------------|------|
| 1 | `app/routers/bookings.py` | `cancel_booking` | +1 (add `db.refresh(booking)`) | #6 |
| 2 | `app/routers/bookings.py` | `create_booking` | +1 (add `cache.invalidate_report(...)`) | #12 |

**Total: 2 lines added. No lines removed. No other files modified.**
