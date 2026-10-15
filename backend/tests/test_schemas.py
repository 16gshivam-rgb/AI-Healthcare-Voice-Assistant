import pytest
from pydantic import ValidationError
from app.schemas.patient import PatientCreate

def test_valid_patient_schema():
    obj = PatientCreate(full_name="Demo Patient", email="demo@example.com", age=25, gender="other")
    assert obj.age == 25

def test_invalid_age_rejected():
    with pytest.raises(ValidationError):
        PatientCreate(full_name="Demo Patient", email="demo@example.com", age=150, gender="other")
