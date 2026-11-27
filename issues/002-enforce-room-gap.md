# 002 · Enforce the 15-minute room gap

**Status** · Open · [Parent spec 001](001-room-booking-gap.md)

Update the conflict check in `create_booking` in `booking/main.py` and cover it through `POST /bookings` in `tests/test_bookings.py`.

## Acceptance criteria

For the boundary cases, fix the clock at 08:00 and start each case with Room A booked from 10:00 to 11:00 that day. All requests are otherwise valid.

- [ ] A request ending at 09:45 or starting at 11:15 returns 201. A request ending at 09:46 or starting at 11:14 returns 409.
- [ ] Back-to-back and overlapping room bookings return 409. The same rule applies to requests by the existing booking's owner and by another user.
- [ ] The request must clear every uncancelled booking in the room. With Room A also booked from 12:00 to 13:00, an 11:15–11:46 request returns 409. An 11:15–11:45 request returns 201.
- [ ] For compatibility, both overlaps and short room gaps return HTTP 409 with the existing detail `Resource is already booked for this interval`. After rejection, `GET /bookings` returns the same records and values as before the request.
- [ ] Apply this check only on creation, including when an existing confirmation predates the rule. Honour all existing confirmations. The guarantee covers sequential requests.
