import argparse
import os
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from booking.models import Resource, User


def database_path() -> Path:
    return Path(os.environ.get("BOOKING_DATABASE", "booking.sqlite3"))


def make_engine(path: Path) -> Engine:
    return create_engine(
        f"sqlite:///{path.resolve()}", connect_args={"check_same_thread": False}
    )


def initialize(path: Path, *, reset: bool = False) -> None:
    engine = make_engine(path)
    try:
        if reset:
            SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            for user in [User(id=1, name="Alex Chen"), User(id=2, name="Sam Patel")]:
                if session.get(User, user.id) is None:
                    session.add(user)
            for resource in [
                Resource(id=1, name="Study room A", kind="room"),
                Resource(id=2, name="Study room B", kind="room"),
                Resource(id=3, name="Camera 01", kind="device"),
                Resource(id=4, name="Camera 02", kind="device"),
            ]:
                if session.get(Resource, resource.id) is None:
                    session.add(resource)
            session.commit()
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize sample booking data.")
    parser.add_argument("command", choices=["init", "reset"])
    parser.add_argument("--yes", action="store_true", help="Confirm data deletion")
    args = parser.parse_args()
    if args.command == "reset" and not args.yes:
        parser.error("reset deletes all application data; supply --yes to confirm")
    path = database_path()
    initialize(path, reset=args.command == "reset")
    print(f"Initialized {path.resolve()}")


if __name__ == "__main__":
    main()
