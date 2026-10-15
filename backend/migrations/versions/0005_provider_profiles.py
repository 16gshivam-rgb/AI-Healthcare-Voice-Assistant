"""Add provider profile details, qualifications, and recurring schedules."""

from alembic import op
import sqlalchemy as sa

revision = "0005_provider_profiles"
down_revision = "0004_auth_tenant_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("consultation_type", sa.String(32), nullable=False, server_default="in_person"))
    op.add_column("hospitals", sa.Column("address", sa.String(255), nullable=True))
    op.add_column("hospitals", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("hospitals", sa.Column("website", sa.String(255), nullable=True))
    op.add_column("hospitals", sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"))
    op.create_index("ix_hospitals_verification_status", "hospitals", ["verification_status"])
    op.execute("UPDATE hospitals SET verification_status = 'verified' WHERE verified = true")

    op.add_column("doctors", sa.Column("bio", sa.Text(), nullable=False, server_default=""))
    op.add_column("doctors", sa.Column("specialties", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("doctors", sa.Column("language_list", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("doctors", sa.Column("consultation_types", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("doctors", sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"))
    op.create_index("ix_doctors_verification_status", "doctors", ["verification_status"])
    op.execute("UPDATE doctors SET verification_status = 'verified' WHERE verified = true")

    op.create_table(
        "doctor_qualifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("degree", sa.String(120), nullable=False),
        sa.Column("institution", sa.String(180), nullable=False),
        sa.Column("completion_year", sa.Integer(), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.create_index("ix_doctor_qualifications_doctor_id", "doctor_qualifications", ["doctor_id"])

    op.create_table(
        "doctor_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.Time(), nullable=False),
        sa.Column("ends_at", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("consultation_type", sa.String(32), nullable=False, server_default="in_person"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_doctor_schedules_day_of_week"),
        sa.CheckConstraint("starts_at < ends_at", name="ck_doctor_schedules_time_order"),
    )
    op.create_index("ix_doctor_schedules_doctor_id", "doctor_schedules", ["doctor_id"])


def downgrade() -> None:
    op.drop_index("ix_doctor_schedules_doctor_id", table_name="doctor_schedules")
    op.drop_table("doctor_schedules")
    op.drop_index("ix_doctor_qualifications_doctor_id", table_name="doctor_qualifications")
    op.drop_table("doctor_qualifications")
    op.drop_column("appointments", "consultation_type")
    op.drop_index("ix_doctors_verification_status", table_name="doctors")
    op.drop_column("doctors", "verification_status")
    op.drop_column("doctors", "consultation_types")
    op.drop_column("doctors", "language_list")
    op.drop_column("doctors", "specialties")
    op.drop_column("doctors", "bio")
    op.drop_index("ix_hospitals_verification_status", table_name="hospitals")
    op.drop_column("hospitals", "verification_status")
    op.drop_column("hospitals", "website")
    op.drop_column("hospitals", "phone")
    op.drop_column("hospitals", "address")
