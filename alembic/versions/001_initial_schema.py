"""Initial schema creation.

Revision ID: 001
Revises:
Create Date: 2026-02-15 05:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the initial schema."""
    # Create detections table
    op.create_table(
        "detections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("class_name", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_timestamp", "detections", ["timestamp"])

    # Create offline_queue table
    op.create_table(
        "offline_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("detection_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_synced_at", "offline_queue", ["synced_at"])

    # Create audit_trail table
    op.create_table(
        "audit_trail",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_timestamp", "audit_trail", ["timestamp"])


def downgrade() -> None:
    """Revert the initial schema."""
    op.drop_index("idx_audit_timestamp", table_name="audit_trail")
    op.drop_table("audit_trail")
    op.drop_index("idx_synced_at", table_name="offline_queue")
    op.drop_table("offline_queue")
    op.drop_index("idx_timestamp", table_name="detections")
    op.drop_table("detections")
