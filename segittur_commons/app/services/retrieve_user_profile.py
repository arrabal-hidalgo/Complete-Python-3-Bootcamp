import os
from typing import Any

import requests

from segittur_commons.app.entities.user_profile import (
    InternalUserProfile,
    RecievedUserProfile,
)


def fetch_user_profile(endpoint: str, identifier: str) -> dict[str, Any] | None:
    """Fetches a user profile from the API given an endpoint and an identifier."""
    base_url = os.getenv("S5_USER_PROFILE_API_URL")
    token = os.getenv("S5_API_TOKEN")

    url = f"{base_url}/persons/{endpoint}/{identifier}"
    headers = {"accept": "application/json", "Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)

        if not response.text.strip():
            return None

        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP error retrieving user profile from {endpoint}: {e}") from e
    except ValueError:
        raise RuntimeError(f"Invalid JSON response from {endpoint}")


def get_user_profile(identifier: str, endpoint: str) -> InternalUserProfile | None:
    """Retrieves the internal user profile, handling both anonymous and registered users."""

    user_data = fetch_user_profile(endpoint, identifier)
    if not user_data:
        return None

    try:
        user_profile = RecievedUserProfile(**user_data)
        return user_profile.get_internal_user_profile()
    except Exception as e:
        raise RuntimeError(f"Error parsing user profile: {e}") from e
