from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum, Interval, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base


class UserRole(str, enum.Enum):
    OWNER = "Owner"
    EDITOR = "Editor"
    VIEWER = "Viewer"


class RecurrenceFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrenceEndType(str, enum.Enum):
    NEVER = "never"
    COUNT = "count"
    UNTIL = "until"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    events = relationship("Event", back_populates="owner")
    permissions = relationship("EventPermission", back_populates="user")
    versions = relationship("EventVersion", back_populates="user")
    blacklisted_tokens = relationship("TokenBlacklist", back_populates="user")

    __table_args__ = (
        Index('idx_user_email_username', 'email', 'username'),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), index=True)
    description = Column(Text)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    location = Column(String(200))
    is_recurring = Column(Boolean, default=False)
    recurrence_frequency = Column(String(20))
    recurrence_interval = Column(Integer, default=1)
    recurrence_days = Column(JSON)
    recurrence_end_type = Column(String(20))
    recurrence_end_count = Column(Integer)
    recurrence_end_date = Column(DateTime)
    recurrence_exceptions = Column(JSON)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    owner = relationship("User", back_populates="events")
    versions = relationship("EventVersion", back_populates="event")
    changelog = relationship("Changelog", back_populates="event")
    conflicts = relationship("EventConflict", back_populates="event", foreign_keys="[EventConflict.event_id]")
    conflicting_events = relationship("EventConflict", back_populates="conflicting_event", foreign_keys="[EventConflict.conflicting_event_id]")
    permissions = relationship("EventPermission", back_populates="event")

    __table_args__ = (
        Index('idx_event_dates', 'start_time', 'end_time'),
        Index('idx_event_owner', 'owner_id'),
        Index('idx_event_recurring', 'is_recurring'),
    )


class EventPermission(Base):
    __tablename__ = "event_permissions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    event = relationship("Event", back_populates="permissions")
    user = relationship("User", back_populates="permissions")

    __table_args__ = (
        Index('idx_permission_event_user', 'event_id', 'user_id', unique=True),
    )


class EventVersion(Base):
    __tablename__ = "event_versions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    version_number = Column(Integer)
    data = Column(JSON)
    changed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    event = relationship("Event", back_populates="versions")
    user = relationship("User", back_populates="versions")

    __table_args__ = (
        Index('idx_version_event', 'event_id', 'version_number'),
    )


class Changelog(Base):
    __tablename__ = "changelog"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    version_from = Column(Integer)
    version_to = Column(Integer)
    diff = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    event = relationship("Event", back_populates="changelog")

    __table_args__ = (
        Index('idx_changelog_event', 'event_id', 'created_at'),
    )


class EventConflict(Base):
    __tablename__ = "event_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    conflicting_event_id = Column(Integer, ForeignKey("events.id"))
    conflict_type = Column(String(20))
    resolution = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    event = relationship("Event", back_populates="conflicts", foreign_keys=[event_id])
    conflicting_event = relationship("Event", back_populates="conflicting_events", foreign_keys=[conflicting_event_id])

    __table_args__ = (
        Index('idx_conflict_events', 'event_id', 'conflicting_event_id'),
        Index('idx_conflict_resolution', 'resolution'),
    )


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="blacklisted_tokens") 