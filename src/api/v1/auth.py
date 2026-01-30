"""API для аунтентификации и авторизации"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from requests_oauthlib import OAuth2Session
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.dependencies.auth import get_auth_service, get_current_user
from api.v1.dependencies.dependency import PaginationParams
from api.v1.scheme.auth_scheme import (
    LoginHistoryListResponse,
    LoginHistoryResponse,
    MessageResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from core.config import settings
from db.postgres import get_db
from models.user import User
from services.auth import AuthService
from services.oauth import OAuthService, register_yandex_user

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])


class LoginHistoryParams(PaginationParams):
    """Параметры пагинации для истории входов."""

    def __init__(
            self,
            page: int = Query(1, ge=1, description='Номер страницы'),
            size: int = Query(10, ge=1, le=100, description='Размер страницы'),
    ):
        """Инициализация параметров пагинации."""
        super().__init__(sort='', page=page, size=size)


@router.post(
    '/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
        user_data: UserRegister,
        auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Регистрация нового пользователя.

    Args:
        user_data: Данные для регистрации пользователя
        auth_service: Сервис аутентификации

    Returns:
        Созданный пользователь

    Raises:
        HTTPException: Если username или email уже существуют
    """
    try:
        user = await auth_service.register_user(user_data)
        return UserResponse.model_validate(user)
    except Exception as e:
        raise HTTPException(e)


@router.get("/authorize", summary="Получить ссылку на авторизацию Яндекс")
async def authorize():
    """
    Получение ссылки для авторизации через Яндекс.

    **return**: Ссылка на авторизацию в Яндексе
    """
    try:
        oauth = OAuth2Session(settings.oauth_yandex_client_id, redirect_uri=settings.oauth_yandex_client_secret)
        authorization_url, _ = oauth.authorization_url(settings.AUTHORIZATION_BASE_URL)
        return {"authorization_url": authorization_url}
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка получения ссылки")


@router.post("/callback", summary="Обработка кода и добавление в базу данных пользователя")
async def callback(
        response: Response,
        code: str = Query(..., description="Код подтверждения из Яндекса"),
        password: str = Query(..., description="Пароль")
):
    """
    Обработка кода подтверждения и регистрация пользователя через Яндекс.
    Параметры:
    - **response**: Объект ответа для установки access-токена в куки
    - **code**: Код подтверждения из Яндекса
    - **password**: Пароль для создания учетной записи
    **return**: Access-токен в ответе и куки
    """
    try:
        oauth = OAuth2Session(settings.oauth_yandex_client_id, redirect_uri=settings.oauth_yandex_client_secret)
        token = oauth.fetch_token(settings.TOKEN_URL, client_secret=settings.oauth_yandex_client_secret, code=code)
        access_token = token.get("access_token")


        # Устанавливаем access_token в куки
        response.set_cookie(
            key="yandex_access_token",
            value=access_token,
            httponly=True,
        )


        await register_yandex_user(access_token, password)

        return {"access_token": access_token}
    except Exception:
        raise HTTPException(status_code=400, detail="Получите код")


@router.post('/login', response_model=TokenResponse)
async def login(
        response: Response,
        credentials: UserLogin,
        request: Request,
        auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Вход пользователя и получение JWT токенов.

    Args:
        response: Response объект для установки куков
        credentials: Учетные данные для входа
        request: FastAPI запрос (для получения IP и User-Agent)
        auth_service: Сервис аутентификации

    Returns:
        Access и refresh токены

    Raises:
        HTTPException: Если аутентификация не удалась
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get('User-Agent')

    result = await auth_service.authenticate_user(
        credentials.username,
        credentials.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверное имя пользователя или пароль',
        )

    user, access_token, refresh_token = result

    # Устанавливаем токены в куки
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=False,  # В продакшене должно быть True
        samesite='lax',
        max_age=1800,  # 30 минут (в секундах)
    )

    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite='lax',
        max_age=604800,  # 7 дней (в секундах)
    )

    # Также возвращаем токены в теле ответа (опционально)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
    )


@router.post('/refresh', response_model=TokenResponse)
async def refresh_token(
        request: Request,
        response: Response,
        auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Обновить access токен с помощью refresh токена.

    Args:
        request: FastAPI запрос (для получения кук)
        response: Response объект для обновления куков
        auth_service: Сервис аутентификации

    Returns:
        Новый access токен

    Raises:
        HTTPException: Если токен невалиден или истек
    """
    # Получаем refresh_token из куков
    refresh_token = request.cookies.get('refresh_token')

    if not refresh_token:
        # Пробуем получить из заголовка (для обратной совместимости)
        authorization = request.headers.get('Authorization')
        if authorization and authorization.startswith('Bearer '):
            refresh_token = authorization.split(' ')[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh токен не найден в куках',
            )

    result = await auth_service.refresh_access_token(refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный или истекший токен',
        )

    access_token, user_id = result

    # Обновляем access_token в куках
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=False,
        samesite='lax',
        max_age=1800,
    )

    # Также можно вернуть новый refresh_token, если используется ротация токенов
    # В этом примере refresh_token остается тем же

    return TokenResponse(
        access_token=access_token,
        token_type='bearer',
    )


@router.post('/logout', response_model=MessageResponse)
async def logout(
        request: Request,
        response: Response,
        auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Выход пользователя из системы путем отзыва refresh токена.

    Args:
        request: FastAPI запрос (для получения кук)
        response: Response объект для удаления куков
        auth_service: Сервис аутентификации

    Returns:
        Сообщение об успешном выходе

    Raises:
        HTTPException: Если токен невалиден
    """
    # Получаем refresh_token из куков
    refresh_token = request.cookies.get('refresh_token')

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Refresh токен не найден в куках',
        )

    success = await auth_service.logout(refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный токен',
        )

    # Удаляем куки
    response.delete_cookie(key='access_token')
    response.delete_cookie(key='refresh_token')

    return MessageResponse(message='Успешный выход из системы')


@router.post('/logout-all', response_model=MessageResponse)
async def logout_all(
        response: Response,
        current_user: User = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Выход пользователя из всех устройств.

    Args:
        response: Response объект для удаления куков
        current_user: Текущий аутентифицированный пользователь
        auth_service: Сервис аутентификации

    Returns:
        Сообщение об успешном выходе
    """
    await auth_service.logout_all(current_user.id)

    # Удаляем куки
    response.delete_cookie(key='access_token')
    response.delete_cookie(key='refresh_token')

    return MessageResponse(message='Успешный выход из всех устройств')


@router.patch('/profile', response_model=UserResponse)
async def update_profile(
        update_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Обновить профиль пользователя (логин и/или пароль).

    Args:
        update_data: Данные для обновления
        current_user: Текущий аутентифицированный пользователь
        auth_service: Сервис аутентификации

    Returns:
        Обновленный пользователь

    Raises:
        HTTPException: Если username уже существует или валидация не прошла
    """
    if not update_data.username and not update_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Необходимо указать хотя бы одно поле (username или password)',
        )

    try:
        updated_user = await auth_service.update_user_profile(
            current_user.id, update_data
        )
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Пользователь не найден',
            )
        return UserResponse.model_validate(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get('/login-history', response_model=LoginHistoryListResponse)
async def get_login_history(
        pagination: LoginHistoryParams = Depends(),
        current_user: User = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service),
) -> LoginHistoryListResponse:
    """
    Получить историю входов текущего пользователя.

    Args:
        pagination: Параметры пагинации
        current_user: Текущий аутентифицированный пользователь
        auth_service: Сервис аутентификации

    Returns:
        История входов с пагинацией
    """
    items, total = await auth_service.get_login_history(
        current_user.id,
        page=pagination.page,
        size=pagination.size,
    )

    import math

    pages = math.ceil(total / pagination.size) if total > 0 else 0

    return LoginHistoryListResponse(
        items=[LoginHistoryResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )


@router.get('/verify', response_model=UserResponse)
async def verify_token(
        request: Request,
        db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Проверить токен и вернуть информацию о пользователе.
    Используется другими сервисами для проверки токена.

    Args:
        request: FastAPI запрос (для получения токена)
        db: Сессия базы данных

    Returns:
        Информация о пользователе

    Raises:
        HTTPException: Если токен невалиден
    """
    # Получаем токен из заголовка Authorization
    authorization = request.headers.get('Authorization')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Токен не предоставлен',
        )

    token = authorization.split(' ')[1]

    # Проверяем токен через JWT сервис
    from core.jwt import jwt_service

    payload = jwt_service.verify_token(token, token_type='access')
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный токен',
        )

    user_id_str = payload.get('sub')
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный токен',
        )

    user_id = UUID(user_id_str)

    # Получаем пользователя из базы данных
    from db.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )
    return UserResponse.model_validate(user)


@router.get('/users/{user_id}', response_model=UserResponse)
async def get_user_info(
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Получить информацию о пользователе по ID.
    Используется другими сервисами для получения информации о пользователе.

    Args:
        user_id: UUID пользователя
        db: Сессия базы данных

    Returns:
        Информация о пользователе

    Raises:
        HTTPException: Если пользователь не найден
    """
    from db.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )
    return UserResponse.model_validate(user)
