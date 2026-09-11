from datetime import datetime
from zoneinfo import ZoneInfo


def campus_now() -> datetime:
    """Toronto wall time, matching the API's offset-free campus timestamps."""
    return datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None)
