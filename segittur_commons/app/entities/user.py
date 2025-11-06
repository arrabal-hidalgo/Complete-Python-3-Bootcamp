from typing import List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """
    Represents a user authenticated via token, holding their ID,
    anonymity status, and a list of role assignments.
    """

    id: str | None = None
    session: UUID | None = None
    token: str | None = None
    # List of (role, destination) tuples. Destination is None for global roles.
    roles: List[Tuple[str, Optional[str]]] = []
