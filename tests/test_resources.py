import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from booking.database import initialize, make_engine
from booking.main import create_app
from booking.models import Resource


def test_student_can_browse_seeded_resources(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    with TestClient(create_app(database)) as client:
        response = client.get("/resources")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Study room A", "kind": "room"},
        {"id": 2, "name": "Study room B", "kind": "room"},
        {"id": 3, "name": "Camera 01", "kind": "device"},
        {"id": 4, "name": "Camera 02", "kind": "device"},
    ]


def test_documented_init_command_is_repeatable(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "booking.database", "init"],
            env={**os.environ, "BOOKING_DATABASE": str(database)},
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Initialized" in result.stdout
    with TestClient(create_app(database)) as client:
        assert len(client.get("/resources").json()) == 4


def test_startup_and_init_preserve_persisted_changes(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    # Fixture setup simulates an existing database; no administration API is needed.
    engine = make_engine(database)
    with Session(engine) as session:
        room = session.get(Resource, 1)
        assert room is not None
        room.name = "Renamed study room"
        session.add(room)
        session.commit()
    engine.dispose()
    initialize(database)
    for _ in range(2):
        with TestClient(create_app(database)) as client:
            assert client.get("/resources").json()[0]["name"] == "Renamed study room"


def test_databases_are_isolated_and_startup_does_not_seed(tmp_path: Path) -> None:
    seeded = tmp_path / "seeded.sqlite3"
    empty = tmp_path / "empty.sqlite3"
    initialize(seeded)
    with TestClient(create_app(seeded)) as first:
        with TestClient(create_app(empty)) as second:
            assert len(first.get("/resources").json()) == 4
            assert second.get("/resources").json() == []


def test_interactive_documentation_describes_resource_listing(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "booking.sqlite3")) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/resources"]["get"]
    assert "200" in operation["responses"]
    assert operation.get("parameters", []) == []


def test_reset_requires_confirmation_and_restores_samples(tmp_path: Path) -> None:
    database = tmp_path / "booking.sqlite3"
    initialize(database)
    engine = make_engine(database)
    with Session(engine) as session:
        session.add(Resource(id=99, name="Extra camera", kind="device"))
        session.commit()
    engine.dispose()
    command = [sys.executable, "-m", "booking.database", "reset"]
    environment = {**os.environ, "BOOKING_DATABASE": str(database)}
    refused = subprocess.run(command, env=environment, capture_output=True)
    assert refused.returncode != 0
    with TestClient(create_app(database)) as client:
        assert len(client.get("/resources").json()) == 5
    for _ in range(2):
        subprocess.run(command + ["--yes"], env=environment, check=True)
        with TestClient(create_app(database)) as client:
            resources = client.get("/resources").json()
            assert [resource["id"] for resource in resources] == [1, 2, 3, 4]
