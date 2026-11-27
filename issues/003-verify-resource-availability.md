# 003 · Verify cancellations, other rooms, and devices

**Status** · Implemented · [Parent spec 001](001-room-booking-gap.md) · Depends on [ticket 002](002-enforce-room-gap.md)

Add API regression cases to `tests/test_bookings.py` and `tests/test_cancellation.py` using otherwise valid future requests.

## Acceptance criteria

- [x] With Room A booked from 10:00 to 11:00, booking Room B from 10:00 to 11:00 returns 201.
- [x] With Room A booked from 10:00 to 11:00, an 11:00–12:00 request for Room A returns 409. After the owner cancels the first booking, retrying the same request returns 201. The booking list contains the cancelled original and the new active booking.
- [x] With a camera booked from 10:00 to 11:00, a 10:59–12:00 request for that camera returns 409 and leaves the original as its only booking. An 11:00–12:00 request for the same camera returns 201.
- [x] Open a database with two existing room confirmations less than 15 minutes apart. Both remain active and retain their original times. A new request too close to either returns the compatible 409 response. A request with sufficient clearance succeeds.
