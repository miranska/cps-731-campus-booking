"""Series creation checks V1 to V12 and V17 from the Group 12 change plan.

Every test uses a fresh SQLite file and a fixed clock of Tuesday
2030-01-15 09:00. Rejection tests compare the full stored database state
before and after the request, because Appendix A has no series-list
endpoint and a status code alone does not prove nothing was written.
"""

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session as OrmSession

from booking.database import initialize
from booking.main import create_app

NOW = datetime(2030, 1, 15, 9)
ALEX = {"X-User-ID": "1"}
SAM = {"X-User-ID": "2"}


@dataclass
class Api:
    client: TestClient
    database: Path


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(create_app(database, clock=lambda: NOW)) as client:
        yield Api(client, database)


def stored_state(database: Path) -> dict[str, list[tuple[Any, ...]]]:
    """Every row of every table, so any new series or booking row shows up
    regardless of how the series is stored."""
    connection = sqlite3.connect(database)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        return {
            table: sorted(
                connection.execute(f'SELECT * FROM "{table}"').fetchall(), key=repr
            )
            for table in tables
        }
    finally:
        connection.close()


def series_request(
    start: str = "2030-01-15T10:00:00",
    end: str = "2030-01-15T11:00:00",
    count: object = 4,
    resource_id: object = 1,
) -> dict[str, object]:
    return {"resource_id": resource_id, "start": start, "end": end, "count": count}


def book_single(api: Api, start: str, end: str, resource_id: int = 1) -> None:
    response = api.client.post(
        "/bookings",
        headers=SAM,
        json={"resource_id": resource_id, "start": start, "end": end},
    )
    assert response.status_code == 201


def weekly(first: str, count: int) -> list[str]:
    start = datetime.fromisoformat(first)
    return [(start + timedelta(weeks=i)).isoformat() for i in range(count)]


def assert_rejected(
    api: Api,
    body: dict[str, object],
    status: int,
    headers: dict[str, str] | None = None,
) -> None:
    before = stored_state(api.database)
    bookings_before = api.client.get("/bookings").json()
    response = api.client.post(
        "/series", headers=ALEX if headers is None else headers, json=body
    )
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)
    assert api.client.get("/bookings").json() == bookings_before
    assert stored_state(api.database) == before


# V1: C1, C2, C6. Weekly occurrences owned by the acting user, readable both
# as a series and as ordinary bookings.
def test_creates_weekly_series_owned_by_acting_user(api: Api) -> None:
    response = api.client.post("/series", headers=ALEX, json=series_request())
    assert response.status_code == 201
    series = response.json()
    assert set(series) == {"id", "owner_id", "resource_id", "occurrences"}
    assert series["owner_id"] == 1
    assert series["resource_id"] == 1

    occurrences = series["occurrences"]
    assert [o["start"] for o in occurrences] == weekly("2030-01-15T10:00:00", 4)
    assert [o["end"] for o in occurrences] == weekly("2030-01-15T11:00:00", 4)
    for occurrence in occurrences:
        assert set(occurrence) == {
            "id",
            "owner_id",
            "resource_id",
            "start",
            "end",
            "cancelled",
        }
        assert occurrence["owner_id"] == 1
        assert occurrence["resource_id"] == 1
        assert occurrence["cancelled"] is False
        assert api.client.get(f"/bookings/{occurrence['id']}").json() == occurrence

    assert api.client.get(f"/series/{series['id']}").json() == series
    listed = {b["id"]: b for b in api.client.get("/bookings").json()}
    assert all(listed[o["id"]] == o for o in occurrences)


# V2: C1. Both ends of the permitted count range.
@pytest.mark.parametrize(
    ("count", "last_start"),
    [(1, "2030-01-15T10:00:00"), (12, "2030-04-02T10:00:00")],
)
def test_count_boundaries_accepted(api: Api, count: int, last_start: str) -> None:
    response = api.client.post(
        "/series", headers=ALEX, json=series_request(count=count)
    )
    assert response.status_code == 201
    occurrences = response.json()["occurrences"]
    assert len(occurrences) == count
    assert occurrences[-1]["start"] == last_start
    assert len(api.client.get("/bookings").json()) == count


# V3: C1. Out-of-range and non-integer counts, including booleans.
@pytest.mark.parametrize("count", [0, 13, -1, 2.5, "4", True, None])
def test_invalid_count_rejected_without_changes(api: Api, count: object) -> None:
    book_single(api, "2030-01-16T10:00:00", "2030-01-16T11:00:00")
    assert_rejected(api, series_request(count=count), 422)


def test_missing_count_rejected(api: Api) -> None:
    body = series_request()
    del body["count"]
    assert_rejected(api, body, 422)


# V4: C2. Identity comes only from X-User-ID; resource must exist.
def test_unknown_user_rejected(api: Api) -> None:
    assert_rejected(api, series_request(), 404, headers={"X-User-ID": "99"})


@pytest.mark.parametrize("headers", [{}, {"X-User-ID": "abc"}, {"X-User-ID": "0"}])
def test_missing_or_malformed_identity_rejected(
    api: Api, headers: dict[str, str]
) -> None:
    assert_rejected(api, series_request(), 422, headers=headers)


@pytest.mark.parametrize(
    "extra", [{"owner_id": 2}, {"id": 5}, {"cancelled": True}, {"weekday": 1}]
)
def test_client_cannot_supply_extra_fields(api: Api, extra: dict[str, object]) -> None:
    assert_rejected(api, series_request() | extra, 422)


def test_unknown_resource_rejected(api: Api) -> None:
    assert_rejected(api, series_request(resource_id=99), 404)


@pytest.mark.parametrize("resource_id", [0, "1", True, 1.0])
def test_malformed_resource_id_rejected(api: Api, resource_id: object) -> None:
    assert_rejected(api, series_request(resource_id=resource_id), 422)


# V5: C3. Start strictly after now; end after start; timestamp format.
@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2030-01-15T09:00:00", "2030-01-15T10:00:00"),  # starts exactly now
        ("2030-01-15T08:00:00", "2030-01-15T10:00:00"),  # starts in the past
        ("2030-01-15T10:00:00", "2030-01-15T10:00:00"),  # zero length
        ("2030-01-15T11:00:00", "2030-01-15T10:00:00"),  # end before start
        ("2030-01-15T10:00:00Z", "2030-01-15T11:00:00Z"),  # offset not allowed
    ],
)
def test_invalid_interval_rejected(api: Api, start: str, end: str) -> None:
    assert_rejected(api, series_request(start=start, end=end), 422)


# V6: C3. Exactly eight hours is allowed; one second more is not.
def test_eight_hour_boundary(api: Api) -> None:
    assert_rejected(api, series_request(end="2030-01-15T18:00:01", resource_id=2), 422)
    response = api.client.post(
        "/series", headers=ALEX, json=series_request(end="2030-01-15T18:00:00")
    )
    assert response.status_code == 201


# V7: C3. Overnight occurrences up to eight hours.
def test_overnight_series(api: Api) -> None:
    assert_rejected(
        api,
        series_request("2030-01-15T22:00:00", "2030-01-16T06:01:00", count=3),
        422,
    )
    response = api.client.post(
        "/series",
        headers=ALEX,
        json=series_request("2030-01-15T22:00:00", "2030-01-16T06:00:00", count=3),
    )
    assert response.status_code == 201
    occurrences = response.json()["occurrences"]
    assert [o["end"] for o in occurrences] == weekly("2030-01-16T06:00:00", 3)


# V8: C4. Back-to-back with an existing booking is not a conflict, on
# either side.
@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2030-01-15T11:00:00", "2030-01-15T12:00:00"),  # starts as it ends
        ("2030-01-15T09:30:00", "2030-01-15T10:00:00"),  # ends as it starts
    ],
)
def test_adjacent_to_existing_booking_accepted(api: Api, start: str, end: str) -> None:
    book_single(api, "2030-01-22T10:00:00", "2030-01-22T11:00:00")
    response = api.client.post(
        "/series", headers=ALEX, json=series_request(start, end, count=3)
    )
    assert response.status_code == 201


# V9: C4, C5. A one-minute overlap rejects the whole series.
def test_one_minute_overlap_rejects_series(api: Api) -> None:
    book_single(api, "2030-01-22T10:00:00", "2030-01-22T11:00:00")
    assert_rejected(
        api, series_request("2030-01-15T10:59:00", "2030-01-15T11:59:00", count=3), 409
    )


# V10 and V11: C5. A conflict in the last or a middle week rejects everything,
# including earlier weeks that were free.
@pytest.mark.parametrize(
    ("clash_start", "clash_end"),
    [
        ("2030-02-19T10:30:00", "2030-02-19T11:30:00"),  # V10: week 6 of 6
        ("2030-01-29T09:00:00", "2030-01-29T10:01:00"),  # V11: week 3 of 6
    ],
)
def test_later_occurrence_conflict_rejects_whole_series(
    api: Api, clash_start: str, clash_end: str
) -> None:
    book_single(api, clash_start, clash_end)
    assert_rejected(api, series_request(count=6), 409)


def test_conflict_with_another_series_rejects_second(api: Api) -> None:
    first = api.client.post("/series", headers=ALEX, json=series_request(count=6))
    assert first.status_code == 201
    assert_rejected(
        api,
        series_request("2030-02-05T10:30:00", "2030-02-05T12:00:00", count=2),
        409,
        headers=SAM,
    )
    assert api.client.get(f"/series/{first.json()['id']}").json() == first.json()


def test_cancelled_booking_does_not_block_series(api: Api) -> None:
    book_single(api, "2030-01-29T10:00:00", "2030-01-29T11:00:00")
    booking_id = api.client.get("/bookings").json()[0]["id"]
    cancel = api.client.post(f"/bookings/{booking_id}/cancel", headers=SAM)
    assert cancel.status_code == 200
    response = api.client.post("/series", headers=ALEX, json=series_request(count=6))
    assert response.status_code == 201


# V12: C4, C5. The same times on a different resource do not conflict.
def test_different_resource_does_not_conflict(api: Api) -> None:
    book_single(api, "2030-02-19T10:00:00", "2030-02-19T11:00:00", resource_id=1)
    response = api.client.post(
        "/series", headers=ALEX, json=series_request(count=6, resource_id=2)
    )
    assert response.status_code == 201
    assert len(response.json()["occurrences"]) == 6


# V17: C5. A failure after rows are written but before the transaction
# completes must roll everything back. The fault is injected after the
# first flush, so it works whether the code flushes explicitly or commits.
def test_failure_mid_write_leaves_no_partial_series(api: Api) -> None:
    book_single(api, "2030-01-16T10:00:00", "2030-01-16T11:00:00")
    before = stored_state(api.database)
    bookings_before = api.client.get("/bookings").json()

    def fail_after_flush(session: OrmSession, context: object) -> None:
        raise RuntimeError("injected failure after rows were flushed")

    event.listen(OrmSession, "after_flush", fail_after_flush)
    try:
        with pytest.raises(RuntimeError, match="injected failure"):
            api.client.post("/series", headers=ALEX, json=series_request(count=6))
    finally:
        event.remove(OrmSession, "after_flush", fail_after_flush)

    assert api.client.get("/bookings").json() == bookings_before
    assert stored_state(api.database) == before
