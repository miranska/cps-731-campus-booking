from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from booking.database import initialize
from booking.main import create_app

pytest.register_assert_rewrite("booking_assertions")


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(
        create_app(database, clock=lambda: datetime(2030, 1, 15, 9))
    ) as api:
        yield api
