"""Точка входа CLI."""
import asyncio
from getpass import getpass

import typer
from cli.create_superuser import _create_superuser

main_app = typer.Typer()


@main_app.command('create-superuser')
def create_superuser_cmd(
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


def cli() -> None:
    """Точка входа для CLI."""
    main_app()


if __name__ == '__main__':
    cli()
