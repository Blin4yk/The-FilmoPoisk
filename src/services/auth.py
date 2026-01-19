"""Сервис аутентификации."""

from uuid import UUID

from api.v1.scheme.auth_scheme import UserRegister, UserUpdate
from core.jwt import jwt_service
from core.security import get_password_hash, verify_password
from db.interface.interfaces import AbstractCache
from db.repositories.login_history_repository import LoginHistoryRepository
from db.repositories.refresh_token_repository import RefreshTokenRepository
from db.repositories.role_repository import RoleRepository
from db.repositories.user_repository import UserRepository
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    """Сервис для операций аутентификации."""

    def __init__(
        self,
        session: AsyncSession,
        cache: AbstractCache,
    ):
        """
        Инициализация сервиса аутентификации.

        Args:
            session: Сессия базы данных
            cache: Хранилище кэша
        """
        self.session = session
        self.cache = cache
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.login_history_repo = LoginHistoryRepository(session)
        self.refresh_token_repo = RefreshTokenRepository(session)

    async def register_user(self, user_data: UserRegister) -> User:
        """
        Зарегистрировать нового пользователя.

        Args:
            user_data: Данные для регистрации пользователя

        Returns:
            Созданный объект User

        Raises:
            ValueError: Если username или email уже существуют
        """
        # Проверяем, существует ли username
        existing_user = await self.user_repo.get_by_username(user_data.username)
        if existing_user:
            raise ValueError('Пользователь с таким username уже существует')

        # Проверяем, существует ли email
        existing_email = await self.user_repo.get_by_email(user_data.email)
        if existing_email:
            raise ValueError('Пользователь с таким email уже существует')

        # Хешируем пароль
        password_hash = get_password_hash(user_data.password)

        # Создаем пользователя
        user = await self.user_repo.create(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
        )

        return user

    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str] | None:
        """
        Аутентифицировать пользователя и вернуть токены.

        Args:
            username: Имя пользователя
            password: Пароль в открытом виде
            ip_address: IP адрес (опционально)
            user_agent: User agent (опционально)

        Returns:
            Кортеж из (User, access_token, refresh_token) или None если аутентификация не удалась
        """
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Получаем роли пользователя
        roles = await self.role_repo.get_user_roles(user.id)
        role_names = [role.name for role in roles]

        # Получаем поколение пользователя (для функции logout-all)
        generation = await self._get_user_generation(user.id)

        # Создаем токены
        access_token = jwt_service.create_access_token(
            user_id=str(user.id),
            username=user.username,
            is_superuser=user.is_superuser,
            roles=role_names,
            generation=generation,
        )
        refresh_token, jti = jwt_service.create_refresh_token(str(user.id))

        # Сохраняем refresh токен в базу данных
        from datetime import datetime, timedelta

        expires_at = datetime.utcnow() + timedelta(
            days=jwt_service.refresh_token_expire_days
        )
        await self.refresh_token_repo.create(user.id, jti, expires_at)

        # Сохраняем историю входа
        await self.login_history_repo.create(user.id, ip_address, user_agent)

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, UUID] | None:
        """
        Обновить access токен с помощью refresh токена.

        Args:
            refresh_token: JWT refresh токен

        Returns:
            Кортеж из (новый_access_token, user_id) или None если невалиден
        """
        payload = jwt_service.verify_token(refresh_token, token_type='refresh')

        if not payload:
            return None

        jti = payload.get('jti')
        if not jti:
            return None

        # Проверяем, находится ли токен в blacklist
        blacklist_key = f'refresh_token:blacklist:{jti}'
        if await self.cache.get(blacklist_key):
            return None

        # Проверяем, существует ли токен в базе данных
        token_record = await self.refresh_token_repo.get_by_jti(jti)
        if not token_record:
            return None

        user_id = UUID(payload['sub'])
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        # Получаем роли пользователя
        roles = await self.role_repo.get_user_roles(user.id)
        role_names = [role.name for role in roles]

        # Получаем поколение пользователя
        generation = await self._get_user_generation(user.id)

        # Создаем новый access токен
        access_token = jwt_service.create_access_token(
            user_id=str(user.id),
            username=user.username,
            is_superuser=user.is_superuser,
            roles=role_names,
            generation=generation,
        )

        return access_token, user_id

    async def logout(self, refresh_token: str) -> bool:
        """
        Выйти пользователя из системы путем отзыва refresh токена.

        Args:
            refresh_token: JWT refresh токен

        Returns:
            True если выход успешен
        """
        payload = jwt_service.verify_token(refresh_token, token_type='refresh')
        if not payload:
            return False

        jti = payload.get('jti')
        if not jti:
            return False

        # Добавляем в blacklist в Redis (с TTL равным оставшемуся времени жизни токена)
        exp = payload.get('exp')
        if exp:
            from datetime import datetime

            current_time = datetime.utcnow().timestamp()
            ttl = int(exp - current_time)  # Оставшееся время в секундах
            if ttl > 0:
                blacklist_key = f'refresh_token:blacklist:{jti}'
                await self.cache.set(blacklist_key, '1', expire=ttl)

        # Также удаляем из базы данных (опционально, для очистки)
        await self.refresh_token_repo.delete_by_jti(jti)
        return True

    async def logout_all(self, user_id: UUID) -> None:
        """
        Выйти пользователя из всех устройств путем увеличения поколения.

        Args:
            user_id: UUID пользователя
        """

        # Инвалидируем кэш
        await self._invalidate_user_cache(user_id)

        # Удаляем все refresh токены пользователя
        await self.refresh_token_repo.delete_all_by_user_id(user_id)

    async def update_user_profile(self, user_id: UUID, update_data: UserUpdate) -> User:
        """
        Обновить профиль пользователя (логин и/или пароль).

        Args:
            user_id: UUID пользователя
            update_data: Данные для обновления

        Returns:
            Обновленный объект User

        Raises:
            ValueError: Если новый username уже существует или пользователь не найден
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('Пользователь не найден')

        # Проверяем уникальность username при изменении
        if update_data.username and update_data.username != user.username:
            existing_user = await self.user_repo.get_by_username(update_data.username)
            if existing_user:
                raise ValueError('Пользователь с таким username уже существует')

        # Хешируем новый пароль, если предоставлен
        new_password_hash = None
        if update_data.password:
            new_password_hash = get_password_hash(update_data.password)

        # Обновляем пользователя
        updated_user = await self.user_repo.update_username_and_password(
            user_id, update_data.username, new_password_hash
        )

        # Инвалидируем кэш
        await self._invalidate_user_cache(user_id)

        return updated_user

    async def get_login_history(
        self, user_id: UUID, page: int = 1, size: int = 10
    ) -> tuple[list, int]:
        """
        Получить историю входов пользователя.

        Args:
            user_id: UUID пользователя
            page: Номер страницы
            size: Размер страницы

        Returns:
            Кортеж из (список записей истории входов, общее количество)
        """
        return await self.login_history_repo.get_by_user_id(user_id, page, size)

    async def _get_user_generation(self, user_id: UUID) -> int:
        """
        Получить номер поколения пользователя из кэша или вернуть 0 по умолчанию.

        Args:
            user_id: UUID пользователя

        Returns:
            Номер поколения
        """
        cache_key = f'user:generation:{user_id}'
        cached = await self.cache.get(cache_key)
        if cached:
            return int(cached)
        return 0

    async def _increment_user_generation(self, user_id: UUID) -> int:
        """
        Увеличить номер поколения пользователя.

        Args:
            user_id: UUID пользователя

        Returns:
            Новый номер поколения
        """
        current = await self._get_user_generation(user_id)
        new_generation = current + 1
        cache_key = f'user:generation:{user_id}'
        # Устанавливаем TTL равным дням истечения refresh токена (чтобы не истек раньше токенов)
        ttl = jwt_service.refresh_token_expire_days * 86400
        await self.cache.set(cache_key, str(new_generation), expire=ttl)
        return new_generation

    async def _invalidate_user_cache(self, user_id: UUID) -> None:
        """
        Инвалидировать кэш-записи, связанные с пользователем.

        Args:
            user_id: UUID пользователя
        """
        await self.cache.delete(f'user:{user_id}')
        await self.cache.delete(f'user:roles:{user_id}')
