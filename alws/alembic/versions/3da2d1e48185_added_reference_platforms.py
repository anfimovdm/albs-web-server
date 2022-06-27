"""Added reference platforms

Revision ID: 3da2d1e48185
Revises: 2af59b3b1a4d
Create Date: 2022-02-14 08:17:11.709795

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3da2d1e48185'
down_revision = '6f8e782397d2'
down_revision = '2af59b3b1a4d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('reference_platforms',
    sa.Column('platform_id', sa.Integer(), nullable=False),
    sa.Column('refefence_platform_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['platform_id'], ['platforms.id'], ),
    sa.ForeignKeyConstraint(['refefence_platform_id'], ['platforms.id'], ),
    sa.PrimaryKeyConstraint('platform_id', 'refefence_platform_id')
    )
    op.add_column('platforms', sa.Column('is_reference', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('platforms', 'is_reference')
    op.drop_table('reference_platforms')
    # ### end Alembic commands ###
