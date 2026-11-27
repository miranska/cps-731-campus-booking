# 004 · Document the booking rules for rooms and devices

**Status** · Open · [Parent spec 001](001-room-booking-gap.md) · Depends on [ticket 002](002-enforce-room-gap.md)

Update the booking rules in `README.md` and the description of `POST /bookings` served in the interactive API docs.

## Acceptance criteria

- [ ] Both surfaces state that uncancelled bookings of the same room require a gap of at least 15 minutes in either direction. Both explain that same-device bookings may touch and that overlaps on the same device return 409.
- [ ] The README gives a concrete room example. For a 10:00–11:00 booking, an 11:14 start conflicts and an 11:15 start is allowed.
- [ ] The README explains that bookings in different rooms are independent and that cancelling a room booking releases its slot and the surrounding gap.
- [ ] Both surfaces explain that the rule applies on creation, honours existing confirmations, and keeps the existing HTTP 409 wording for compatibility.
- [ ] Both surfaces document simultaneous requests as a known limitation. Two requests can both be confirmed because availability is checked before insertion.
