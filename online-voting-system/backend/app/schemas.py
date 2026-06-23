from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MessageResponse(BaseModel):
    message: str


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: str
    cnic: str | None = None
    role: str
    is_verified: bool
    is_blocked: bool = False


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=80)
    email: EmailStr
    cnic: str = Field(pattern=r"^\d{5}-?\d{7}-?\d{1}$")
    password: str = Field(min_length=5, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class SessionPublic(BaseModel):
    id: int
    ip_address: str | None = None
    user_agent: str | None = None
    expires_at: str
    revoked_at: str | None = None
    created_at: str


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class EmailRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=5, max_length=128)


class ElectionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=500)
    start_time: datetime | None = None
    end_time: datetime | None = None


class ElectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    start_time: datetime | None = None
    end_time: datetime | None = None


class ElectionStatusUpdate(BaseModel):
    status: str = Field(pattern="^(DRAFT|ACTIVE|PAUSED|CLOSED|PUBLISHED)$")


class CandidateCreate(BaseModel):
    election_id: int = 1
    name: str = Field(min_length=3, max_length=80)
    party: str = Field(min_length=2, max_length=80)
    manifesto: str = Field(min_length=10, max_length=500)
    image_url: str | None = None
    color: str = Field(default="cyan", max_length=24)


class CandidateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=80)
    party: str | None = Field(default=None, min_length=2, max_length=80)
    manifesto: str | None = Field(default=None, min_length=10, max_length=500)
    image_url: str | None = None
    color: str | None = Field(default=None, max_length=24)


class CandidateApplicationCreate(BaseModel):
    election_id: int = 1
    full_name: str = Field(min_length=3, max_length=80)
    party: str = Field(min_length=2, max_length=80)
    manifesto: str = Field(min_length=20, max_length=700)
    experience: str = Field(min_length=10, max_length=700)
    image_url: str | None = None


class CandidateApplicationReview(BaseModel):
    status: str = Field(pattern="^(ACCEPTED|DECLINED)$")


class VoteCreate(BaseModel):
    election_id: int = 1
    candidate_id: int
    device_hash: str | None = None


class AlertResolveRequest(BaseModel):
    status: str = Field(default="RESOLVED", pattern="^(ACKNOWLEDGED|RESOLVED)$")


class NotificationCreate(BaseModel):
    user_id: int | None = None
    role_target: str | None = Field(default=None, pattern="^(VOTER|ADMIN|SUPER_ADMIN)$")
    title: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=3, max_length=500)
    type: str = Field(default="INFO", pattern="^(INFO|SUCCESS|WARNING|ERROR|SECURITY)$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    page: str = Field(default="website", max_length=80)


class AdminRoleUpdate(BaseModel):
    role: str = Field(pattern="^(VOTER|ADMIN|SUPER_ADMIN)$")


class BlockUserRequest(BaseModel):
    is_blocked: bool
