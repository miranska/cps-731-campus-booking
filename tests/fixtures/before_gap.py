"""Original confirmations from v1.0.0 (8544ba7).

To rebuild the fixture, point PYTHONPATH to that checkout and use an unused path.

    PYTHONPATH=/tmp/v1.0.0 python tests/fixtures/before_gap.py /tmp/before-gap.sqlite3
"""

import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from booking.database import initialize
from booking.main import create_app

CONFIRMATIONS = [
    {
        "id": 1,
        "owner_id": 1,
        "resource_id": 1,
        "start": "2030-01-15T10:00:00",
        "end": "2030-01-15T11:00:00",
        "cancelled": False,
    },
    {
        "id": 2,
        "owner_id": 2,
        "resource_id": 1,
        "start": "2030-01-15T11:05:00",
        "end": "2030-01-15T12:00:00",
        "cancelled": False,
    },
]


def generate(database: Path) -> None:
    if database.exists():
        raise FileExistsError(database)
    initialize(database)
    app = create_app(database, clock=lambda: datetime(2030, 1, 15, 8))
    with TestClient(app) as api:
        expected = []
        for booking in CONFIRMATIONS:
            response = api.post(
                "/bookings",
                headers={"X-User-ID": str(booking["owner_id"])},
                json={key: booking[key] for key in ("resource_id", "start", "end")},
            )
            assert response.status_code == 201, response.text
            assert response.json() == booking
            expected.append(booking)
            listed = api.get("/bookings")
            assert listed.status_code == 200
            assert listed.json() == expected


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
