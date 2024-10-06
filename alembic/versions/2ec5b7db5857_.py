"""empty message

Revision ID: 2ec5b7db5857
Revises: ddc7f0bbc1b9
Create Date: 2024-10-06 17:43:10.214626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2ec5b7db5857'
down_revision: Union[str, None] = 'ddc7f0bbc1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('temp_diary', 'created_at',
               existing_type=mysql.TIMESTAMP(),
               nullable=True)
    op.alter_column('temp_diary', 'updated_at',
               existing_type=mysql.TIMESTAMP(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('temp_diary', 'updated_at',
               existing_type=mysql.TIMESTAMP(),
               nullable=False)
    op.alter_column('temp_diary', 'created_at',
               existing_type=mysql.TIMESTAMP(),
               nullable=False)
    # ### end Alembic commands ###
