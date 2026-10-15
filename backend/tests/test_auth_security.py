from datetime import datetime, timedelta, timezone
import smtplib
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.rate_limit import reset_auth_rate_limits
from app.auth.security import create_access_token, hash_password
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.providers import Appointment, Doctor, Hospital
from app.models.security import AuthSession, PasswordResetToken
from app.models.user import User
from tests.auth_utils import make_session_token


def _client_with_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_database
    return engine, sessions, TestClient(app)


def test_login_rejects_invalid_credentials_and_persists_login_failure():
    engine, sessions, client = _client_with_database()
    with sessions() as db:
        db.add(User(full_name="Patient", email="patient@example.com", password_hash=hash_password("correct-password")))
        db.commit()
    reset_auth_rate_limits()
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "patient@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
        with sessions() as db:
            from app.models.security import AuditLog

            assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed")) is not None
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_authentication_rate_limit_blocks_repeated_failures(monkeypatch):
    engine, sessions, client = _client_with_database()
    monkeypatch.setattr(settings, "auth_rate_limit_attempts", 1)
    monkeypatch.setattr(settings, "auth_rate_limit_window_seconds", 60)
    reset_auth_rate_limits()
    try:
        body = {"email": "missing@example.com", "password": "wrong-password"}
        assert client.post("/api/v1/auth/login", json=body).status_code == 401
        limited = client.post("/api/v1/auth/login", json=body)
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_logout_revokes_session_and_sessionless_token_is_rejected():
    engine, sessions, client = _client_with_database()
    with sessions() as db:
        user = User(full_name="Patient", email="patient@example.com", password_hash=hash_password("correct-password"))
        db.add(user)
        db.commit()
        db.refresh(user)
        token = make_session_token(db, user)
        missing_session_token = create_access_token(user.id, user.role, str(uuid4()))
    headers = {"Authorization": f"Bearer {token}"}
    try:
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
        assert client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {missing_session_token}"},
        ).status_code == 401
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        with sessions() as db:
            session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
            assert session.revoked_at is not None
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_expired_session_is_rejected():
    engine, sessions, client = _client_with_database()
    with sessions() as db:
        user = User(full_name="Patient", email="patient@example.com", password_hash="unused")
        db.add(user)
        db.commit()
        db.refresh(user)
        session_id = str(uuid4())
        db.add(
            AuthSession(
                id=session_id,
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        db.commit()
        token = create_access_token(user.id, user.role, session_id)
    try:
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_patient_routes_forbid_hospital_staff_and_appointments_are_tenant_scoped():
    engine, sessions, client = _client_with_database()
    with sessions() as db:
        first_hospital = Hospital(name="Hospital One", city="Delhi", state="Delhi")
        second_hospital = Hospital(name="Hospital Two", city="Pune", state="Maharashtra")
        patient = User(full_name="Patient", email="patient@example.com", password_hash="unused")
        staff_one = User(
            full_name="Staff One",
            email="staff-one@example.com",
            password_hash="unused",
            role="hospital_staff",
        )
        staff_two = User(
            full_name="Staff Two",
            email="staff-two@example.com",
            password_hash="unused",
            role="hospital_admin",
        )
        db.add_all([first_hospital, second_hospital, patient, staff_one, staff_two])
        db.commit()
        staff_one.hospital_id = first_hospital.id
        staff_two.hospital_id = second_hospital.id
        doctor = Doctor(hospital_id=first_hospital.id, full_name="Dr One", specialty="General Medicine")
        db.add(doctor)
        db.commit()
        appointment = Appointment(
            patient_user_id=patient.id,
            doctor_id=doctor.id,
            hospital_id=first_hospital.id,
            scheduled_for=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(appointment)
        db.commit()
        appointment_id = appointment.id
        staff_one_token = make_session_token(db, staff_one)
        staff_two_token = make_session_token(db, staff_two)
    try:
        staff_one_headers = {"Authorization": f"Bearer {staff_one_token}"}
        staff_two_headers = {"Authorization": f"Bearer {staff_two_token}"}
        assert client.get("/api/v1/patients/", headers=staff_one_headers).status_code == 403
        own_tenant = client.get("/api/v1/providers/appointments", headers=staff_one_headers)
        other_tenant = client.get("/api/v1/providers/appointments", headers=staff_two_headers)
        assert own_tenant.status_code == 200 and len(own_tenant.json()) == 1
        assert other_tenant.status_code == 200 and other_tenant.json() == []
        cross_cancel = client.patch(
            f"/api/v1/providers/appointments/{appointment_id}/cancel",
            headers=staff_two_headers,
        )
        assert cross_cancel.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_password_reset_is_single_use_and_revokes_existing_sessions(monkeypatch):
    engine, sessions, client = _client_with_database()
    with sessions() as db:
        user = User(full_name="Patient", email="patient@example.com", password_hash=hash_password("old-password"))
        db.add(user)
        db.commit()
        db.refresh(user)
        old_token = make_session_token(db, user)
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(settings, "smtp_host", "mail.example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "no-reply@example.com")
    monkeypatch.setattr(
        "app.routes.auth_routes._send_password_reset_email",
        lambda email, token: sent.append((email, token)),
    )
    reset_auth_rate_limits()
    try:
        requested = client.post("/api/v1/auth/password-reset/request", json={"email": "patient@example.com"})
        assert requested.status_code == 202
        assert len(sent) == 1 and sent[0][0] == "patient@example.com"
        with sessions() as db:
            reset_record = db.scalar(select(PasswordResetToken))
            assert reset_record is not None
            assert reset_record.token_hash != sent[0][1]
        changed = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": sent[0][1], "new_password": "new-valid-password"},
        )
        assert changed.status_code == 200
        assert client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": sent[0][1], "new_password": "another-valid-password"},
        ).status_code == 400
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "patient@example.com", "password": "new-valid-password"},
        )
        assert login.status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_password_reset_delivery_failure_does_not_reveal_account_existence(monkeypatch, caplog):
    engine, sessions, client = _client_with_database()
    with sessions() as db:
        db.add(User(full_name="Patient", email="patient@example.com", password_hash="unused"))
        db.commit()
    monkeypatch.setattr(settings, "smtp_host", "mail.example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "no-reply@example.com")

    def fail_delivery(_email, _token):
        raise smtplib.SMTPException("mail transport unavailable")

    monkeypatch.setattr("app.routes.auth_routes._send_password_reset_email", fail_delivery)
    reset_auth_rate_limits()
    try:
        missing_account = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "missing@example.com"},
        )
        existing_account = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "patient@example.com"},
        )
        assert missing_account.status_code == existing_account.status_code == 202
        assert missing_account.json() == existing_account.json()
        assert "Password-reset email delivery failed" in caplog.text
        with sessions() as db:
            from app.models.security import AuditLog

            assert db.scalar(
                select(AuditLog).where(AuditLog.action == "auth.password_reset_delivery_failed")
            ) is not None
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
