# 01: Enforce the 15-minute gap for room bookings

Status: ready-for-agent

Blocked by: None (can start immediately)

**What to build:** A user can reserve a room when the requested interval leaves at least 15 minutes between it and every active booking of that room. The cutoff applies in either booking order and across owners.

- [ ] Given a room booked from 10:00 to 11:00, reject an overlap, an 11:00 start, and an 11:14:59 start. In independent cases, accept an 11:15 start and a later start. Verify the same outcomes when the later interval is booked first. Apply the cutoff across midnight as well.
- [ ] Given bookings from 10:00 to 11:00 and 12:00 to 13:00 in one room, accept 11:15–11:45. In independent cases, reject 11:14–11:45 and 11:15–11:46.
- [ ] Accept the same time interval in different rooms. On a single device, accept adjacent bookings and reject overlapping bookings.
- [ ] Exercise booking creation through the HTTP API with sequential requests. Assert each response status and body. Success returns `201 Created` with the requested times. Both overlaps and insufficient gaps return `409 Conflict` with detail `Resource is already booked for this interval`.
- [ ] After each request, use `GET /bookings` to verify the visible records. A successful request adds exactly its confirmed booking. After a rejection, the list contains exactly the records visible before the request.
- [ ] Update the booking API description and user-facing examples to show the exact room cutoff, back-to-back device bookings, and the limitation for simultaneous submissions.
