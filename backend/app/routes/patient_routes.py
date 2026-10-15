from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session
from app.controllers.patient_controller import patient_controller
from app.auth.security import require_roles
from app.core.database import get_db
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.models.user import User
from app.services.audit_service import record_audit

router = APIRouter(prefix="/patients", tags=["Patients"])
patient_user = require_roles("patient")

@router.post("/", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(patient_user)):
    patient = patient_controller.create(db, payload, user.id)
    record_audit(db, request, "patient.create", actor=user, resource_type="patient", resource_id=patient.id)
    db.commit()
    return patient

@router.get("/", response_model=list[PatientRead])
def list_patients(request: Request, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(patient_user)):
    patients = patient_controller.list(db, skip, limit, user.id)
    record_audit(db, request, "patient.list", actor=user, details={"count": len(patients)})
    db.commit()
    return patients

@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(patient_user)):
    patient = patient_controller.get(db, patient_id, user.id)
    record_audit(db, request, "patient.read", actor=user, resource_type="patient", resource_id=patient_id)
    db.commit()
    return patient

@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(patient_id: int, payload: PatientUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(patient_user)):
    patient = patient_controller.update(db, patient_id, payload, user.id)
    record_audit(db, request, "patient.update", actor=user, resource_type="patient", resource_id=patient_id)
    db.commit()
    return patient

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(patient_user)):
    patient_controller.delete(db, patient_id, user.id)
    record_audit(db, request, "patient.delete", actor=user, resource_type="patient", resource_id=patient_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
