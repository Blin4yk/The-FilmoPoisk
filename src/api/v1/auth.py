"""API для аунтентификации и авторизации"""

from models.user import User

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
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginHistoryParams(PaginationParams):
    """Параметры пагинации для истории входов."""

    def __init__(
            self,
            page: int = Query(1, ge=1, description='Номер страницы'),
            size: int = Query(10, ge=1, le=100, description='Размер страницы'),
    ):
        """Инициализация параметров пагинации."""
        super().__init__(sort='', page=page, size=size)


@router.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.post('/login', response_model=TokenResponse)
async def login(
        credentials: UserLogin,
        request: Request,
        auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Вход пользователя и получение JWT токенов.

    Args:
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
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
    )


@router.post('/refresh', response_model=TokenResponse)
async def refresh_token(
        request: Request,
        auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Обновить access токен с помощью refresh токена.

    Args:
        request: FastAPI запрос (для заголовка Authorization)
        auth_service: Сервис аутентификации

    Returns:
        Новый access токен

    Raises:
        HTTPException: Если токен невалиден или истек
    """
    authorization = request.headers.get('Authorization')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный формат токена',
        )

    refresh_token = authorization.split(' ')[1]
    result = await auth_service.refresh_access_token(refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный или истекший токен',
        )

    access_token, _ = result
    return TokenResponse(
        access_token=access_token,
        token_type='bearer',
    )


@router.post('/logout', response_model=MessageResponse)
async def logout(
        request: Request,
        auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Выход пользователя из системы путем отзыва refresh токена.

    Args:
        request: FastAPI запрос (для заголовка Authorization)
        auth_service: Сервис аутентификации

    Returns:
        Сообщение об успешном выходе

    Raises:
        HTTPException: Если токен невалиден
    """
    authorization = request.headers.get('Authorization')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный формат токена',
        )

    refresh_token = authorization.split(' ')[1]
    success = await auth_service.logout(refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный токен',
        )

    return MessageResponse(message='Успешный выход из системы')


@router.post('/logout-all', response_model=MessageResponse)
async def logout_all(
        current_user: User = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Выход пользователя из всех устройств.

    Args:
        current_user: Текущий аутентифицированный пользователь
        auth_service: Сервис аутентификации

    Returns:
        Сообщение об успешном выходе
    """
    await auth_service.logout_all(current_user.id)
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
        updated_user = await auth_service.update_user_profile(current_user.id, update_data)
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
