"""profile soft delete

Revision ID: 7a1e6b4c2d11
Revises: 889d2adc1dab
Create Date: 2026-04-06 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a1e6b4c2d11'
down_revision: Union[str, Sequence[str], None] = '889d2adc1dab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_profiles', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_profiles', 'deleted_at')
