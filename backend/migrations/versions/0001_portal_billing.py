"""Add account-owned profiles and invoice/payment storage.

Revision ID: 0001_portal_billing
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "0001_portal_billing"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("full_name", sa.String(120), nullable=False),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="patient"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "patients" not in tables:
        op.create_table(
            "patients",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("full_name", sa.String(120), nullable=False),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("age", sa.Integer(), nullable=False),
            sa.Column("gender", sa.String(24), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_patients_email", "patients", ["email"], unique=True)
        op.create_index("ix_patients_full_name", "patients", ["full_name"])

    patient_columns = {column["name"] for column in inspect(bind).get_columns("patients")}
    if "owner_user_id" not in patient_columns:
        op.add_column("patients", sa.Column("owner_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_patients_owner_user_id_users",
            "patients",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    index_names = {index["name"] for index in inspect(bind).get_indexes("patients")}
    if "ix_patients_owner_user_id" not in index_names:
        op.create_index("ix_patients_owner_user_id", "patients", ["owner_user_id"])

    bind.execute(
        text(
            "UPDATE patients SET owner_user_id = "
            "(SELECT users.id FROM users WHERE lower(users.email) = lower(patients.email) LIMIT 1) "
            "WHERE owner_user_id IS NULL"
        )
    )

    if "invoices" not in set(inspect(bind).get_table_names()):
        op.create_table(
            "invoices",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("invoice_number", sa.String(40), nullable=False, unique=True),
            sa.Column("description", sa.String(240), nullable=False),
            sa.Column("amount_minor", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("status", sa.String(16), nullable=False, server_default="unpaid"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_invoices_owner_user_id", "invoices", ["owner_user_id"])

    if "payments" not in set(inspect(bind).get_table_names()):
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider_order_id", sa.String(80), nullable=False, unique=True),
            sa.Column("provider_payment_id", sa.String(80), nullable=True, unique=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="created"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_invoices_owner_user_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("ix_patients_owner_user_id", table_name="patients")
    op.drop_constraint("fk_patients_owner_user_id_users", "patients", type_="foreignkey")
    op.drop_column("patients", "owner_user_id")
