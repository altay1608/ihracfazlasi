"""add shared barcode mode for bulk-counted products"""

from alembic import op
import sqlalchemy as sa


revision = "g7b8c9d0e1f2"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("barcode_mode", sa.String(length=20), nullable=False, server_default="unit"))

    with op.batch_alter_table("inventory_count_scans") as batch_op:
        batch_op.drop_constraint("uq_inventory_count_scans_count_barcode", type_="unique")


def downgrade():
    with op.batch_alter_table("inventory_count_scans") as batch_op:
        batch_op.create_unique_constraint(
            "uq_inventory_count_scans_count_barcode",
            ["inventory_count_id", "product_barcode_id"],
        )

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("barcode_mode")
