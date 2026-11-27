# 03: Honor room bookings confirmed before the rule took effect

Status: ready-for-agent

Blocked by: 01 — Enforce the 15-minute gap for room bookings

**What to build:** Users keep their existing room confirmations when the rule takes effect, even if two bookings are only five minutes apart. Each original booking enforces the full gap for new requests.

- [ ] Prepare an existing schedule through the pre-change booking HTTP API. Create two active bookings for the same room on a future date, 10:00–11:00 and 11:05–12:00. Verify both confirmations.
- [ ] Open that schedule with the updated service. Verify through `GET /bookings` that both original records match their confirmations, including IDs, owners, resource, times, and active status.
- [ ] In independent cases, reject a new booking ending at 09:46 and one starting at 12:14. Both return `409 Conflict` with detail `Resource is already booked for this interval`. Accept an otherwise valid booking ending at 09:45 or starting at 12:15 with `201 Created` and the requested times.
- [ ] Use the booking HTTP API as the single test boundary before and after the update. For each create request, assert the response status and body, then call `GET /bookings` to verify the full list. Both originals retain their confirmed details throughout, and only successful requests add records.
