"""pg question new

Revision ID: 2f3d2be4c9fa
Revises: 5b442f2da6e4
Create Date: 2024-12-11 10:07:59.841287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2f3d2be4c9fa'
down_revision: Union[str, None] = '5b442f2da6e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('initial_playground_question',
    sa.Column('starter_code', sa.String(), nullable=False),
    sa.Column('solution_code', sa.String(), nullable=False),
    sa.Column('solution_time_complexity', sa.String(), nullable=False),
    sa.Column('test_case_list', sa.String(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('example_io_list', sa.String(), nullable=False),
    sa.Column('created_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_created_playground_question',
    sa.Column('custom_user_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('example_io_list', sa.String(), nullable=False),
    sa.Column('created_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['custom_user_id'], ['custom_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('playground_question')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('playground_question',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('text', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('starter_code', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('solution_code', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('solution_time_complexity', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('example_io_list', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('test_case_list', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_date', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='playground_question_pkey')
    )
    op.drop_table('user_created_playground_question')
    op.drop_table('initial_playground_question')
    # ### end Alembic commands ###
