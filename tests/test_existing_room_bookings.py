from datetime import datetime
from pathlib import Path
from shutil import copyfile

import pytest
from booking_assertions import assert_booking_list, assert_booking_request
from fastapi.testclient import TestClient
from fixtures.before_gap import CONFIRMATIONS

from booking.main import create_app


@pytest.mark.parametrize(
    "start,end,status",
    [
        ("09:00:00", "09:46:00", 409),
        ("09:00:00", "09:45:00", 201),
        ("12:14:00", "13:00:00", 409),
        ("12:15:00", "13:00:00", 201),
    ],
)
def test_room_bookings_confirmed_before_the_gap_rule(
    tmp_path: Path, start: str, end: str, status: int
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "before-gap.sqlite3"
    database = tmp_path / "bookings.sqlite3"
    copyfile(fixture, database)
    app = create_app(database, clock=lambda: datetime(2030, 1, 15, 8))
    with TestClient(app) as api:
        bookings = list(CONFIRMATIONS)
        assert_booking_list(api, bookings)
        assert_booking_request(
            api,
            bookings,
            f"2030-01-15T{start}",
            f"2030-01-15T{end}",
            owner_id=1,
            status=status,
        )
