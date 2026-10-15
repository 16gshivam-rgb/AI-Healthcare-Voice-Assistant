from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.security import create_access_token
from app.models.security import AuthSession
from app.models.user import User


def make_session_token(db, user: User) -> str:
    session = AuthSession(
        id=str(uuid4()),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
    )
    db.add(session)
    db.commit()
    return create_access_token(user.id, user.role, session.id)
