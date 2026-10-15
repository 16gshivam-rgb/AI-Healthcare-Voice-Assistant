"""Link invoices to appointments and prevent duplicate appointment invoices."""

from alembic import op
import sqlalchemy as sa

revision = "0011_appointment_invoices"
down_revision = "0010_admin_bootstrap_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("appointment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_invoices_appointment_id_appointments",
        "invoices",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_invoices_appointment_id", "invoices", ["appointment_id"])
    op.create_unique_constraint("uq_invoices_appointment_id", "invoices", ["appointment_id"])


def downgrade() -> None:
    op.drop_constraint("uq_invoices_appointment_id", "invoices", type_="unique")
    op.drop_index("ix_invoices_appointment_id", table_name="invoices")
    op.drop_constraint("fk_invoices_appointment_id_appointments", "invoices", type_="foreignkey")
    op.drop_column("invoices", "appointment_id")
