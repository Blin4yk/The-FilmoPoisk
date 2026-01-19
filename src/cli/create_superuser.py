"""CLI команда для создания суперпользователя."""
import asyncio
from getpass import getpass

import typer
from core.security import get_password_hash
from db.postgres import AsyncSessionLocal
from db.repositories.user_repository import UserRepository


async def _create_superuser(username: str, email: str, password: str) -> None:
    """
    Создать суперпользователя в базе данных.

    Args:
        username: Имя пользователя
        email: Email
        password: Пароль в открытом виде
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)

        existing_email = await user_repo.get_by_email(email)
        if existing_email:
            typer.echo(
                f'Ошибка: Пользователь с email "{email}" уже существует', err=True
            )
            raise typer.Exit(code=1)

        # Хешируем пароль
        password_hash = get_password_hash(password)

        # Создаем суперпользователя
        user = await user_repo.create(
            username=username,
            email=email,
            password_hash=password_hash,
            is_superuser=True,
        )

        typer.echo(f'Суперпользователь "{username}" успешно создан с ID: {user.id}')


def create_superuser(
    username: str = typer.Option(None, '--username', '-u', help='Имя пользователя'),
    email: str = typer.Option(None, '--email', '-e', help='Email'),
    password: str = typer.Option(None, '--password', '-p', help='Пароль'),
) -> None:
    """
    Создать учетную запись суперпользователя.

    Если username, email или password не предоставлены как опции,
    они будут запрошены интерактивно.
    """
    # Получаем username
    if not username:
        username = typer.prompt('Имя пользователя')

    # Получаем email
    if not email:
        email = typer.prompt('Email')

    # Получаем пароль
    if not password:
        password = getpass('Пароль: ')
        password_confirm = getpass('Подтвердите пароль: ')
        if password != password_confirm:
            typer.echo('Ошибка: Пароли не совпадают', err=True)
            raise typer.Exit(code=1)

    if '@' not in email:
        typer.echo('Ошибка: Неверный формат email', err=True)
        raise typer.Exit(code=1)

    # Создаем суперпользователя
    asyncio.run(_create_superuser(username, email, password))
