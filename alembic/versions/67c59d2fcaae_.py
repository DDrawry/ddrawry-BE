"""empty message

Revision ID: 67c59d2fcaae
Revises: f5f1179a76ce
Create Date: 2024-10-13 22:50:24.411095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67c59d2fcaae'
down_revision: Union[str, None] = 'f5f1179a76ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('temp_diary', sa.Column('image', sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('temp_diary', 'image')
    # ### end Alembic commands ###
