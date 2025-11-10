from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: UUID | None = None
    channel: str = "S8"


class SentProfile(BaseModel):
    likes: list[str] = []
    dislikes: list[str] = []


class SentUserProfile(UserProfile):
    profile: SentProfile


class GetId(BaseModel):
    id: str = Field(default="", alias="_id")
    timestamp: Optional[int] = None
    date: Optional[datetime] = None


class Localization(BaseModel):
    get_id: Optional[GetId] = None
    street: Optional[str] = None
    country: Optional[str] = None
    province: Optional[str] = None
    postalCode: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    autonomousCommunity: Optional[str] = None
    region: Optional[str] = None


class TypeValueDescription(BaseModel):
    get_id: Optional[GetId] = None
    type: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None


class Segment(BaseModel):
    get_id: Optional[GetId] = None
    identificator: Optional[str] = None
    name: Optional[str] = None
    ruleSet: Optional[dict[str, Any]] = None
    minThreshold: Optional[int] = None
    expirationTime: Optional[int] = None


class SegmentationItem(BaseModel):
    get_id: Optional[GetId] = None
    segment: Optional[Segment] = None
    counter: Optional[int] = None
    lastUpdate: Optional[datetime] = None
    expiresAt: Optional[datetime] = None


class SegmentationlistItem(BaseModel):
    get_id: Optional[GetId] = None
    identificator: Optional[str] = None
    name: Optional[str] = None
    ruleSet: Optional[dict[str, Any]] = None
    minThreshold: Optional[int] = None
    expirationTime: Optional[int] = None


class InternalUserProfile(BaseModel):
    age: int
    personalInterests: dict[str, float]
    relatedInterests: dict[str, float]

    def format_profile(self) -> str:
        likes_str = (
            "\n".join(f"- {k} priority: {v:.2f}" for k, v in self.personalInterests.items())
            or "None"
        )
        interests_str = (
            "\n".join(f"- {k} priority: {v:.2f}" for k, v in self.relatedInterests.items())
            or "None"
        )
        return f"Age: {self.age}\nLikes:\n{likes_str}\nInterests:\n{interests_str}"


class RecievedUserProfile(BaseModel):
    get_id: Optional[GetId] = None
    idPid: Optional[str] = None
    fingerPrint: Optional[str] = None
    tag: Optional[str] = None
    comments: Optional[str] = None
    description: Optional[str] = None
    age: Optional[int] = None
    language: Optional[str] = None
    localization: Optional[Localization] = None
    educationLevel: Optional[TypeValueDescription] = None
    professionalPosition: Optional[TypeValueDescription] = None
    genre: Optional[TypeValueDescription] = None
    segmentation: list[SegmentationItem] = []
    segmentationWhitelist: list[SegmentationlistItem] = []
    segmentationBlacklist: list[SegmentationlistItem] = []
    interactionsTypesBlacklist: list[str] = []
    personalInterests: dict[str, float] = {}
    relatedInterests: dict[str, float] = {}
    clusterId: Optional[int] = None
    deleted: Optional[bool] = None

    def get_internal_user_profile(self) -> InternalUserProfile:
        related_interests_int = {k: v for k, v in self.relatedInterests.items()}
        return InternalUserProfile(
            age=self.age or 0,
            personalInterests=self.personalInterests,
            relatedInterests=related_interests_int,
        )
