import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, NaiveDatetime


def timestamp_string(value: object) -> object:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?", value
    ):
        raise ValueError(
            "Use YYYY-MM-DDTHH:MM:SS with optional microseconds, no offset"
        )
    return value


CampusTimestamp = Annotated[
    NaiveDatetime,
    BeforeValidator(timestamp_string),
    Field(
        description=(
            "Toronto local YYYY-MM-DDTHH:MM:SS, optional 1–6 fractional digits; "
            "no Z or offset. DST transitions are outside the simulation."
        )
    ),
]


class ErrorResponse(BaseModel):
    detail: str


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: int = Field(strict=True, gt=0, le=9223372036854775807)
    start: CampusTimestamp
    end: CampusTimestamp


class BookingRead(BaseModel):
    id: int
    owner_id: int
    resource_id: int
    start: datetime
    end: datetime
    cancelled: bool
