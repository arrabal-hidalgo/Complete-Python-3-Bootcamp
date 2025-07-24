from typing import List, Optional, Tuple

from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """
    Represents a user authenticated via token, holding their ID,
    anonymity status, and a list of role assignments.
    """

    id: str | None = None
    ref: str | None = None
    anonymous: bool
    # List of (role, destination) tuples. Destination is None for global roles.
    roles: List[Tuple[str, Optional[str]]] = []
