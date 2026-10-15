# CareVoice Existing-System Audit

**Audit date:** 2026-10-10  
**Scope:** Phase 0, read-only code and configuration review, plus non-destructive validation attempts. No feature code, migrations, environment files, or existing application data were modified.

## Evidence and limitations

- **Verified** means directly observed in the checked-in workspace files or returned by a command.
- **Not verified** means the implementation exists in code/configuration but could not be exercised end-to-end.
- **Assessment** means an engineering or product risk inferred from the verified implementation.
- The local `.env` file exists, but its contents were deliberately not read or printed. No credentials, tokens, or patient data were inspected.
- Git history and working-tree changes could not be inspected: Git is not installed/available in this environment, and no `.git` directory was present in the workspace root. The prompt's reference to prior Git work therefore remains unverified. Do not assume the current files include all prior changes or that `.env` was never committed.
- No containers were running when `docker compose ps --all` was checked. No application service, migration, live database, LLM, speech provider, or payment gateway was exercised.
- A Docker test attempt created the Compose project network and named `postgres_data` and `ollama_data` volumes before failing to download the Python base image. No application container or migration ran. These resources were left untouched.

## 1. Existing architecture and folder structure

**Verified:** This is a development-oriented modular monolith. The browser calls a FastAPI REST API; SQLAlchemy models and repositories persist to PostgreSQL. Docker Compose defines the frontend, backend, database, Ollama, and pgAdmin.

```text
.
|-- backend/
|   |-- app/
|   |   |-- auth/          Password hashing and bearer-token authentication
|   |   |-- controllers/   Patient route coordination
|   |   |-- core/          Settings, database session, exceptions
|   |   |-- models/        User, patient profile, invoice, payment
|   |   |-- repositories/  Patient persistence queries
|   |   |-- routes/        Authentication, patients, assistant, billing
|   |   |-- schemas/       Patient request/response validation
|   |   |-- services/      Patient business logic
|   |   |-- cli.py         Interactive clinic-staff account creation
|   |   `-- main.py        FastAPI application and health endpoint
|   |-- migrations/        Alembic environment and one initial revision
|   |-- tests/             Account boundaries, billing, schema tests
|   |-- Dockerfile
|   |-- alembic.ini
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- components/   VoiceAssistant.jsx, Billing.jsx
|   |   |-- services/     Shared fetch helper and money formatting
|   |   |-- App.jsx       Authentication and single patient portal
|   |   `-- *.css         Portal and application styles
|   |-- Dockerfile
|   |-- index.html
|   |-- package.json
|   `-- vite.config.js
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- PROJECT_GUIDE.html
|   `-- PROJECT_GUIDE.pdf
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
`-- README.md
```

**Verified stack:** Python 3.12 image, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Pydantic settings, Argon2 password hashing, JWT (`python-jose`), HTTPX, React 18, and Vite. Frontend dependencies are limited to React/React DOM and Vite/plugin tooling. No Redis, queue, CI workflow, frontend test runner, or e2e test setup was present in the enumerated project files.

## 2. Features and actual implementation status

| Capability | Status from code review | Runtime status |
|---|---|---|
| Patient registration/login | Email/password registration and login; patient role is assigned by registration; passwords use the recommended pwdlib hash. | Not exercised; existing tests do not demonstrate the full registration/login journey. |
| Current account | Authenticated `/auth/me` endpoint; UI stores the access token and cached account in browser local storage. | Not exercised. |
| Patient profiles | Create/list/read/update/delete routes; data queries are scoped by `owner_user_id`; tests cover a cross-account read denial. | Unit/integration test execution blocked; live PostgreSQL not exercised. |
| General assistant chat | Authenticated `/assistant/chat` forwards up to 20 messages to an OpenAI-compatible chat-completions API; supports local Ollama or hosted provider configuration. | Provider-mocked cases exist in source; no test ran and no actual model was called. |
| Browser speech | Optional browser Web Speech API capture and browser speech synthesis playback. Text input remains available. | Not exercised in a browser. Browser/vendor speech behavior is outside the app's verified control. |
| Invoices | Staff/admin role can issue an invoice to a patient account; patient invoice listing is account-scoped; amount is stored in paise. | Mocked payment flow is covered by a source test; not run. |
| Razorpay checkout | Server creates orders from stored invoice values; checkout verification checks HMAC and verifies captured payment details with Razorpay; signed webhook is present. | No live gateway, webhook, or database transaction was tested. |
| Appointments, doctors, hospitals | No corresponding API/model/integration exists. The UI explicitly reports appointments and care-team integration as disconnected. | Not implemented. |
| Medical records / sharing | No records exchange, consent, or sharing backend exists; UI identifies records as not connected. | Not implemented. |
| Triage / emergency response | No symptom intake workflow, deterministic red-flag rules, urgency schema, emergency screen, or emergency-number action exists. The chat prompt only asks the general LLM to be cautious. | Not implemented or clinically validated. |
| Hospital tenancy / admin verification | No hospital/tenant model, tenant isolation policy, registry check, or platform-admin workflow exists. | Not implemented. |

The portal's navigation includes placeholders and disconnected pages; these should not be mistaken for implemented services. README statements about account ownership, provider configuration, and disconnected scheduling/records are broadly consistent with the code inspected.

## 3. Voice workflow analysis

**Verified code path:**

1. The patient types into the assistant textarea or starts browser `SpeechRecognition`/`webkitSpeechRecognition`.
2. Recognition requests `en-IN`, one final result, and one alternative. There is no UI language selector, partial-transcript flow, confidence threshold, or transcript confirmation.
3. The transcript is put into the draft. On submit, the browser appends it to the in-memory conversation and sends the last 20 messages to the authenticated `/assistant/chat` endpoint.
4. The API prepends a general-purpose safety system message and sends the full supplied message history to the configured provider. It does not redact identifying or health information, ask for consent, or run deterministic clinical checks.
5. The provider's first message content is checked to be a non-empty string, then returned as free-form text. No JSON/schema validation or medical post-filter is present.
6. The browser renders the text. The user may explicitly select “Read aloud”; browser speech synthesis speaks the response. Speech is not automatically played.

**Not implemented:** dedicated STT/TTS clients or provider interfaces, streaming audio, wake word, WebSocket/WebRTC, barge-in, partial-transcript emergency detection, speech confidence handling, Hindi/Hinglish-specific speech configuration, read-back confirmation, emergency-first response, audio retention controls, or voice quality/latency evaluations.

**Assessment:** This is optional browser dictation plus optional read-aloud around a text-chat product, not an end-to-end voice triage pipeline. Browser recognition may send audio to a browser-vendor service; the UI does not explain this at the point of capture. The API may send the conversation to an external configured provider. The app does not persist chat in its database, but that alone does not establish that the browser or provider retains no data.

## 4. Frontend, backend, and database integration

- **Verified:** The frontend uses a shared `fetch` helper and calls `/api/v1` routes. API base URL is configurable through `VITE_API_BASE_URL`.
- **Verified:** The FastAPI app registers auth, patient, assistant, and billing routers. Health checks execute `SELECT 1` against the configured database.
- **Verified:** SQLAlchemy models cover users, patient profiles, invoices, and payment records. One Alembic revision creates/adds these structures and associates matching legacy patient rows with accounts by email.
- **Not verified:** Successful frontend-to-backend requests, PostgreSQL connectivity, migration behavior on a clean or legacy database, and startup/health behavior; no services were running and no image build completed.
- **Assessment:** The migration's legacy email association changes ownership of existing rows based on matching email. Before production or real-data migration, this mapping needs an explicit reviewed reconciliation plan and backup/restore validation. Do not run a downgrade against data without reviewing its destructive table drops.
- **Assessment:** Patient access is owner-scoped at the application query layer, but there is no tenant concept or database Row-Level Security. There are no hospital/doctor tables or tenant-isolation tests.
- **Assessment:** Application startup in the backend image runs `alembic upgrade head` before Uvicorn. That is convenient for a single local instance, but schema migration should be an explicit, coordinated deployment step before multiple production API instances are considered.

## 5. Authentication and authorization review

**Positive controls verified:**

- Argon2 password hashes are used; password input is bounded and registration requires at least 10 characters.
- Registration creates a `patient` role; staff creation is a separate interactive CLI command.
- Access tokens are signed HS256 JWTs with a short configured expiry. Authenticated requests reload the user from the database and reject inactive/missing accounts.
- Patient repository/API queries include the current account owner ID. A test in source asserts that another account cannot retrieve a profile.
- Staff/admin checks protect invoice creation; invoice checkout and verification query by both invoice ID and owning user ID.

**Gaps / risks:**

- Access tokens are stored in `localStorage`, increasing impact if a browser XSS flaw is introduced. No CSP/security-header configuration was identified.
- No refresh-token rotation, token/session revocation, MFA, device/session management, login/registration rate limit, OTP, or brute-force controls exist.
- Roles are simple string values (`patient`, `staff`, `admin`); there is no centralized policy layer, hospital staff role, or tenant-scoped authorization.
- Staff/admin invoice history is global rather than constrained to a clinic/tenant. Today there is no tenant model to enforce a clinic boundary.
- No PHI access audit log, break-glass workflow, granular consent receipts, or patient access history exists.
- No rate limiting was found for chat, authentication, or payment routes.
- No production assessment of transport security, reverse-proxy headers, cookie/session policy, or secret-manager configuration was possible.

## 6. Medical safety, privacy, and compliance risks

### Medical safety

**High priority, verified absence:** no deterministic emergency/red-flag engine runs before the LLM. Emergency symptoms therefore have no guaranteed out-of-band behavior, emergency screen, 112/108 action, or Tele-MANAS 14416 path.

**High priority, verified absence:** model output is unstructured text. There is no validated urgency/specialty schema, safety post-filter, medication/dose block, fallback urgency, under-triage metric, clinician-reviewed rule set, or clinical evaluation dataset. A general system prompt is not an enforceable medical-safety boundary.

**Verified safeguards:** prompt/UI state that this assistant is general information and not a clinician, advise emergency users to contact local emergency services, discourage identifying details, and do not intentionally store chat in the app database.

**Assessment:** These safeguards are insufficient to offer clinical triage. The product should remain a clearly labelled development scaffold for synthetic data. Do not present its output as diagnosis, treatment, or clinically validated advice.

### Privacy and data protection

- Patient profile data includes name, email, age, and gender; it is stored in PostgreSQL without field-level encryption or consent-managed access.
- Chat payloads are forwarded as provided to the configured LLM. There is no PII/PHI redaction, data-minimization layer, consent receipt, retention policy, or verified provider no-training/retention setting.
- Browser speech recognition may involve a third-party browser speech service. There is no app-level audio storage, but vendor handling has not been verified.
- Chat messages are held in frontend component state during the page session and are not written to an application conversation table. This is not a guarantee about browser/provider/network logs.
- No immutable PHI-access audit log, patient export/erasure workflow, clinical-record consent, encrypted backup/restore process, or DPDP/ABDM/FHIR integration was found.
- `.env` is excluded by `.gitignore`, and `.env.example` contains development placeholders. Because Git/history is unavailable and `.env` was not inspected, whether any secret was ever committed cannot be determined.

## 7. Docker, configuration, and run/test results

### Configuration observations

- **Verified:** `docker compose config --quiet` succeeded.
- **Verified:** PostgreSQL is pinned to `postgres:16-alpine`; database, frontend, and backend published ports bind to loopback.
- **High risk:** pgAdmin publishes `5050:80` without a loopback bind and uses a fixed default administrator credential in the Compose file. This may expose the development admin UI to other hosts on the machine's network. Do not start this Compose stack on an untrusted/shared network before this is secured or disabled.
- **Risk:** Compose includes a fallback weak database password, and the settings class has a development fallback JWT secret. Production validation only rejects an unchanged/short JWT secret when `APP_ENV=production`; deployment still needs secret-manager handling and a non-default database credential.
- **Risk:** Ollama uses the mutable `latest` image tag. Pin and test a supported version for reproducible deployments.
- **Documentation mismatch:** `.env.example` comments describe Ollama as a profile-enabled optional service, but Compose defines no profiles and the backend depends on Ollama. The actual Compose configuration starts/depends on Ollama unconditionally.
- **Verified:** Compose health checks exist for PostgreSQL, API, frontend, and Ollama. The frontend is a Vite development server; backend Uvicorn runs with `--reload`. These are development containers, not production deployment settings.
- **Not verified:** PostgreSQL readiness, persistence, DB migration, API/frontend health checks, Ollama model availability, or pgAdmin access in a running stack.

### Commands and results

| Command/check | Result |
|---|---|
| `docker compose config --quiet` | **Passed**; Compose syntax/interpolation validated without printing rendered configuration. |
| `docker compose ps --all` | **Passed, no services listed**; the project was not running at the time of inspection. |
| `python -m pytest backend\tests -q` | **Not run:** host Python executable is unavailable (Windows app-execution alias reports Python is not installed). |
| `docker compose run --build --rm --no-deps backend pytest -q` | **Blocked before tests:** Docker could not obtain an anonymous token from Docker Hub for `python:3.12-slim` because the network connection was forcibly closed. No test result can be claimed. The failed attempt created the Compose network and named volumes; no containers or migrations ran. |
| Frontend build/test | **Not run:** Node.js and npm are unavailable on the host. Docker frontend build was not attempted; network access to Docker Hub already blocked the backend image pull. |
| Live app, voice, PostgreSQL, LLM, Razorpay | **Not run:** application services were not started; external/provider credentials and reachable integrations were not tested. |

The source contains eight backend test functions across the account-boundary, billing, and schema test files. That is a source count, not a passing-test count. There are no frontend tests in the inspected package scripts.

## 8. Broken/incomplete functionality and technical debt

1. The product's core promise—safe symptom triage and emergency handling—is absent; free-form LLM chat is not triage.
2. Voice support is browser-dependent English-India dictation and manual read-aloud, with no multilingual confirmation or emergency interrupt.
3. Appointments, hospital/doctor portals, provider verification, scheduling, and matching are disconnected/not implemented.
4. Consent, privacy requests, health-data audit, encryption, tenant isolation, and clinical records sharing are absent.
5. Authentication lacks MFA, refresh/revocation, abuse protection, and production-grade session security.
6. Payment processing has no tenant association, reconciliation/refund/dispute workflow, or demonstrated real-gateway test. Payment concurrency/idempotency behavior has not been validated.
7. Test coverage is narrow: backend ownership/payment/schema tests exist in source; frontend, migration-on-Postgres, concurrency, tenant isolation, clinical safety, voice, and end-to-end tests are absent.
8. No CI configuration, lint/type-check scripts, security/dependency scanning, threat model, runbooks, or clinical eval gate appeared in the enumerated tree.
9. The patient controller/service/repository layering is a reusable starting point, but several files use compressed one-line statements and uneven formatting; routes also directly contain assistant and payment provider orchestration.
10. The environment could not run tests, so syntax, package installation, migrations, and actual runtime behavior remain partly unverified.

## 9. Reusable code versus code to refactor

### Reuse

- Keep the React/Vite + FastAPI + PostgreSQL + SQLAlchemy/Alembic stack; it is coherent, familiar, and sufficient for an initial modular monolith.
- Retain the existing Argon2 hashing, database-reloaded current-user check, patient owner-filtered repository pattern, and corresponding negative ownership test as a base.
- Retain integer-paise invoice representation, server-derived invoice amount, Razorpay HMAC checks, and captured-payment verification, subject to new tenant and idempotency controls.
- Retain the assistant's small provider HTTP boundary as an integration starting point, not as a safe triage implementation.
- Retain clear UI states for not-connected appointments/records rather than substituting fabricated clinics or appointments.
- Retain the Compose health checks, PostgreSQL health dependency, and Alembic-managed schema history after operational hardening.

### Refactor / replace incrementally

- Split provider transport from triage policy; add deterministic, versioned emergency rules before any model call, then structured output validation and a safety post-filter.
- Add consent/redaction boundaries before any external LLM or browser speech provider; define retention and audit behavior.
- Move identity/authorization toward explicit policies and sessions/refresh controls; add hospital tenant context and database-enforced isolation before adding hospital-owned records.
- Extract payment provider calls into a billing application/infrastructure boundary and add idempotency, reconciliation, and tenant ownership.
- Evolve the frontend into explicit patient and hospital/doctor experiences only when the relevant authenticated backend domains exist. Keep text-first accessible fallback and progressively enhance voice.
- Add test, lint, accessibility, security-scan, migration-validation, and clinical-evaluation gates before expanding product claims.

## 10. Migrate-versus-rewrite decisions

| Module | Recommendation | Rationale |
|---|---|---|
| Frontend portal | **Migrate in place** | Existing React/Vite shell, account flow, profile, and disconnected-feature UX are useful. Add routes and capabilities incrementally; no reason for a framework rewrite. |
| FastAPI application/API | **Migrate in place** | The current application is small and has clear route boundaries. Introduce domain/application/provider boundaries as needed without a big-bang rewrite. |
| Identity/auth | **Migrate and harden** | Keep Argon2 and the current account lookup; add MFA, refresh/revocation, abuse controls, explicit authorization policies, and tenant-aware context before hospital users. |
| Patient/profile data | **Migrate schema incrementally** | Preserve owner scoping, but add consent, audit, privacy lifecycle, and later family/clinical data through reviewed forward migrations. Reconcile legacy email ownership before real data. |
| Assistant/triage | **Replace the clinical decision path, not the app** | Existing LLM proxy and chat UI can be adapted, but cannot be promoted to triage. Build deterministic safety and validated structured processing in a separate module and keep general chat clearly distinct. |
| Voice | **Migrate behind interfaces** | Preserve browser text/voice entry as a fallback. Add STT/TTS interfaces, language selection, confirmation, emergency interruption, and privacy controls; benchmark providers before selecting one. |
| Billing/payments | **Migrate and modularize** | Existing invoice and signature-verification logic is valuable. Add tenant scoping, idempotency, reconciliation/refunds, audit, and provider abstraction with targeted tests. |
| Database/migrations | **Keep and extend** | Continue PostgreSQL/Alembic with forward-safe reviewed migrations, RLS where appropriate, and explicit deployment sequencing. Do not rewrite or reset existing data. |
| Docker/docs | **Harden and maintain** | Keep Compose for local development; fix exposure/defaults and config/documentation drift. Do not treat the current dev containers as production infrastructure. |

**Conclusion:** No major module is unsalvageable. A rewrite would discard tested ownership/payment foundations and increase risk. Prefer an incremental modular-monolith migration; no microservices are justified by the current scale or codebase.

## 11. Proposed target architecture and ADRs

Keep the existing stack and evolve the backend into explicit modular-monolith domains:

```text
React/Vite patient UI (hospital/doctor UI added as a separate experience later)
        |
Versioned FastAPI interface
        |
Identity & policy | Tenancy | Patients & consent | Providers | Appointments
        |                 Triage & safety       | Billing | Audit
Application use cases and domain rules (framework-independent where practical)
        |
Infrastructure adapters: PostgreSQL/Alembic, LLM, STT/TTS, payments, notifications
```

Each domain should own its tables and expose explicit interfaces; avoid cross-domain direct table access. Use PostgreSQL tenant scoping plus application authorization, and add Row-Level Security only with transaction-scoped tenant context and tests proving isolation. Introduce model-assisted triage only after clinician-approved deterministic emergency rules, data minimization/consent, schema validation, safe fallback, and evaluation gates exist. Keep provider integrations swappable rather than adding services prematurely.

Proposed ADRs to write/review before the corresponding implementation (not created in this audit):

1. **ADR-001: Modular monolith and incremental module boundaries** — preserve Python/FastAPI, React/Vite, and PostgreSQL; define module ownership and migration strategy.
2. **ADR-002: Identity, tenancy, and authorization model** — roles, hospital tenant context, RLS approach, patient/family relationships, and staff access.
3. **ADR-003: Health-data consent, minimization, retention, and audit** — DPDP/ABDM mapping, external-provider terms, encryption, and privacy lifecycle.
4. **ADR-004: Clinical safety boundary and red-flag governance** — clinician-approved rules, emergency behavior, versioning, escalation, and clinical evaluation acceptance criteria.
5. **ADR-005: Hindi/Hinglish voice provider and confirmation strategy** — compare privacy, WER on approved medical phrases, latency, availability, and cost before selection.
6. **ADR-006: Appointment consistency and payment lifecycle** — slot locking/idempotency, booking state machine, payment reconciliation, and provider abstraction.

## 12. Prioritized implementation roadmap

Do not begin until Phase 0 has been reviewed and approved.

| Priority / phase | Outcome | Dependencies | Main risks / gates |
|---|---|---|---|
| **P0 — Audit follow-up / safe local baseline** | Restore Git tooling/history visibility; review existing changes and determine whether `.env` was ever tracked without displaying its contents; secure or disable network-exposed pgAdmin/default credentials; align Compose docs; establish reproducible local test prerequisites. | User/environment access to Git and Docker Hub or approved cached images. | If secrets were committed, rotate them; never print them. Do not start the current full Compose stack on a shared/untrusted network as-is. |
| **Phase 1 — Foundation** | CI, lint/format/type checks, repeatable tests, PostgreSQL integration/migration tests, structured non-PHI logs, secret/dependency/container scans, hardened dev Compose and documented setup. | P0 decisions; CI and registry access. | Avoid production migrations on app startup; validate backup/restore before any real data. |
| **Phase 2 — Identity, tenant, privacy** | Patient and hospital identity boundaries, authorization policies, tenant model/RLS tests, MFA/session controls, consent receipts, PHI audit trail, privacy lifecycle. | Phase 1; identity/tenancy and privacy ADRs; legal/privacy review. | Tenant leak, consent ambiguity, and legacy account/profile mapping are release blockers. |
| **Phase 3 — Verified provider and appointment foundation** | Hospital/doctor onboarding and verification workflow, schedules, timezone rules, concurrency-safe booking lifecycle, notifications, tenant-scoped dashboard APIs. | Phase 2; authoritative registry/data strategy; hospital operational input. | Never seed fabricated provider data; prove no double-booking and tenant separation under concurrency. |
| **Phase 4 — Medical safety and triage** | Clinician-governed red-flag engine and emergency UX first; structured intake; redacted/consented LLM integration, validated JSON, safety post-filter, conservative fallback, multilingual eval harness. | Phase 1–2; clinical governance, approved content/licenses, model privacy assessment. | No launch without clinician sign-off, emergency recall gates, under-triage monitoring, and safe outage behavior. |
| **Phase 5 — Voice and matching vertical slice** | Hindi/English/Hinglish STT/TTS seams, transcript confirmation, partial emergency interruption, accessible text fallback, explainable recommendations into verified appointments. | Phases 3–4; voice ADR/provider tests and consent. | Voice WER/latency, audio privacy, network quality, and false-negative emergency detection. |
| **Phase 6 — Hardening and pilot readiness** | Security/accessibility/load testing, incident and restore runbooks, SLOs/observability, privacy/legal and clinical review, controlled pilot checklist. | Phases 1–5. | Do not expose real PHI or claim clinical readiness before all approvals and operational controls. |

## 13. Immediate decisions / blockers

- **Git history and user changes:** Git is unavailable and `.git` is absent here. Before modifying existing code, review the real repository history and working tree in an environment with Git; identify the referenced prior session and preserve its work.
- **Local execution:** Install/provide approved host runtimes or permit access to the required Docker Hub images so tests and builds can run. This audit did not install dependencies.
- **Compose exposure:** Decide whether pgAdmin should be removed from the default stack or explicitly bound/protected for local-only use. The present default credential and all-interface binding should not be used on a shared network.
- **Clinical/privacy governance:** Before triage implementation, designate clinical reviewers and decide consent, provider retention/no-training requirements, supported languages, escalation language, and emergency UX.
- **Operational data:** Confirm whether any existing local PostgreSQL volume contains data before any migration, reset, or cleanup operation. No data volume was inspected or removed in this audit.

