from uuid import UUID

from pydantic import BaseModel, SecretStr


class AuthenticatedUser(BaseModel):
    """
    Represents a user authenticated via token, holding their ID,
    anonymity status, and a list of role assignments.
    """

    id: str | None = None
    session: UUID | None = None
    access_token: SecretStr | None = None
    # List of (role, destination) tuples. Destination is None for global roles.
    roles: list[tuple[str, str | None]] = []

    @property
    def token(self):
        return self.access_token.get_secret_value()
