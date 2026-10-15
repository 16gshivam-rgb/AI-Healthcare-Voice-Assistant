from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import verify_password
from app.core.database import Base
from app.models.providers import Hospital
from app.models.security import AuditLog
from app.models.user import User
from app import cli


def test_cli_can_provision_legacy_unassigned_staff_and_audits_change(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    with sessions() as db:
        hospital = Hospital(name="Legacy Hospital", city="Delhi", state="Delhi")
        staff = User(
            full_name="Legacy Staff",
            email="legacy-staff@example.com",
            password_hash="old-password-hash",
            role="hospital_staff",
        )
        db.add_all([hospital, staff])
        db.commit()
        hospital_id = hospital.id
    password_values = iter(("new-secure-password", "new-secure-password"))
    monkeypatch.setattr(cli, "SessionLocal", lambda: sessions())
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(password_values))

    try:
        assert cli.create_account("legacy-staff@example.com", "hospital_staff", hospital_id, None) == 0
        with sessions() as db:
            staff = db.scalar(select(User).where(User.email == "legacy-staff@example.com"))
            assert staff.hospital_id == hospital_id
            assert verify_password("new-secure-password", staff.password_hash)
            event = db.scalar(select(AuditLog).where(AuditLog.action == "account.provisioned"))
            assert event.resource_id == str(staff.id)
            assert event.details == {"role": "hospital_staff"}
    finally:
        engine.dispose()
