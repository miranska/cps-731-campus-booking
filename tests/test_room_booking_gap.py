import pytest
from booking_assertions import assert_booking_request
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "later_first", [False, True], ids=["earlier-first", "later-first"]
)
@pytest.mark.parametrize(
    "later_start,status",
    [
        ("10:59:59", 409),
        ("11:00:00", 409),
        ("11:14:59", 409),
        ("11:14:59.999999", 409),
        ("11:15:00", 201),
        ("11:15:01", 201),
    ],
)
def test_room_booking_cutoff(
    client: TestClient, later_start: str, status: int, later_first: bool
) -> None:
    bookings = []
    earlier = ("2030-01-15T10:00:00", "2030-01-15T11:00:00")
    later = (f"2030-01-15T{later_start}", "2030-01-15T12:00:00")
    first, second = (later, earlier) if later_first else (earlier, later)
    assert_booking_request(client, bookings, *first, owner_id=1)
    assert_booking_request(client, bookings, *second, owner_id=2, status=status)


def test_room_booking_can_end_at_latest_timestamp(client: TestClient) -> None:
    bookings = []
    assert_booking_request(
        client,
        bookings,
        "9999-12-31T23:45:00",
        "9999-12-31T23:59:59.999999",
        owner_id=1,
    )


@pytest.mark.parametrize("next_start,status", [("00:09:59", 409), ("00:10:00", 201)])
def test_room_booking_gap_crosses_midnight(
    client: TestClient, next_start: str, status: int
) -> None:
    bookings = []
    assert_booking_request(
        client, bookings, "2030-01-15T22:55:00", "2030-01-15T23:55:00", owner_id=1
    )
    assert_booking_request(
        client,
        bookings,
        f"2030-01-16T{next_start}",
        "2030-01-16T01:10:00",
        owner_id=2,
        status=status,
    )


@pytest.mark.parametrize(
    "start,end,status",
    [
        ("11:15:00", "11:45:00", 201),
        ("11:14:00", "11:45:00", 409),
        ("11:15:00", "11:46:00", 409),
    ],
)
def test_room_booking_between_two_active_bookings(
    client: TestClient, start: str, end: str, status: int
) -> None:
    bookings = []
    assert_booking_request(
        client, bookings, "2030-01-15T10:00:00", "2030-01-15T11:00:00", owner_id=1
    )
    assert_booking_request(
        client, bookings, "2030-01-15T12:00:00", "2030-01-15T13:00:00", owner_id=1
    )
    assert_booking_request(
        client,
        bookings,
        f"2030-01-15T{start}",
        f"2030-01-15T{end}",
        owner_id=2,
        status=status,
    )


def test_different_rooms_can_be_booked_at_the_same_time(client: TestClient) -> None:
    bookings = []
    for room_id in (1, 2):
        assert_booking_request(
            client,
            bookings,
            "2030-01-15T10:00:00",
            "2030-01-15T11:00:00",
            resource_id=room_id,
            owner_id=1,
        )


@pytest.mark.parametrize("start,status", [("11:00:00", 201), ("10:59:59", 409)])
def test_device_bookings_allow_adjacency_and_reject_overlap(
    client: TestClient, start: str, status: int
) -> None:
    bookings = []
    assert_booking_request(
        client,
        bookings,
        "2030-01-15T10:00:00",
        "2030-01-15T11:00:00",
        resource_id=3,
        owner_id=1,
    )
    assert_booking_request(
        client,
        bookings,
        f"2030-01-15T{start}",
        "2030-01-15T12:00:00",
        resource_id=3,
        owner_id=2,
        status=status,
    )
