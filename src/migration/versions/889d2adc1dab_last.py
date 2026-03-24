"""last

Revision ID: 889d2adc1dab
Revises: 058bf0852d30
Create Date: 2026-03-23 14:34:53.570499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '889d2adc1dab'
down_revision: Union[str, Sequence[str], None] = '058bf0852d30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
