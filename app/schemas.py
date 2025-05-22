from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import UserRole, RecurrenceFrequency, RecurrenceEndType


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class EventBase(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_frequency: Optional[RecurrenceFrequency] = None
    recurrence_interval: int = 1
    recurrence_days: Optional[List[str]] = None
    recurrence_end_type: Optional[RecurrenceEndType] = None
    recurrence_end_count: Optional[int] = None
    recurrence_end_date: Optional[datetime] = None
    recurrence_exceptions: Optional[List[datetime]] = None

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

    @validator('recurrence_days')
    def validate_recurrence_days(cls, v, values):
        if values.get('recurrence_frequency') == RecurrenceFrequency.WEEKLY and not v:
            raise ValueError('Days must be specified for weekly recurrence')
        if v and not all(day.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] for day in v):
            raise ValueError('Days must be valid weekday names')
        return v

    @validator('recurrence_end_count')
    def validate_recurrence_end_count(cls, v, values):
        if values.get('recurrence_end_type') == RecurrenceEndType.COUNT and not v:
            raise ValueError('End count must be specified when end_type is COUNT')
        return v

    @validator('recurrence_end_date')
    def validate_recurrence_end_date(cls, v, values):
        if values.get('recurrence_end_type') == RecurrenceEndType.UNTIL and not v:
            raise ValueError('End date must be specified when end_type is UNTIL')
        return v


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventPermissionBase(BaseModel):
    role: UserRole


class EventPermissionCreate(EventPermissionBase):
    user_id: int


class EventPermission(EventPermissionBase):
    id: int
    event_id: int
    user_id: int

    class Config:
        from_attributes = True


class EventVersionBase(BaseModel):
    version_number: int
    data: dict
    changed_by: int


class EventVersion(EventVersionBase):
    id: int
    event_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChangelogBase(BaseModel):
    version_from: int
    version_to: int
    diff: dict


class Changelog(ChangelogBase):
    id: int
    event_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventConflictBase(BaseModel):
    event_id: int
    conflicting_event_id: int
    conflict_type: str
    resolution: Optional[str] = None


class EventConflict(EventConflictBase):
    id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    event_id: int
    message: str
    type: str


class Notification(NotificationBase):
    id: int
    user_id: int
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True 