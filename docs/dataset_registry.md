# Medical dataset registry and use policy

This project does not download, ingest, or train on MedQA, PubMedQA, MedMCQA, or MedQuAD. The machine-readable review record is [`backend/data/dataset_registry.json`](../backend/data/dataset_registry.json). Upstream licenses, mirrors, source materials, and exam questions can have different terms; an OSI-style license displayed on one mirror is not treated as proof that every upstream work is cleared.

## Dataset review

| Dataset | Intended task | Version/provenance checked | License and usage review | Current gate |
| --- | --- | --- | --- | --- |
| MedQA | Medical examination QA research evaluation only | Upstream repository identifies the 2020 release; data is linked through external storage and includes question sets and textbooks. | No explicit dataset-wide license was identified on the upstream repository page reviewed. | **Do not download or process** until terms and source-work rights are verified. |
| PubMedQA | Biomedical QA with yes/no/maybe labels, evaluation only | Upstream GitHub project and Hugging Face card reviewed. Hugging Face mirror lists 1,000 labeled, 211,269 artificial, and 61,249 unlabeled examples; mirror revision is not pinned. | The mirror card declares MIT; upstream README does not state a dataset license. Underlying PubMed abstracts have source terms/rights that require separate review. | **Do not download or process** until artifact and abstract-text rights are cleared. |
| MedMCQA | Indian medical exam-style QA evaluation only | Hugging Face card reports 182,822 train, 6,150 test, and 4,183 validation questions. Card describes collection from exam sites/books; no immutable revision pinned. | Hugging Face dataset card declares Apache-2.0. Its GitHub repository has an MIT badge, but repository code terms do not alone clear third-party exam questions. | **Do not download or process** until the artifact and exam-source rights are reviewed. |
| MedQuAD | Medical QA/retrieval research evaluation only | The project literature attributes QA pairs to US NIH websites; a current canonical immutable data release was not established in this review. | No dataset-wide license or uniform source-site reuse permission was verified. | **Do not download, ingest, or redistribute** pending dataset and per-source review. |
| Repository synthetic safety cases | Deterministic regression tests only | Version 1.1, [`backend/data/synthetic_medical_cases.json`](../backend/data/synthetic_medical_cases.json) | Repository-authored synthetic content; no real patient records. | Available for local tests. Reviewable, but not clinician-reviewed. |

## Sources checked

- [MedQA upstream repository](https://github.com/jind11/MedQA) and [paper](https://arxiv.org/abs/2009.13081)
- [PubMedQA upstream repository](https://github.com/pubmedqa/pubmedqa), [Hugging Face dataset card](https://huggingface.co/datasets/qiaojin/PubMedQA), and [paper](https://aclanthology.org/D19-1259/)
- [MedMCQA upstream repository](https://github.com/MedMCQA/MedMCQA) and [Hugging Face dataset card](https://huggingface.co/datasets/openlifescienceai/medmcqa)
- [MedQuAD Hugging Face mirror card](https://huggingface.co/datasets/keivalya/MedQuad-MedicalQnADataset); its reviewed card did not provide a verified dataset-wide reuse license.

The registry's `checked_on` date is the date of this documentation pass. Re-check upstream data revisions, licences, source terms, and intended use before any future use. Keep an immutable dataset commit/release identifier and the license/permission evidence with the evaluation results.

## Reproducible evaluation

Run the local deterministic test-set evaluation from the backend container:

```sh
docker compose exec backend python scripts/evaluate_datasets.py
```

It reports the synthetic set version/sample size, urgency exact accuracy, emergency sensitivity, prompt-injection block rate, synthetic RAG recall@3, missing-evidence behavior, failures, and limitations. It does **not** call an LLM or download any external dataset. Retrieval fixtures are repository-authored and explicitly not public-health sources.

An opt-in model smoke comparison is available:

```sh
docker compose exec backend python scripts/evaluate_models.py
docker compose exec backend python scripts/evaluate_models.py --run
docker compose exec backend python scripts/evaluate_models.py --run --models gpt-5-mini,gpt-4.1-mini
```

Without `--run`, the script performs no model request. The explicit `--run` command can use paid hosted APIs; select only models supported by the configured provider and review cost/privacy first. It uses four synthetic prompts and reports strict-schema validity, simple language/refusal heuristics, latency, usage tokens, and estimated cost only where a published rate is configured. These are smoke-test measurements, not controlled model comparisons or clinical accuracy scores. Never include patient data.

Benchmark scores are not clinical validation and do not prove safe use with patients.
