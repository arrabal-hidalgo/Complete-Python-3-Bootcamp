from typing import Any

from pydantic import BaseModel


class RouteResult(BaseModel):
    """Represents the result of a route calculation."""

    output_stops: Any
    output_routes: Any
    output_directions: Any
