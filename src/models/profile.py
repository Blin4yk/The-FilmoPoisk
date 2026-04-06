import uuid
from datetime import datetime, timezone

from db.postgres import Base
from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID


class UserProfile(Base):
    __tablename__ = 'user_profiles'
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_profiles_user_id'),
        UniqueConstraint('phone', name='uq_user_profiles_phone'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(32), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f'<UserProfile {self.user_id} {self.phone}>'

