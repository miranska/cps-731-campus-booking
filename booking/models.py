from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str


class Resource(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    kind: str


class Booking(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    resource_id: int = Field(foreign_key="resource.id")
    start: datetime
    end: datetime
    cancelled: bool = False
