"""Модели ролей для контроля доступа."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.postgres import Base


class Role(Base):
    """Модель роли для хранения информации о ролях."""

    __tablename__ = 'roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    user_roles = relationship('UserRole', back_populates='role', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Role {self.name}>'


class UserRole(Base):
    """Связь Many-to-Many между Пользователями и Ролями."""

    __tablename__ = 'user_roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='uq_user_role'),)

    # Связи
    user = relationship('User', back_populates='roles')
    role = relationship('Role', back_populates='user_roles')

    def __repr__(self) -> str:
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'


class LoginHistory(Base):
    """Модель истории входов для отслеживания входов пользователей."""

    __tablename__ = 'login_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    login_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship('User', back_populates='login_history')

    def __repr__(self) -> str:
        return f'<LoginHistory user_id={self.user_id} login_at={self.login_at}>'


class RefreshToken(Base):
    """Модель refresh токена для хранения активных refresh токенов."""

    __tablename__ = 'refresh_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_jti = Column(String(36), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    user = relationship('User', back_populates='refresh_tokens')

    def __repr__(self) -> str:
        return f'<RefreshToken user_id={self.user_id} jti={self.token_jti}>'

