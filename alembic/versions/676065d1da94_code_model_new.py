"""code model new

Revision ID: 676065d1da94
Revises: cf28ee1dbfef
Create Date: 2024-12-15 22:39:59.152547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '676065d1da94'
down_revision: Union[str, None] = 'cf28ee1dbfef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('playground_chat_conversation',
    sa.Column('code', sa.String(), nullable=True),
    sa.Column('question_object_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('question', sa.String(), nullable=False),
    sa.Column('prompt', sa.String(), nullable=False),
    sa.Column('response', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['question_object_id'], ['user_created_playground_question.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('playground_chat_conversation')
    # ### end Alembic commands ###
