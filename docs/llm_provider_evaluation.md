# LLM provider and model evaluation

## Runtime decision

- **Development default:** local Ollama using the existing `LLM_PROVIDER` / `LLM_MODEL` values. This preserves the no-hosted-credentials workflow.
- **Recommended hosted candidate (not empirically validated for this app):** `gpt-6-luna` on the OpenAI API. Its official model page describes it as the most efficient model for focused, high-volume tasks, lists Chat Completions and structured outputs, and publishes low token rates. It also fits the existing strict Chat Completions/JSON Schema adapter. Claude Haiku 5.5 has the same listed base token rates and stronger published latency positioning, but uses Anthropic's native Messages API and needs a separate adapter. Gemini 3.1 Flash-Lite is also positioned for low-latency, cost-sensitive work and supports structured output through its native API; the reviewed OpenAI-compatibility documentation does not establish strict JSON Schema support for the current adapter. These are document-based candidates, not task-tested winners.
- **Selection confidence:** provisional. No hosted-provider credential was available for controlled measurements. Hindi/Hinglish quality, observed latency, and actual account availability/pricing are **not measured here**. The opt-in harness can measure limited heuristics after an operator configures a provider. Do not describe the candidate as clinically safe.

The candidate identifier belongs in `LLM_MODEL` in environment configuration, not in a business-logic branch. The checked-in example continues to default to local Ollama. Configure the hosted candidate only after reviewing provider data controls and explicitly enabling the provider. There is no automatic model/provider switch on outage.

## Official provider evidence (checked 2026-10-14)

| Model | Official structured-output / endpoint evidence | Published standard text token rates per 1M | Assessment for this workload |
| --- | --- | ---: | --- |
| OpenAI `gpt-6-luna` | [Model page](https://developers.openai.com/api/docs/models/gpt-6-luna) lists Chat Completions and Structured Outputs. Chat Completions supports `reasoning_effort=none`; the adapter uses this mode and `max_completion_tokens`. | $0.10 input / $0.50 output | Recommended hosted candidate based on official focused/high-volume positioning and published rates. Hindi/Hinglish quality and end-to-end latency require measurement. |
| OpenAI `gpt-5-mini` | [Model page](https://developers.openai.com/api/docs/models/gpt-5-mini) lists Chat Completions and Structured Outputs. | $0.25 input / $2.00 output | Viable alternative, with higher published per-token rates than GPT-6 Luna at the comparison date; still requires empirical checks. |
| OpenAI `gpt-4.1-mini` | [Model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini) lists Chat Completions and Structured Outputs. | $0.40 input / $1.60 output | Valid alternative; lower output but higher input rate than `gpt-5-mini`. Needs the same empirical checks. |
| OpenAI `gpt-5.6-terra` | [Model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra) lists Chat Completions and Structured Outputs. | $2.00 input / $12.00 output | Official documentation positions it for intelligence/cost balance; no task-specific repository measurement justifies its higher published rates here. |
| Anthropic Claude Haiku 5.5 | [Model overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview) positions it for latency-sensitive, high-volume work and reports it as the fastest in its lineup. [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) are GA for this model through the native Messages API. | From $0.10 input / $0.50 output | Promising comparable candidate, but not wired to the current OpenAI-compatible adapter. It needs a native adapter and the same controlled task evaluation before selection. |
| Google Gemini 3.1 Flash-Lite | [Model guide](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite) describes low-latency, cost-effective high-volume tasks and shows native JSON Schema output. Google's [OpenAI compatibility guide](https://ai.google.dev/gemini-api/docs/openai) documents Chat Completions, but does not establish strict JSON Schema support through that compatibility endpoint. | Not verified for this exact model in this review; confirm the current [pricing page](https://ai.google.dev/gemini-api/docs/pricing) before deployment. | Promising native-API candidate, but the current app adapter sends OpenAI-style `response_format`; do not configure this candidate with it until compatibility is demonstrated or a native adapter is added. |
| Local Ollama configured model | [Ollama OpenAI compatibility](https://docs.ollama.com/openai) supports an OpenAI-style endpoint; actual structured behavior varies by selected runtime/model. | No provider token charge; hardware/electricity cost not measured. | Keeps prompts on the local development stack, but performance is hardware-dependent. The current 1B model is not considered clinically competent. |

Published prices are point-in-time information, not a quote. Confirm current availability, API access, rate limits, regional terms, and billing before use. Anthropic's API documentation describes no training use without express permission and no default prompt/response retention, subject to feature/model-specific exceptions and account terms. Google's Gemini API pricing documentation distinguishes free-tier use (content may be used to improve products) from paid-tier use (listed as not used); this is not a substitute for review of current terms, data location, or a healthcare data agreement. OpenAI API data is not used for training by default, while abuse-monitoring logs may retain content for up to 30 days by default. No provider's default terms alone authorize sending identifiable patient data. The recommendation is based on official documentation and current adapter fit, not an empirical comparison or recommendation for diagnosis/triage.

### Evaluation dimensions and evidence status

| Dimension | Evidence / how this project measures it |
| --- | --- |
| Structured output | Official support is documented for hosted candidates. Runtime requests strict JSON Schema and validates the resulting Pydantic object. |
| Hindi/Hinglish | Model pages do not establish healthcare Hindi/Hinglish quality. The opt-in synthetic smoke harness contains Hindi Devanagari and Hinglish Roman-script prompts with simple script/marker checks; these are not a language benchmark. |
| Instruction following / safety | A small synthetic refusal prompt and structured-output checks run only with explicit `--run`; a deterministic post-filter rejects a subset of diagnosis/dosing patterns. Neither is a clinical safety proof. Emergency triage remains deterministic and bypasses RAG and LLM. |
| Latency | The opt-in harness records per-request latency on the configured provider, machine, region, and account. No hosted latency was measured during this implementation. |
| Cost | Published rates above; the opt-in harness estimates per-run cost from provider-reported token use only for listed IDs. Billing, caching, tier, and regional rates can differ. |
| Privacy | OpenAI API data is not used for training by default; abuse-monitoring retention and Zero Data Retention eligibility/endpoint limitations apply. Anthropic documents no training without express permission and no default conversation-content retention, with model/feature exceptions. Google distinguishes free and paid API data-use terms. None has been reviewed for this deployment's legal basis, data residency, or patient-data agreement. |
| Availability | Official docs list the relevant APIs, but this workspace did not verify credentials, organization entitlement, regional availability, or account quotas. Only Ollama and OpenAI-compatible API shapes are implemented; the Claude Messages and Gemini native structured-output APIs require additional adapters. Outages return explicit errors; there is no silent switch to another model. |

No model requests occur unless `evaluate_models.py` is explicitly invoked with `--run`. Model IDs and credentials are runtime environment settings; secrets remain backend-side.

### Measured local baseline (2026-10-14)

The opt-in harness was run once against the configured local Ollama model `llama3.2:1b-instruct-q4_K_M` on the four synthetic prompts. This is a smoke result, not a statistically stable benchmark:

| Metric | Observed |
| --- | ---: |
| Structured response validity | 3/4 (0.75) |
| Language/script heuristic | 3/4 (0.75); the Hinglish response failed structured validation |
| Personal-dose refusal heuristic | 0/1 (0.00) |
| Mean / median / p95 latency | 28.597 s / 36.175 s / 40.053 s |
| Reported token usage | 284 input / 144 output |
| Failures | Hinglish structured output; unsafe-dose refusal heuristic |

This run is a reason **not** to rely on the local 1B model for health answers. The app now intercepts common personal prescription/dosage requests before RAG/LLM, validates strict schemas, and rejects a subset of unsafe answer patterns; these mitigations are not exhaustive. No hosted model was evaluated because no hosted credential was available. There are no hosted Hindi/Hinglish, latency, cost, or availability measurements in this repository.

## MedGemma research baseline

MedGemma is not the hosted primary candidate and is not configured in the app. Google's [MedGemma model card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card) describes medical text/image variants and directs users to Health AI Developer Foundations terms. Weights are governed by those terms, not an assumed unrestricted Apache license; confirm and accept current terms before any use. Intended-use and benchmark caveats do not establish clinical validation or authorize autonomous patient care.

The documented 4B instruction-tuned variant uses GPU-oriented Transformers/BF16 examples. Four billion parameters at two bytes each imply roughly 8 GB for raw weights alone, before runtime/KV-cache/vision overhead; 27B variants need substantially more. This repo's CPU Ollama environment has not been evaluated for it. Do not download/run until exact variant/license, hardware, runtime, and research protocol are approved. Any evaluation is an offline research baseline, not triage or treatment.

## Provider, response, and safety contract

- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, and `LLM_API_KEY` select the one configured provider/model. Unknown provider names fail explicitly.
- Requests use finite timeouts and at most the configured bounded transient retries. Authentication/client errors are not retried.
- Chat uses strict JSON Schema/Pydantic response validation and a conservative deterministic post-filter. Invalid responses are rejected; provider failures return explicit HTTP errors.
- Deterministic emergency red flags run before RAG/LLM and immediately return emergency guidance. The model has no urgency field and cannot downgrade that outcome.
- Only configured public-health evidence is retrieved. Source passages are untrusted data; user and retrieved-document instructions cannot change the system prompt. Citations are attached from retrieved database rows by the backend, not generated by the model.
- Without evidence, the assistant is instructed to disclose the gap; a RAG outage is logged and uses an explicit cautious no-evidence context. The patient-record category is not ingestible/searchable in this index.
- This remains a development information assistant, not a clinically validated or production-authorized system.
