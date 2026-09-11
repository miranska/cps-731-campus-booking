from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from booking.database import initialize
from booking.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(
        create_app(database, clock=lambda: datetime(2030, 1, 15, 9))
    ) as api:
        yield api


def test_create_retrieve_and_list_booking(client: TestClient) -> None:
    response = client.post(
        "/bookings",
        headers={"X-User-ID": "2"},
        json={
            "resource_id": 1,
            "start": "2030-01-15T10:00:00",
            "end": "2030-01-15T11:00:00",
        },
    )
    assert response.status_code == 201
    expected = {
        "id": 1,
        "owner_id": 2,
        "resource_id": 1,
        "start": "2030-01-15T10:00:00",
        "end": "2030-01-15T11:00:00",
        "cancelled": False,
    }
    assert response.json() == expected
    assert client.get("/bookings/1").json() == expected
    assert client.get("/bookings").json() == [expected]


@pytest.mark.parametrize(
    "changes,headers",
    [
        ({"resource_id": 99}, {"X-User-ID": "1"}),
        ({}, {"X-User-ID": "99"}),
        ({}, {}),
        ({}, {"X-User-ID": "Alex"}),
        ({"owner_id": 2}, {"X-User-ID": "1"}),
        ({"start": "2030-01-15T08:00:00"}, {"X-User-ID": "1"}),
        ({"end": "2030-01-15T09:00:00"}, {"X-User-ID": "1"}),
        ({"end": "2030-01-15T20:00:00"}, {"X-User-ID": "1"}),
        ({"start": "bad timestamp"}, {"X-User-ID": "1"}),
        ({"start": "2030-01-15T10:00:00Z"}, {"X-User-ID": "1"}),
    ],
)
def test_invalid_request_does_not_create_booking(
    client: TestClient, changes: dict[str, object], headers: dict[str, str]
) -> None:
    body = {
        "resource_id": 1,
        "start": "2030-01-15T10:00:00",
        "end": "2030-01-15T11:00:00",
    }
    response = client.post("/bookings", headers=headers, json={**body, **changes})
    assert response.status_code in (404, 422)
    assert client.get("/bookings").json() == []


def test_conflict_preserves_existing_booking(client: TestClient) -> None:
    body = {
        "resource_id": 1,
        "start": "2030-01-15T10:00:00",
        "end": "2030-01-15T12:00:00",
    }
    created = client.post("/bookings", headers={"X-User-ID": "1"}, json=body)
    assert created.status_code == 201
    conflict = client.post(
        "/bookings",
        headers={"X-User-ID": "2"},
        json={**body, "start": "2030-01-15T11:00:00", "end": "2030-01-15T13:00:00"},
    )
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "Resource is already booked for this interval"}
    assert client.get("/bookings").json() == [created.json()]


def test_bookings_survive_restart(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(
        create_app(database, clock=lambda: datetime(2030, 1, 15, 9))
    ) as api:
        response = api.post(
            "/bookings",
            headers={"X-User-ID": "1"},
            json={
                "resource_id": 1,
                "start": "2030-01-15T10:00:00",
                "end": "2030-01-15T11:00:00",
            },
        )
        assert response.status_code == 201
        record = response.json()
    with TestClient(create_app(database)) as api:
        assert api.get(f"/bookings/{record['id']}").json() == record
        assert api.get("/bookings").json() == [record]


def test_missing_booking_and_documented_operations(client: TestClient) -> None:
    response = client.get("/bookings/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown booking"}
    schema = client.get("/openapi.json").json()
    creation = schema["paths"]["/bookings"]["post"]
    assert set(creation["responses"]) == {"201", "404", "409", "422"}
    assert creation["responses"]["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    assert creation["parameters"][0]["name"].lower() == "x-user-id"
    assert creation["parameters"][0]["required"] is True
