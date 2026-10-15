"""Add hospitals, doctors, and appointment records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_doctors_appointments"
down_revision = "0001_portal_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())

    if "hospitals" not in existing:
        op.create_table(
            "hospitals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("city", sa.String(80), nullable=False),
            sa.Column("state", sa.String(80), nullable=False),
            sa.Column("departments", sa.Text(), nullable=False, server_default="General Medicine"),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_hospitals_name", "hospitals", ["name"])
        op.create_index("ix_hospitals_city", "hospitals", ["city"])
        op.create_index("ix_hospitals_state", "hospitals", ["state"])

    if "doctors" not in existing:
        op.create_table(
            "doctors",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True),
            sa.Column("full_name", sa.String(120), nullable=False),
            sa.Column("specialty", sa.String(120), nullable=False),
            sa.Column("languages", sa.String(255), nullable=False, server_default="English"),
            sa.Column("fee_minor", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consultation_mode", sa.String(32), nullable=False, server_default="in_person"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_doctors_hospital_id", "doctors", ["hospital_id"])
        op.create_index("ix_doctors_full_name", "doctors", ["full_name"])
        op.create_index("ix_doctors_specialty", "doctors", ["specialty"])

    if "appointments" not in existing:
        op.create_table(
            "appointments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("patient_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
            sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True),
            sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_appointments_patient_user_id", "appointments", ["patient_user_id"])
        op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
        op.create_index("ix_appointments_scheduled_for", "appointments", ["scheduled_for"])


def downgrade() -> None:
    op.drop_index("ix_appointments_scheduled_for", table_name="appointments")
    op.drop_index("ix_appointments_doctor_id", table_name="appointments")
    op.drop_index("ix_appointments_patient_user_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index("ix_doctors_specialty", table_name="doctors")
    op.drop_index("ix_doctors_full_name", table_name="doctors")
    op.drop_index("ix_doctors_hospital_id", table_name="doctors")
    op.drop_table("doctors")
    op.drop_index("ix_hospitals_state", table_name="hospitals")
    op.drop_index("ix_hospitals_city", table_name="hospitals")
    op.drop_index("ix_hospitals_name", table_name="hospitals")
    op.drop_table("hospitals")
