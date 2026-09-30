"""link supplier invoices to existing debts without duplicating payables"""

from alembic import op
import sqlalchemy as sa


revision = "j0e1f2a3b4c5"
down_revision = "i9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("supplier_invoices") as batch_op:
        batch_op.add_column(
            sa.Column("linked_current_entry_id", sa.Integer(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_supplier_invoices_linked_current_entry",
            "current_entries",
            ["linked_current_entry_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_supplier_invoices_linked_current_entry_id",
            ["linked_current_entry_id"],
            unique=False,
        )
        batch_op.alter_column(
            "current_entry_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade():
    op.execute("DELETE FROM supplier_invoices WHERE current_entry_id IS NULL")
    with op.batch_alter_table("supplier_invoices") as batch_op:
        batch_op.alter_column(
            "current_entry_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_index("ix_supplier_invoices_linked_current_entry_id")
        batch_op.drop_constraint(
            "fk_supplier_invoices_linked_current_entry",
            type_="foreignkey",
        )
        batch_op.drop_column("linked_current_entry_id")
