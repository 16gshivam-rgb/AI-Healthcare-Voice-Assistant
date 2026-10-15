from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate

class PatientService:
    def __init__(self, repository: PatientRepository | None = None):
        self.repository = repository or PatientRepository()
    def create_patient(self, db: Session, data: PatientCreate, owner_user_id: int) -> Patient:
        email = str(data.email).lower()
        if self.repository.get_by_email(db, email, owner_user_id):
            raise DuplicateResourceError("A patient with this email already exists.")
        try: return self.repository.create(db, data, owner_user_id)
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceError("A patient with this email already exists.") from exc
    def list_patients(self, db: Session, owner_user_id: int, skip: int = 0, limit: int = 50):
        return self.repository.list(db, owner_user_id, skip, limit)
    def get_patient(self, db: Session, patient_id: int, owner_user_id: int) -> Patient:
        obj = self.repository.get_by_id(db, patient_id, owner_user_id)
        if obj is None: raise ResourceNotFoundError("Patient not found.")
        return obj
    def update_patient(self, db: Session, patient_id: int, data: PatientUpdate, owner_user_id: int) -> Patient:
        obj = self.get_patient(db, patient_id, owner_user_id)
        updates = data.model_dump(exclude_unset=True)
        if updates.get("email") is not None:
            existing = self.repository.get_by_email(db, str(updates["email"]).lower(), owner_user_id)
            if existing and existing.id != patient_id:
                raise DuplicateResourceError("A patient with this email already exists.")
        try: return self.repository.update(db, obj, data)
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceError("A patient with this email already exists.") from exc
    def delete_patient(self, db: Session, patient_id: int, owner_user_id: int) -> None:
        self.repository.delete(db, self.get_patient(db, patient_id, owner_user_id))
