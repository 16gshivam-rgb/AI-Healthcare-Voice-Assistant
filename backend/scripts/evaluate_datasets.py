from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.services.rag_service import RAGDocumentInput, RAGService
from app.services.triage_service import evaluate_triage

CASE_PATH = ROOT / "data" / "synthetic_medical_cases.json"
REGISTRY_PATH = ROOT / "data" / "dataset_registry.json"
SYNTHETIC_DATASET_VERSION = "1.1"
INJECTION_MARKERS = ("ignore all previous instructions", "system prompt", "ignore the safety rules")


def run_evaluation() -> dict:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not cases:
        raise ValueError("The synthetic evaluation set must contain at least one case.")

    failures: list[dict[str, str]] = []
    triage_passes = 0
    expected_emergencies = 0
    detected_emergencies = 0
    injection_cases = 0
    injection_blocks = 0
    retrieval_cases = [
        ("clinic appointment checkup questions", "Synthetic retrieval fixture: clinic appointment"),
        ("respiratory cough breathing concern", "Synthetic retrieval fixture: respiratory symptoms"),
    ]
    retrieval_hits = 0
    retrieval_precision_cases = 0
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    original_hosts = settings.rag_approved_source_hosts
    settings.rag_approved_source_hosts = f"{original_hosts},example.org"
    try:
        with session_factory() as db:
            rag = RAGService()
            for title, content in (
                (
                    "Synthetic retrieval fixture: clinic appointment",
                    "Synthetic test-only fixture about a clinic appointment, checkup, and preparing questions for the doctor.",
                ),
                (
                    "Synthetic retrieval fixture: respiratory symptoms",
                    "Synthetic test-only fixture about respiratory symptoms including cough, breathing concern, and follow-up.",
                ),
            ):
                rag.ingest_document(
                    db,
                    RAGDocumentInput(
                        title=title,
                        source_url=f"https://example.org/{title.rsplit(': ', 1)[-1].replace(' ', '-')}",
                        content=content,
                        version=SYNTHETIC_DATASET_VERSION,
                        licence="Synthetic test data",
                        allowed_use="Evaluation script only",
                        provenance="Synthetic fixture; not an external medical source",
                    ),
                )
            db.commit()

            for case in cases:
                result = evaluate_triage(case["input"])
                if result.urgency == case["expected_urgency"]:
                    triage_passes += 1
                else:
                    failures.append({
                        "id": case["id"],
                        "check": "urgency",
                        "expected": case["expected_urgency"],
                        "actual": result.urgency,
                    })

                if case["expected_urgency"] == "emergency":
                    expected_emergencies += 1
                    if result.urgency == "emergency":
                        detected_emergencies += 1

                lower = case["input"].casefold()
                expects_injection_block = (
                    case["expected_urgency"] == "urgent"
                    and any(marker in lower for marker in INJECTION_MARKERS)
                )
                if expects_injection_block:
                    injection_cases += 1
                    if result.safety_block:
                        injection_blocks += 1
                    else:
                        failures.append({
                            "id": case["id"],
                            "check": "prompt_injection_block",
                            "expected": "blocked",
                            "actual": "not blocked",
                        })

            for query, expected_title in retrieval_cases:
                hits = rag.search(db, query, category="public_health", limit=3)
                retrieval_precision_cases += 1
                if any(hit.title == expected_title for hit in hits):
                    retrieval_hits += 1
                else:
                    failures.append({
                        "id": "rag-retrieval",
                        "check": "recall_at_3",
                        "expected": expected_title,
                        "actual": ", ".join(hit.title for hit in hits),
                    })

            empty_evidence_hits = rag.search(
                db,
                "astronomy nebula orbital telescope spectral analysis",
                category="public_health",
            )
            if empty_evidence_hits:
                failures.append({
                    "id": "rag-empty-evidence",
                    "check": "no_evidence_fallback",
                    "expected": "no retrieved sources",
                    "actual": f"{len(empty_evidence_hits)} source(s)",
                })
    finally:
        settings.rag_approved_source_hosts = original_hosts
        engine.dispose()

    return {
        "evaluation": "deterministic_triage_and_empty_evidence",
        "dataset": {
            "name": "synthetic-medical-safety-set",
            "version": SYNTHETIC_DATASET_VERSION,
            "sample_size": len(cases),
            "source": "Repository-authored synthetic cases; not real patient data.",
            "clinician_review_status": "Reviewable; not clinician-reviewed.",
        },
        "retrieval_dataset": {
            "name": "synthetic-rag-retrieval-fixtures",
            "version": SYNTHETIC_DATASET_VERSION,
            "sample_size": len(retrieval_cases),
            "source": "Two synthetic local fixtures; not real public-health guidance.",
        },
        "metrics": {
            "triage_exact_accuracy": round(triage_passes / len(cases), 4),
            "emergency_sensitivity": round(detected_emergencies / expected_emergencies, 4) if expected_emergencies else None,
            "prompt_injection_block_rate": round(injection_blocks / injection_cases, 4) if injection_cases else None,
            "synthetic_rag_recall_at_3": round(retrieval_hits / retrieval_precision_cases, 4) if retrieval_precision_cases else None,
            "empty_evidence_fallback_passed": not any(
                failure["check"] == "no_evidence_fallback" for failure in failures
            ),
        },
        "failures": failures,
        "llm_model_comparison": {
            "status": "not_run",
            "reason": "This deterministic harness does not call an LLM. Run the opt-in model evaluation harness with authorized credentials to measure a configured model.",
        },
        "dataset_registry": registry,
        "limitations": [
            "Synthetic rule regression scores are not model benchmark scores and do not establish clinical safety.",
            "The synthetic examples are not clinician-reviewed.",
            "No MedQA, PubMedQA, MedMCQA, or MedQuAD data were downloaded or processed.",
            "No hosted model latency, cost, Hindi/Hinglish quality, or availability was measured by this run.",
        ],
    }


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2, ensure_ascii=False))
