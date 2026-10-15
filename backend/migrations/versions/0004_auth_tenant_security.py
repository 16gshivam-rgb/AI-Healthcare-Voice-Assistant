"""Add hospital-scoped roles, revocable sessions, reset tokens, and audit records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "0004_auth_tenant_security"
down_revision = "0003_knowledge_base"
branch_labels = None
depends_on = None

ROLES = "'patient', 'doctor', 'hospital_staff', 'hospital_admin', 'platform_admin'"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "hospital_id" not in user_columns:
        op.add_column("users", sa.Column("hospital_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_users_hospital_id_hospitals",
            "users",
            "hospitals",
            ["hospital_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_users_hospital_id", "users", ["hospital_id"])
    if "doctor_id" not in user_columns:
        op.add_column("users", sa.Column("doctor_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_users_doctor_id_doctors",
            "users",
            "doctors",
            ["doctor_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_users_doctor_id", "users", ["doctor_id"], unique=True)

    bind.execute(text("UPDATE users SET role = 'hospital_staff' WHERE role = 'staff'"))
    bind.execute(text("UPDATE users SET role = 'platform_admin' WHERE role = 'admin'"))
    op.create_check_constraint("ck_users_role_allowed", "users", f"role IN ({ROLES})")

    invoice_columns = {column["name"] for column in inspector.get_columns("invoices")}
    if "hospital_id" not in invoice_columns:
        op.add_column("invoices", sa.Column("hospital_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_invoices_hospital_id_hospitals",
            "invoices",
            "hospitals",
            ["hospital_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_invoices_hospital_id", "invoices", ["hospital_id"])

    if "auth_sessions" not in tables:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    if "password_reset_tokens" not in tables:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
        op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])

    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("resource_type", sa.String(80), nullable=True),
            sa.Column("resource_id", sa.String(80), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(512), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
        op.create_index("ix_audit_logs_hospital_id", "audit_logs", ["hospital_id"])
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())
    if "audit_logs" in existing:
        for index in inspector.get_indexes("audit_logs"):
            op.drop_index(index["name"], table_name="audit_logs")
        op.drop_table("audit_logs")
    if "password_reset_tokens" in existing:
        for index in inspector.get_indexes("password_reset_tokens"):
            op.drop_index(index["name"], table_name="password_reset_tokens")
        op.drop_table("password_reset_tokens")
    if "auth_sessions" in existing:
        for index in inspector.get_indexes("auth_sessions"):
            op.drop_index(index["name"], table_name="auth_sessions")
        op.drop_table("auth_sessions")

    op.drop_constraint("ck_users_role_allowed", "users", type_="check")
    invoice_columns = {column["name"] for column in inspector.get_columns("invoices")}
    if "hospital_id" in invoice_columns:
        op.drop_index("ix_invoices_hospital_id", table_name="invoices")
        op.drop_constraint("fk_invoices_hospital_id_hospitals", "invoices", type_="foreignkey")
        op.drop_column("invoices", "hospital_id")
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "doctor_id" in user_columns:
        op.drop_index("ix_users_doctor_id", table_name="users")
        op.drop_constraint("fk_users_doctor_id_doctors", "users", type_="foreignkey")
        op.drop_column("users", "doctor_id")
    if "hospital_id" in user_columns:
        op.drop_index("ix_users_hospital_id", table_name="users")
        op.drop_constraint("fk_users_hospital_id_hospitals", "users", type_="foreignkey")
        op.drop_column("users", "hospital_id")
    bind.execute(text("UPDATE users SET role = 'staff' WHERE role = 'hospital_staff'"))
    bind.execute(text("UPDATE users SET role = 'admin' WHERE role = 'platform_admin'"))
