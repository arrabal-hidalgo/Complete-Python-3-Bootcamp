import os
from abc import ABC, abstractmethod
from typing import List, Type

from jwt.exceptions import InvalidTokenError

from segittur_commons.app.entities.user import AuthenticatedUser
from segittur_commons.app.infrastructure.identity_manager.keycloack_im import KeycloakIm


class UserParser(ABC):
    """Abstract base class for parsing a token into a user object."""

    def __init__(self, token: dict):
        self.token = token

    @abstractmethod
    def can_parse(self) -> bool:
        """Determines if this parser can handle the given token."""
        pass

    @abstractmethod
    def get_user(self) -> AuthenticatedUser:
        """Parses the token and returns an AuthenticatedUser."""
        pass


class RegisteredUserParser(UserParser):
    """Parses a standard registered user token from Keycloak."""

    AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "account")

    def can_parse(self) -> bool:
        # This parser handles tokens for the 'account' audience or tokens without a specific audience.
        return "aud" not in self.token or self.token.get("aud") == self.AUDIENCE

    def get_user(self) -> AuthenticatedUser:
        user_id = self.token.get("username")
        parsed_roles = []
        token_roles = self.token.get("roles", [])
        for role_info in token_roles:
            destination = role_info.get("destination")
            for role_name in role_info.get("roles", []):
                parsed_roles.append((role_name, destination))

        return AuthenticatedUser(id=user_id, anonymous=False, roles=parsed_roles)


class Authenticator:
    """
    Service to authenticate a user by decoding a token and parsing it
    into a user entity using a chain of parsers.
    """

    def __init__(self, identity_manager: KeycloakIm, custom_parsers: List[Type[UserParser]] = None):
        self.identity_manager = identity_manager
        # Standard parser are always included. Custom parsers are checked first.
        self.parsers = (custom_parsers or []) + [RegisteredUserParser]

    def get_current_user(self, token: str) -> AuthenticatedUser:
        access_token = self.identity_manager.decode(token)

        for parser_class in self.parsers:
            parser_instance = parser_class(access_token)
            if parser_instance.can_parse():
                return parser_instance.get_user()

        raise InvalidTokenError("No suitable parser found for the provided token.")
