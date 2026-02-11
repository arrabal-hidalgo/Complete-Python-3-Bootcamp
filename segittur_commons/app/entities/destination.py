from enum import Enum

from pydantic import BaseModel, Field


class DestinationType(str, Enum):
    municipio = "Municipio"
    provincia = "Provincia"
    ccaa = "Comunidad autónoma"


class DestinationInfo(BaseModel):
    dest_type: DestinationType
    ineCode: str


class LightDestinationDTO(BaseModel):
    identifier: str
    name: str


class DestinationLightlistWrapper(BaseModel):
    destinations: list[LightDestinationDTO]
    total: int
    page: int
    total_pages: int = Field(..., alias="totalPages")
    size: int


class DestinationLightlistRequest(BaseModel):
    name_like: str | None = Field(None, alias="nameLike")
    grouping_type: str | None = Field(None, alias="groupingType")
    autonomous_community: str | None = Field(None, alias="autonomousCommunity")
    provinces: list[str] | None = None
