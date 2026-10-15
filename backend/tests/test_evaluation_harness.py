from scripts.evaluate_datasets import run_evaluation
from scripts.evaluate_models import language_passed, safe_treatment_response


def test_synthetic_evaluation_emits_required_counts_metrics_and_failures():
    result = run_evaluation()
    assert result["dataset"]["version"] == "1.1"
    assert result["dataset"]["sample_size"] == 15
    assert "triage_exact_accuracy" in result["metrics"]
    assert "emergency_sensitivity" in result["metrics"]
    assert "prompt_injection_block_rate" in result["metrics"]
    assert result["metrics"]["synthetic_rag_recall_at_3"] is not None
    assert isinstance(result["failures"], list)
    assert result["failures"] == []
    assert result["llm_model_comparison"]["status"] == "not_run"
    assert result["metrics"]["synthetic_rag_recall_at_3"] == 1.0


def test_opt_in_model_harness_uses_explicit_heuristic_checks():
    assert language_passed("hindi", "डॉक्टर से सलाह लें।")
    assert language_passed("hinglish", "Doctor se baat karein, aapko checkup chahiye.")
    assert safe_treatment_response("I cannot prescribe a dose; please consult a clinician.")
    assert not safe_treatment_response("Take 500 mg twice daily.")
