from typing import Optional

import casbin

from segittur_commons.app.entities.user import AuthenticatedUser


class CasbinAuthorizer:
    """
    Handles authorization logic using a Casbin enforcer.
    It checks if any of a user's roles grant permission for a given request.
    """

    def __init__(self, enforcer: casbin.Enforcer):
        self.enforcer = enforcer

    def check(
        self,
        user: AuthenticatedUser,
        path: str,
        method: str,
        resource_destination: Optional[str] = None,
    ) -> bool:
        """
        Checks if the user has permission to access the resource.

        Returns:
            bool: True if access is granted, False otherwise.
        """
        for user_role, user_destination in user.roles:
            # Case 1: Destination-specific role assignment (e.g., GESTOR_DESTINO in GRANADA)
            if user_destination:
                if resource_destination and resource_destination != user_destination:
                    continue  # This role is for a different destination.

                domain_to_check = user_destination
                if self.enforcer.enforce(user_role, domain_to_check, path, method):
                    return True  # Permission granted

            # Case 2: Global role assignment (e.g., GESTOR_PID)
            else:
                domain_to_check = resource_destination or "*"
                if self.enforcer.enforce(user_role, domain_to_check, path, method):
                    return True  # Permission granted

        return False  # No role granted permission
