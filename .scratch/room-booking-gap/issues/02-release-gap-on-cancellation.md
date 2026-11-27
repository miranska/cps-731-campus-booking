# 02: Release the gap when a room booking is cancelled

Status: ready-for-agent

Resolution: implemented

Blocked by: 01 — Enforce the 15-minute gap for room bookings

**What to build:** Cancelling a room booking immediately releases its slot and surrounding gap. The user can still see the cancelled record, and each remaining active booking continues to constrain availability.

- [x] Through the HTTP API, book the same room from 10:00 to 11:00 and from 12:00 to 13:00. Request 11:05–11:45 and verify `409 Conflict` with detail `Resource is already booked for this interval`.
- [x] Cancel the 10:00 booking as its owner. Verify `200 OK` and the original record marked as cancelled. Immediately retry 11:05–11:45 and verify `201 Created` with the requested times.
- [x] In a separate case with the same cancellation, request 11:05–11:46. Verify the same conflict response because the active 12:00 booking still needs a 15-minute gap.
- [x] Use the booking HTTP API as the single test boundary. After each create or cancel request, assert the response status and body, then use `GET /bookings` to verify the complete list. After the successful retry it contains the cancelled original, the active noon booking, and the newly confirmed booking. A rejected request adds no record.

## Comments

Verified in `9148992`. After the owner cancels the morning booking, the API accepts 11:05–11:45 and still rejects an 11:46 end because of the noon booking. Both cases verify the full booking list.
