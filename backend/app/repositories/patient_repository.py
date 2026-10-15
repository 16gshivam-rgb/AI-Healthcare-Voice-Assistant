from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate

class PatientRepository:
    def get_by_id(self, db: Session, patient_id: int, owner_user_id: int) -> Patient | None:
        return db.scalar(select(Patient).where(Patient.id == patient_id, Patient.owner_user_id == owner_user_id))
    def get_by_email(self, db: Session, email: str, owner_user_id: int) -> Patient | None:
        return db.scalar(select(Patient).where(Patient.email == email.lower(), Patient.owner_user_id == owner_user_id))
    def list(self, db: Session, owner_user_id: int, skip: int = 0, limit: int = 50) -> list[Patient]:
        return list(db.scalars(select(Patient).where(Patient.owner_user_id == owner_user_id).order_by(Patient.id).offset(skip).limit(limit)).all())
    def create(self, db: Session, data: PatientCreate, owner_user_id: int) -> Patient:
        obj = Patient(owner_user_id=owner_user_id, full_name=data.full_name.strip(), email=str(data.email).lower(), age=data.age, gender=data.gender)
        db.add(obj); db.commit(); db.refresh(obj)
        return obj
    def update(self, db: Session, obj: Patient, data: PatientUpdate) -> Patient:
        for key, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                if key == "email": value = str(value).lower()
                if key == "full_name": value = value.strip()
                setattr(obj, key, value)
        db.add(obj); db.commit(); db.refresh(obj)
        return obj
    def delete(self, db: Session, obj: Patient) -> None:
        db.delete(obj); db.commit()
