"""Утилиты безопасности для хеширования паролей."""
from passlib.context import CryptContext

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto', bcrypt__rounds=12)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль против его хеша.

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хешированный пароль

    Returns:
        True если пароль совпадает, False в противном случае
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Захешировать пароль.

    Args:
        password: Пароль в открытом виде

    Returns:
        Хешированный пароль
    """
    return pwd_context.hash(password)

