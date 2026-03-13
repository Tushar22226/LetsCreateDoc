"""add_theme_color_to_projects

Revision ID: 33e8f8167a91
Revises: cc97d99019d2
Create Date: 2026-03-13 13:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33e8f8167a91'
down_revision: Union[str, Sequence[str], None] = 'cc97d99019d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'projects',
        sa.Column('theme_color', sa.String(length=7), nullable=False, server_default='#1F4E79'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('projects', 'theme_color')
