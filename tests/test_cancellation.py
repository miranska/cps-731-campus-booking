from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from booking.database import initialize
from booking.main import create_app

BODY = {"resource_id": 1, "start": "2030-01-15T10:00:00", "end": "2030-01-15T11:00:00"}


def test_owner_cancels_and_reuses_slot_after_restart(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(
        create_app(database, clock=lambda: datetime(2030, 1, 15, 9))
    ) as api:
        created = api.post("/bookings", headers={"X-User-ID": "1"}, json=BODY)
        assert created.status_code == 201
        expected = {**created.json(), "cancelled": True}
        cancelled = api.post("/bookings/1/cancel", headers={"X-User-ID": "1"})
        assert cancelled.status_code == 200
        assert cancelled.json() == expected
    with TestClient(
        create_app(database, clock=lambda: datetime(2030, 1, 15, 9, 30))
    ) as api:
        assert api.get("/bookings/1").json() == expected
        assert api.get("/bookings").json() == [expected]
        replacement = api.post("/bookings", headers={"X-User-ID": "2"}, json=BODY)
        assert replacement.status_code == 201
        assert replacement.json() == {
            **created.json(),
            "id": 2,
            "owner_id": 2,
            "cancelled": False,
        }


def test_non_owner_cannot_cancel(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(
        create_app(database, clock=lambda: datetime(2030, 1, 15, 9))
    ) as api:
        created = api.post("/bookings", headers={"X-User-ID": "1"}, json=BODY)
        assert created.status_code == 201
        response = api.post("/bookings/1/cancel", headers={"X-User-ID": "2"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Only the owner can cancel this booking"}
        assert api.get("/bookings/1").json() == created.json()
        assert api.get("/bookings").json() == [created.json()]


def test_active_booking_cannot_be_cancelled_after_start(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    now = datetime(2030, 1, 15, 9)
    with TestClient(create_app(database, clock=lambda: now)) as api:
        created = api.post("/bookings", headers={"X-User-ID": "1"}, json=BODY)
        assert created.status_code == 201
        now = datetime(2030, 1, 15, 10, 30)
        response = api.post("/bookings/1/cancel", headers={"X-User-ID": "1"})
        assert response.status_code == 409
        assert response.json() == {"detail": "Booking has already started"}
        assert api.get("/bookings/1").json() == created.json()
        assert api.get("/bookings").json() == [created.json()]


def test_owner_retries_before_and_after_start_without_changes(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    now = datetime(2030, 1, 15, 9)
    with TestClient(create_app(database, clock=lambda: now)) as api:
        assert (
            api.post("/bookings", headers={"X-User-ID": "1"}, json=BODY).status_code
            == 201
        )
        cancelled = api.post("/bookings/1/cancel", headers={"X-User-ID": "1"})
        assert cancelled.status_code == 200
        for retry_time in [datetime(2030, 1, 15, 9, 30), datetime(2030, 1, 15, 12)]:
            now = retry_time
            retry = api.post("/bookings/1/cancel", headers={"X-User-ID": "1"})
            assert retry.status_code == 200
            assert retry.json() == cancelled.json()
            unauthorized = api.post("/bookings/1/cancel", headers={"X-User-ID": "2"})
            assert unauthorized.status_code == 403
            assert unauthorized.json() == {
                "detail": "Only the owner can cancel this booking"
            }
            assert api.get("/bookings/1").json() == cancelled.json()
            assert api.get("/bookings").json() == [cancelled.json()]


def test_cancellation_documents_responses_and_identity(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "booking.sqlite3")) as api:
        operation = api.get("/openapi.json").json()["paths"][
            "/bookings/{booking_id}/cancel"
        ]["post"]
        assert set(operation["responses"]) == {"200", "403", "404", "409", "422"}
        for status in ["403", "404", "409", "422"]:
            assert operation["responses"][status]["content"]["application/json"][
                "schema"
            ] == {"$ref": "#/components/schemas/ErrorResponse"}
        identity = next(
            item
            for item in operation["parameters"]
            if item["name"].lower() == "x-user-id"
        )
        assert identity["required"] is True
