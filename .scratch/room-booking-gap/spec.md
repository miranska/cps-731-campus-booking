# Require a 15-minute gap between bookings of the same room

Status: ready-for-agent

Resolution: implemented

## Problem Statement

Facilities needs 15 minutes between uses of a room. Today, someone can book a room from 10:00 to 11:00 and another person can reserve it from 11:00 onward. Both receive confirmations, leaving Facilities no time between bookings.

## Solution

Require at least 15 minutes between active bookings of the same room. If a booking ends at 11:00, the next one may start at 11:15. The same cutoff applies when the later booking is made first. Each room has its own schedule. Devices continue to allow back-to-back bookings.

## User Stories

1. As a Facilities staff member, I want 15 minutes between active bookings of a room, so that I have time to prepare it for the next use.
2. As a room user, I want to book a room exactly 15 minutes after its previous booking ends, so that I can use the earliest available time.
3. As a room user, I want to book an earlier slot when a later slot is already confirmed, so that I can use the room up to 15 minutes before the next booking.
4. As a room user booking between two reservations, I want both gaps checked, so that my confirmation respects the users on either side.
5. As a user booking another room, I want its availability assessed independently, so that I can use it while Facilities prepares the first room.
6. As a camera user, I want to reserve a device from the moment its previous booking ends, so that consecutive users can arrange a handoff.
7. As a room user, I want a cancellation to release the room and its surrounding gap immediately, so that I can book a time that the cancelled reservation previously blocked.
8. As a user with a confirmed booking, I want to keep my reserved times when the rule takes effect, so that I can rely on my confirmation even if an older pair of bookings is less than 15 minutes apart.
9. As a Facilities staff member, I want new requests checked against those earlier confirmations, so that new bookings respect the gap from day one.
10. As a booking API client, I want overlaps and insufficient gaps to use the existing conflict response, so that my current error handling works for both.
11. As a user checking the booking list after a conflict, I want to see which reservations are still on the schedule, so that I can rely on my original confirmation.

## Implementation Decisions

- Apply the gap during booking creation when the requested resource has kind `room`. Compare against every uncancelled booking with the same resource ID, regardless of owner.
- Reject overlapping intervals. For disjoint room intervals, measure from the earlier end to the later start using the supplied timestamps. A gap shorter than 15 minutes is a conflict. Exactly 15 minutes is sufficient. Store and return the times the user requested.
- For devices, reject overlaps with active bookings of the same device and allow adjacent intervals. Bookings on different resource IDs are independent.
- Return `409 Conflict` with the existing detail `Resource is already booked for this interval` for overlaps and insufficient gaps. A rejected request creates no booking.
- A successful cancellation retains the cancelled record in the booking list and immediately releases its interval and surrounding gap. Every other active booking still constrains availability.
- Apply the rule to new requests. Honor the original times and status of existing bookings, including pairs already less than 15 minutes apart.
- Keep the starter’s sequential-request guarantee. Update the booking API description and user-facing examples to explain the room cutoff and device adjacency, and retain the documented limitation for simultaneous submissions.

## Testing Decisions

Use the existing booking HTTP API as the single test boundary. Create bookings through `POST /bookings` and cancel them through `POST /bookings/{booking_id}/cancel`. After each operation, assert its HTTP status and response body, then call `GET /bookings` and assert the records the client can see. The existing conflict test demonstrates this pattern for a rejected overlap. The cancellation-and-reuse test shows how to check a retained cancelled record alongside its replacement.

- **Room cutoff and booking order.** Start with a 10:00–11:00 booking. In independent cases, try a second booking that overlaps, starts at 11:00, starts at 11:14:59, starts at 11:15, or starts after 11:15. Expect the exact conflict response for the first three cases and `201 Created` for the last two. Repeat with the later interval booked first.
- **Bookings on either side.** With 10:00–11:00 and 12:00–13:00 confirmed for one room, accept 11:15–11:45. In independent cases, reject 11:14–11:45 and 11:15–11:46. After rejection the list contains just the two original records.
- **Resource scope.** Submit two requests in sequence for different rooms at the same time of day and accept both. For one camera, accept a back-to-back booking and reject an overlap. Verify the resource IDs and times in the list.
- **Cancellation.** With 10:00–11:00 and 12:00–13:00 confirmed, reject 11:05–11:45 in the same room. Cancel the first booking and retry successfully. Verify the cancelled record, the other active booking, and the new booking in the list. In a separate case, verify that the 12:00 booking still blocks a request ending at 11:46 after the cancellation.
- **Previously confirmed bookings.** Use a database containing two same-room bookings created through the pre-change HTTP API with a five-minute gap. Open it with the updated service and verify both original confirmations through `GET /bookings`. Submit new requests on either side of the pair to verify that each original booking constrains availability. Check the response and list after each request.

## Out of Scope

Guaranteeing a gap between simultaneous submissions would require a separate concurrency change. This feature covers requests processed one after another. Rescheduling previously confirmed bookings and introducing device turnaround times are also outside this change.

## Further Notes

A gap can cross midnight. For example, if a room booking ends at 23:55, the earliest start allowed by that booking is 00:10 the following day.
