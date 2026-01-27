"""partition_login_history

Revision ID: partition_login_history_001
Revises: 6f0224c512bc
Create Date: 2026-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
from dateutil.relativedelta import relativedelta

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'partition_login_history_001'
down_revision: Union[str, Sequence[str], None] = '6f0224c512bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(connection, table_name: str) -> bool:
    """Проверить существование таблицы."""
    result = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            );
            """
        ),
        {'table_name': table_name}
    )
    return result.scalar()


def _partition_exists(connection, partition_name: str) -> bool:
    """Проверить существование партиции."""
    result = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = :partition_name
            );
            """
        ),
        {'partition_name': partition_name}
    )
    return result.scalar()


def upgrade() -> None:
    """Upgrade schema - создание партицированной таблицы login_history."""
    connection = op.get_bind()
    
    # Проверяем, не была ли уже выполнена миграция
    if _table_exists(connection, 'login_history_new'):
        # Если login_history_new существует, значит миграция частично выполнена
        # Удаляем все партиции и саму таблицу
        op.execute("""
            DO $$ 
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'login_history_%' AND tablename != 'login_history')
                LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        op.execute("DROP TABLE IF EXISTS login_history_new CASCADE;")
    
    # Проверяем, является ли текущая таблица уже партицированной
    result = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = 'login_history'
                AND c.relkind = 'p'
            );
        """)
    )
    is_partitioned = result.scalar()
    
    if is_partitioned:
        # Таблица уже партицирована, ничего не делаем
        return
    
    # Создаем новую партицированную таблицу
    op.execute("""
        CREATE TABLE login_history_new (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            login_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id, login_at),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) PARTITION BY RANGE (login_at);
    """)

    # Создаем партиции по месяцам на год вперед
    current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(12):
        # Используем правильный расчет месяцев
        partition_start = current_date + relativedelta(months=i)
        partition_end = current_date + relativedelta(months=i + 1)
        partition_name = f"login_history_{partition_start.strftime('%Y_%m')}"
        
        # Проверяем существование партиции перед созданием
        if not _partition_exists(connection, partition_name):
            op.execute(f"""
                CREATE TABLE {partition_name} PARTITION OF login_history_new
                FOR VALUES FROM ('{partition_start.isoformat()}') TO ('{partition_end.isoformat()}');
            """)

    # Копируем данные из старой таблицы в новую (если старая существует)
    if _table_exists(connection, 'login_history'):
        op.execute("""
            INSERT INTO login_history_new SELECT * FROM login_history;
        """)
        
        # Удаляем старую таблицу
        op.execute("DROP TABLE login_history CASCADE;")

    # Переименовываем новую таблицу
    op.execute("ALTER TABLE login_history_new RENAME TO login_history;")

    # Восстанавливаем индексы
    op.execute("CREATE INDEX IF NOT EXISTS ix_login_history_login_at ON login_history(login_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_login_history_user_id ON login_history(user_id);")


def downgrade() -> None:
    """Downgrade schema - возврат к обычной таблице."""
    connection = op.get_bind()
    
    # Проверяем, является ли таблица партицированной
    result = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = 'login_history'
                AND c.relkind = 'p'
            );
        """)
    )
    is_partitioned = result.scalar()
    
    if not is_partitioned:
        # Таблица не партицирована, ничего не делаем
        return
    
    # Создаем обычную таблицу
    op.execute("""
        CREATE TABLE login_history_old (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            login_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # Копируем данные из партицированной таблицы
    op.execute("""
        INSERT INTO login_history_old SELECT * FROM login_history;
    """)

    # Удаляем партицированную таблицу
    op.execute("DROP TABLE login_history CASCADE;")

    # Переименовываем старую таблицу
    op.execute("ALTER TABLE login_history_old RENAME TO login_history;")

    # Восстанавливаем индексы
    op.execute("CREATE INDEX IF NOT EXISTS ix_login_history_login_at ON login_history(login_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_login_history_user_id ON login_history(user_id);")
