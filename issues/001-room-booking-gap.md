# 001 · Require 15 minutes between bookings of the same room

**Status** · Agreed, awaiting implementation

When someone requests a room, Facilities requires at least 15 minutes between the end of the earlier booking and the start of the later one. Check every uncancelled booking for that room, regardless of who booked it or which request came first. Exactly 15 minutes is sufficient.

## Facilities decisions

- **Compatibility.** An overlap or a room gap under 15 minutes returns HTTP 409 with the existing detail `Resource is already booked for this interval`. Both the status and the wording are part of the API contract. Rejection preserves all stored bookings.
- **Existing confirmations.** Honour every existing confirmation, including two bookings less than 15 minutes apart. Apply the rule only when processing a new room booking. Check that request against every uncancelled booking of the same room, including confirmations made before the change.
- **Cancellation.** A successful cancellation immediately releases both the room slot and its spacing requirement. The cancelled record stays in the booking list.
- **Known limitation.** The guarantee applies to sequential requests. Simultaneous requests can both pass the availability check and receive confirmations.

## Acceptance examples

Assume Room A has one uncancelled booking from 10:00 to 11:00. Each row is a separate, otherwise valid request.

| Requested booking | Gap | Expected response |
| --- | --- | --- |
| Room A, 09:00–09:45 | 15 minutes before | 201 Created |
| Room A, 09:00–09:46 | 14 minutes before | 409 Conflict |
| Room A, 11:14–12:00 | 14 minutes after | 409 Conflict |
| Room A, 11:15–12:00 | 15 minutes after | 201 Created |
| Room A, 11:00–12:00 | Back-to-back | 409 Conflict |
| Room A, 10:30–11:30 | Overlap | 409 Conflict |
| Room B, 10:00–11:00 | Different room | 201 Created |

Cancelling the 10:00–11:00 booking releases both the slot and its spacing requirement. A new request for Room A from 11:00 to 12:00 then succeeds.

Devices allow back-to-back bookings and reject overlaps on the same device. With a camera booked from 10:00 to 11:00, a request for that camera from 11:00 to 12:00 succeeds. A request from 10:59 to 12:00 conflicts.

## Implementation tickets

- [002 · Enforce the 15-minute room gap](002-enforce-room-gap.md)
- [003 · Verify cancellations, other rooms, and devices](003-verify-resource-availability.md)
- [004 · Document the booking rules for rooms and devices](004-document-booking-rules.md)
