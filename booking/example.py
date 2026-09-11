"""Run against the local server after initializing its sample data."""

import json
from datetime import timedelta

import httpx

from booking.clock import campus_now


def main() -> None:
    start = (campus_now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    with httpx.Client(base_url="http://127.0.0.1:8000") as client:
        resources = client.get("/resources")
        resources.raise_for_status()
        resource = resources.json()[0]
        print(f"Selected {resource['name']} (ID {resource['id']})")
        response = client.post(
            "/bookings",
            headers={"X-User-ID": "1"},
            json={
                "resource_id": resource["id"],
                "start": start.isoformat(),
                "end": (start + timedelta(hours=1)).isoformat(),
            },
        )
        if response.is_error:
            print(response.text)
        response.raise_for_status()
        booking = response.json()
        retrieved = client.get(f"/bookings/{booking['id']}")
        retrieved.raise_for_status()
        print(json.dumps(retrieved.json(), indent=2))
        cancelled = client.post(
            f"/bookings/{booking['id']}/cancel", headers={"X-User-ID": "1"}
        )
        cancelled.raise_for_status()
        print("Cancelled record:")
        print(json.dumps(cancelled.json(), indent=2))
        replacement = client.post(
            "/bookings",
            headers={"X-User-ID": "2"},
            json={
                "resource_id": resource["id"],
                "start": booking["start"],
                "end": booking["end"],
            },
        )
        replacement.raise_for_status()
        print("Released slot booked by user 2:")
        print(json.dumps(replacement.json(), indent=2))


if __name__ == "__main__":
    main()
