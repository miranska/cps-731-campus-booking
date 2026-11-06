"""Series read and cancellation checks V13 to V16 and V18 from the change plan.

Time moves only by rebuilding the app on the same SQLite file with a later
fixed clock, so "now" is always controlled.
"""

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from booking.database import initialize
from booking.main import create_app

CREATED_AT = datetime(2030, 1, 15, 9)
ALEX = {"X-User-ID": "1"}
SAM = {"X-User-ID": "2"}
WEEKS = [
    "2030-01-15T10:00:00",
    "2030-01-22T10:00:00",
    "2030-01-29T10:00:00",
    "2030-02-05T10:00:00",
    "2030-02-12T10:00:00",
    "2030-02-19T10:00:00",
]

Client = Callable[[datetime], TestClient]


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "booking.sqlite3"
    initialize(path)
    return path


@pytest.fixture
def client_at(database: Path) -> Iterator[Client]:
    clients: list[TestClient] = []

    def open_client(now: datetime) -> TestClient:
        client = TestClient(create_app(database, clock=lambda: now))
        client.__enter__()
        clients.append(client)
        return client

    yield open_client
    for client in clients:
        client.__exit__(None, None, None)


def create_six_week_series(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/series",
        headers=ALEX,
        json={
            "resource_id": 1,
            "start": "2030-01-15T10:00:00",
            "end": "2030-01-15T11:00:00",
            "count": 6,
        },
    )
    assert response.status_code == 201
    series: dict[str, Any] = response.json()
    return series


def cancelled_flags(series: dict[str, Any]) -> list[bool]:
    return [o["cancelled"] for o in series["occurrences"]]


# V13: C6. Series and occurrences survive an application restart.
def test_series_persists_after_restart(client_at: Client) -> None:
    created = create_six_week_series(client_at(CREATED_AT))
    restarted = client_at(CREATED_AT)
    response = restarted.get(f"/series/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created
    assert [o["start"] for o in response.json()["occurrences"]] == WEEKS


def test_read_unknown_or_malformed_series(client_at: Client) -> None:
    client = client_at(CREATED_AT)
    assert client.get("/series/999").status_code == 404
    assert client.get("/series/0").status_code == 422
    assert client.get("/series/abc").status_code == 422


# V14: C7, C9. Cancelling one occurrence leaves the rest active and frees
# only that slot.
def test_cancel_single_occurrence(client_at: Client) -> None:
    client = client_at(CREATED_AT)
    series = create_six_week_series(client)
    fourth = series["occurrences"][3]
    response = client.post(f"/bookings/{fourth['id']}/cancel", headers=ALEX)
    assert response.status_code == 200
    assert response.json()["cancelled"] is True

    after = client.get(f"/series/{series['id']}").json()
    assert cancelled_flags(after) == [False, False, False, True, False, False]

    rebook = client.post(
        "/bookings",
        headers=SAM,
        json={
            "resource_id": 1,
            "start": "2030-02-05T10:00:00",
            "end": "2030-02-05T11:00:00",
        },
    )
    assert rebook.status_code == 201


# V15: C8, C9. Past and ongoing occurrences are left alone; future ones are
# cancelled; all six stay visible in start order.
def test_cancel_series_with_past_ongoing_and_future(client_at: Client) -> None:
    series = create_six_week_series(client_at(CREATED_AT))
    later = client_at(datetime(2030, 1, 22, 10, 30))
    response = later.post(f"/series/{series['id']}/cancel", headers=ALEX)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "owner_id", "resource_id", "occurrences"}
    assert [o["start"] for o in body["occurrences"]] == WEEKS
    assert cancelled_flags(body) == [False, False, True, True, True, True]
    assert later.get(f"/series/{series['id']}").json() == body


def test_cancel_series_releases_future_slots(client_at: Client) -> None:
    client = client_at(CREATED_AT)
    series = create_six_week_series(client)
    response = client.post(f"/series/{series['id']}/cancel", headers=ALEX)
    assert response.status_code == 200
    assert cancelled_flags(response.json()) == [True] * 6
    assert create_six_week_series(client)["id"] != series["id"]


def test_cancel_series_with_nothing_left_succeeds_without_changes(
    client_at: Client,
) -> None:
    series = create_six_week_series(client_at(CREATED_AT))
    after_all = client_at(datetime(2030, 3, 1, 9))
    response = after_all.post(f"/series/{series['id']}/cancel", headers=ALEX)
    assert response.status_code == 200
    assert cancelled_flags(response.json()) == [False] * 6


# V16: C9. Only the owner can cancel, including on repeats; repeats by the
# owner change nothing, even after more time passes.
def test_non_owner_cannot_cancel_series(client_at: Client) -> None:
    client = client_at(CREATED_AT)
    series = create_six_week_series(client)
    before = client.get("/bookings").json()
    assert client.post(f"/series/{series['id']}/cancel", headers=SAM).status_code == 403
    assert client.get("/bookings").json() == before

    assert (
        client.post(f"/series/{series['id']}/cancel", headers=ALEX).status_code == 200
    )
    assert client.post(f"/series/{series['id']}/cancel", headers=SAM).status_code == 403


def test_repeat_series_cancel_changes_nothing(client_at: Client) -> None:
    series = create_six_week_series(client_at(CREATED_AT))
    first_now = client_at(datetime(2030, 1, 22, 10, 30))
    first = first_now.post(f"/series/{series['id']}/cancel", headers=ALEX)
    assert first.status_code == 200

    much_later = client_at(datetime(2030, 3, 1, 9))
    repeat = much_later.post(f"/series/{series['id']}/cancel", headers=ALEX)
    assert repeat.status_code == 200
    assert repeat.json() == first.json()


@pytest.mark.parametrize(
    ("path", "headers", "status"),
    [
        ("/series/999/cancel", ALEX, 404),
        ("/series/1/cancel", {"X-User-ID": "99"}, 404),
        ("/series/1/cancel", {}, 422),
        ("/series/0/cancel", ALEX, 422),
    ],
)
def test_cancel_series_rejects_bad_requests(
    client_at: Client, path: str, headers: dict[str, str], status: int
) -> None:
    client = client_at(CREATED_AT)
    create_six_week_series(client)
    before = client.get("/bookings").json()
    assert client.post(path, headers=headers).status_code == status
    assert client.get("/bookings").json() == before


# V16 (C10): a single booking cannot take a slot held by a series occurrence.
def test_single_booking_cannot_overlap_series(client_at: Client) -> None:
    client = client_at(CREATED_AT)
    create_six_week_series(client)
    response = client.post(
        "/bookings",
        headers=SAM,
        json={
            "resource_id": 1,
            "start": "2030-01-29T10:30:00",
            "end": "2030-01-29T11:30:00",
        },
    )
    assert response.status_code == 409


# V18: C7. One occurrence can be cancelled strictly before its start only.
def test_single_occurrence_cancel_boundary(client_at: Client) -> None:
    series = create_six_week_series(client_at(CREATED_AT))
    second = series["occurrences"][1]

    just_before = client_at(datetime(2030, 1, 22, 9, 59, 59))
    response = just_before.post(f"/bookings/{second['id']}/cancel", headers=ALEX)
    assert response.status_code == 200
    assert response.json()["cancelled"] is True


def test_single_occurrence_cannot_be_cancelled_at_start(client_at: Client) -> None:
    series = create_six_week_series(client_at(CREATED_AT))
    second = series["occurrences"][1]

    at_start = client_at(datetime(2030, 1, 22, 10))
    response = at_start.post(f"/bookings/{second['id']}/cancel", headers=ALEX)
    assert response.status_code == 409
    assert at_start.get(f"/bookings/{second['id']}").json()["cancelled"] is False
