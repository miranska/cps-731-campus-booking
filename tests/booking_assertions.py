from fastapi.testclient import TestClient


def assert_booking_list(client: TestClient, expected: list[dict]) -> None:
    response = client.get("/bookings")
    assert response.status_code == 200
    assert response.json() == expected


def assert_booking_request(
    client: TestClient,
    expected_bookings: list[dict],
    start: str,
    end: str,
    *,
    owner_id: int,
    resource_id: int = 1,
    status: int = 201,
) -> None:
    """Submit a request and update the expected list after a confirmation."""
    body = {"resource_id": resource_id, "start": start, "end": end}
    response = client.post("/bookings", headers={"X-User-ID": str(owner_id)}, json=body)
    assert response.status_code == status
    if status == 201:
        booking_id = response.json()["id"]
        assert type(booking_id) is int and booking_id > 0
        assert all(booking["id"] != booking_id for booking in expected_bookings)
        expected = {**body, "id": booking_id, "owner_id": owner_id, "cancelled": False}
        assert response.json() == expected
        expected_bookings.append(expected)
    else:
        assert status == 409
        assert response.json() == {
            "detail": "Resource is already booked for this interval"
        }
    assert_booking_list(client, expected_bookings)
