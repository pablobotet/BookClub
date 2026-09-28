"""Create auditable next-book selections.

Revision ID: 20260928_0003
Revises: 20260928_0002
Create Date: 2026-09-28
"""

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_0003"
down_revision: str | None = "20260928_0002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "selections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("book_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("candidate_book_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "candidate_count > 0", name="ck_selections_candidate_count"
        ),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(
            ["group_id"], ["reading_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_selections_book_id"), "selections", ["book_id"], unique=False
    )
    op.create_index(
        op.f("ix_selections_group_id"), "selections", ["group_id"], unique=False
    )
    op.create_index(
        op.f("ix_selections_requested_by_user_id"),
        "selections",
        ["requested_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_selections_requested_by_user_id"), table_name="selections"
    )
    op.drop_index(op.f("ix_selections_group_id"), table_name="selections")
    op.drop_index(op.f("ix_selections_book_id"), table_name="selections")
    op.drop_table("selections")
