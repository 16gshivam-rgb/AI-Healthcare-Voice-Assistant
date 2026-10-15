"""Add idempotent transactional booking, slot locks, and appointment history."""

from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0006_transactional_appointments"
down_revision = "0005_provider_profiles"
branch_labels = None
depends_on = None

ACTIVE_STATUSES = {"scheduled", "confirmed"}


def upgrade() -> None:
    bind = op.get_bind()
    appointments = bind.execute(
        text(
            """
            SELECT a.id, a.doctor_id, a.scheduled_for, a.duration_minutes, a.status
            FROM appointments a
            ORDER BY a.doctor_id, a.scheduled_for, a.id
            """
        )
    ).mappings().all()
    seen: dict[int, list[tuple[object, object, int]]] = {}
    for row in appointments:
        if row["status"] not in ACTIVE_STATUSES:
            continue
        start = row["scheduled_for"]
        end = start + timedelta(minutes=row["duration_minutes"])
        previous = seen.setdefault(row["doctor_id"], [])
        if any(start < prior_end and prior_start < end for prior_start, prior_end, _ in previous):
            conflicts = [str(existing_id) for prior_start, prior_end, existing_id in previous if start < prior_end and prior_start < end]
            conflicts.append(str(row["id"]))
            raise RuntimeError(
                "Cannot install appointment slot constraints while active appointments overlap. "
                f"Resolve appointment IDs {', '.join(conflicts)} without deleting history, then retry."
            )
        previous.append((start, end, row["id"]))

    op.create_table(
        "appointment_slot_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_start", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("doctor_id", "slot_start", name="uq_appointment_slot_doctor_start"),
        sa.UniqueConstraint("appointment_id", "slot_start", name="uq_appointment_slot_appointment_start"),
    )
    op.create_index("ix_appointment_slot_locks_appointment_id", "appointment_slot_locks", ["appointment_id"])
    op.create_index("ix_appointment_slot_locks_doctor_id", "appointment_slot_locks", ["doctor_id"])

    op.create_table(
        "appointment_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("actor_user_id", "idempotency_key", name="uq_appointment_command_actor_key"),
    )
    op.create_index("ix_appointment_commands_appointment_id", "appointment_commands", ["appointment_id"])

    op.create_table(
        "appointment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("previous_scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_appointment_events_appointment_id", "appointment_events", ["appointment_id"])

    for row in appointments:
        start = row["scheduled_for"]
        if row["status"] in ACTIVE_STATUSES:
            epoch_start = int(start.timestamp())
            epoch_end = epoch_start + row["duration_minutes"] * 60
            bucket_start = epoch_start // 1800 * 1800
            while bucket_start < epoch_end:
                bind.execute(
                    text(
                        """
                        INSERT INTO appointment_slot_locks (appointment_id, doctor_id, slot_start)
                        VALUES (:appointment_id, :doctor_id, :slot_start)
                        """
                    ),
                    {
                        "appointment_id": row["id"],
                        "doctor_id": row["doctor_id"],
                        "slot_start": datetime.fromtimestamp(bucket_start, timezone.utc),
                    },
                )
                bucket_start += 1800
        bind.execute(
            text(
                """
                INSERT INTO appointment_events
                    (appointment_id, actor_user_id, event_type, from_status, to_status, scheduled_for)
                VALUES (:appointment_id, NULL, 'imported', NULL, :status, :scheduled_for)
                """
            ),
            {"appointment_id": row["id"], "status": row["status"], "scheduled_for": start},
        )


def downgrade() -> None:
    op.drop_index("ix_appointment_events_appointment_id", table_name="appointment_events")
    op.drop_table("appointment_events")
    op.drop_index("ix_appointment_commands_appointment_id", table_name="appointment_commands")
    op.drop_table("appointment_commands")
    op.drop_index("ix_appointment_slot_locks_doctor_id", table_name="appointment_slot_locks")
    op.drop_index("ix_appointment_slot_locks_appointment_id", table_name="appointment_slot_locks")
    op.drop_table("appointment_slot_locks")
