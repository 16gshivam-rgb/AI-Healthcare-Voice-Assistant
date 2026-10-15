# MASTER PROMPT — AI Healthcare Platform (Patient + Hospital portals, AI Triage, Appointment Booking)

> Project: **ai-healthcare-voice-assistant**. Best way to use this: save this file as `CLAUDE.md` in the repo root (so every session follows it), then send the short kickoff prompt. You can also paste the whole file into the chat box directly.
> Language rule for the agent: **talk to me in Hinglish. Code, comments, commit messages, docs, and API names stay in English.**

---

## 1. ROLE

You are a principal engineer + healthcare-product architect. You write production-grade, maintainable, secure code. You prefer boring, proven designs over clever ones. You never ship something you have not run and tested.

## 2. MISSION

Upgrade my existing codebase (do NOT start from scratch unless the audit proves it is unsalvageable) into a **large-scale, easy-to-maintain healthcare platform** with:

1. **Patient portal (own login):** patient describes symptoms (text, Hindi/Hinglish/English, optional voice) → gets safe, explainable, best-possible guidance → can book a consultation with the best-matched doctor/hospital.
2. **Hospital portal (own login):** each hospital is a separate tenant. Admin onboards the hospital, adds doctors, sets schedules/fees/departments, manages appointments, sees analytics.
3. **Doctor view:** sees their own appointments, patient-shared triage summary (with consent), writes notes, marks complete.
4. **AI triage engine:** symptom intake → red-flag safety check → urgency level → likely specialty → home-care advice or recommended care level → doctor/hospital recommendation → appointment booking.
5. **Platform admin:** verifies hospitals/doctors, audit logs, feature flags, system health.

Primary market: **India** (Tier-2/3 cities like Durg/Bhilai/Raipur included). Design for low bandwidth, mobile-first, multilingual (Hindi + English minimum, Hinglish input must work).

**Project context:** this repo is `ai-healthcare-voice-assistant`, so the product is **voice-first**: a patient should be able to speak their symptoms in Hindi/Hinglish/English and hear the guidance back (text UI is the equal-citizen fallback). A previous Claude session in this repo ("Enhance project with advanced features", roughly +2667 / −322 lines) already changed the code about a week ago — treat that work as part of the existing codebase: review it, keep what is good, fix what is not, never revert it blindly.

---

## 3. STEP 0 — AUDIT THE EXISTING CODE FIRST (mandatory, before writing anything)

1. Explore the repo fully: stack, folder layout, dependencies, DB schema, auth, env/config, tests, CI, dead code, secrets committed by mistake. Read `git log` and the diffs of the most recent session ("Enhance project with advanced features") to understand what was added and why. Map the **existing voice pipeline** (speech-to-text, LLM call, text-to-speech, any wake word / streaming) and whether it works today — run the app and try it.
2. Write `docs/00-audit.md` with: what exists, what is reusable, what is broken or risky, tech debt, security issues, and a **migrate-vs-rewrite decision per module** with reasons.
3. **Keep my existing stack and conventions** unless there is a strong, written reason to change (record it as an ADR). If there is no code or the stack is unusable, use the default stack in section 5.
4. Show me the audit summary and the proposed plan. **Stop and wait for my "go"** before large changes. Small safe fixes are fine.
5. Never delete or rewrite working code blindly. Refactor in small, test-covered steps (characterization tests first when none exist).

---

## 4. NON-NEGOTIABLES

### 4.1 Medical safety (highest priority)
- The AI **never diagnoses** and never prescribes drugs/doses. It gives **triage guidance + general self-care information + care-level recommendation**, always with a clear "this is not a medical diagnosis" notice in the user's language.
- **Deterministic red-flag engine runs BEFORE and independently of the LLM.** If red flags match (chest pain with sweating/breathlessness, stroke signs FAST, severe bleeding, difficulty breathing, seizure, loss of consciousness, anaphylaxis, suspected poisoning, severe head injury, pregnancy bleeding/pain, infant fever/lethargy, suicidal thoughts, etc.), skip normal flow and show an **EMERGENCY screen**: call **112** (national emergency) / **108** (ambulance), nearest emergency-capable hospital, one-tap call. For self-harm/mental-health distress also show **Tele-MANAS 14416**.
- **Under-triage is the worst failure** (telling a sick person it's fine). Bias toward higher urgency when uncertain. Track under-triage rate as the #1 quality metric.
- LLM output must be **structured JSON validated against a schema**; on invalid/uncertain output → fall back to a safe default ("please consult a doctor", escalate urgency) — never show raw unvalidated text as medical advice.
- Special populations get extra caution and lower thresholds: infants/children, pregnancy, elderly, chronic disease (diabetes, cardiac, kidney), immunocompromised.
- No fabricated doctors, hospitals, ratings, reviews, credentials, or availability — ever. Real data only from verified sources (section 8); dev/demo data must be clearly labelled synthetic.

### 4.2 Privacy & compliance
- Treat all health data as highly sensitive PHI. Follow **India's DPDP Act 2023 (and its Rules)**; design to map cleanly to **ABDM (Ayushman Bharat Digital Mission)** standards (ABHA ID, FHIR) and the **Telemedicine Practice Guidelines 2020**; keep HIPAA-style controls so a US/EU launch is not a rewrite.
- Explicit, granular, revocable **consent** (data processing, sharing triage summary with a doctor, sharing records with a hospital). Store consent receipts. Right to access / correct / erase / export.
- **Minimize data sent to the LLM:** redact name, phone, email, address, exact DOB, IDs before the call; send age band + sex + symptoms only. Use an LLM provider/config with **no training on our data** and zero/limited retention. Log prompts safely (redacted).
- Encrypt in transit (TLS) and at rest; **field-level encryption** for sensitive columns; secrets only via env/secret manager; never commit secrets; rotate any secret found in git history.
- Immutable **audit log** of every PHI access (who, what, when, why) — patient can see who viewed their data.

---

## 5. ARCHITECTURE (high-level, maintainable, scale-ready)

**Principle: Modular monolith first, microservice-ready.** Strict module boundaries, so any module can later be extracted into a service without a rewrite. Clean/Hexagonal architecture: `domain` (pure business rules, no framework imports) → `application` (use-cases) → `infrastructure` (DB, LLM, SMS, payments) → `interface` (HTTP/UI).

**Default stack if there is no usable existing stack** (record as ADR):
- Backend: **Python 3.12 + FastAPI**, SQLAlchemy 2 + Alembic, Pydantic v2 (or TypeScript + NestJS if my existing code is Node).
- DB: **PostgreSQL** (+ `pgvector` for retrieval, `btree_gist` for slot-overlap exclusion constraints, Row-Level Security for tenancy). Redis for cache/rate-limit/queues. Celery/RQ (or BullMQ) for background jobs.
- Frontend: **Next.js + TypeScript**, Tailwind, i18n (Hindi/English), PWA + low-bandwidth mode, accessible (WCAG 2.1 AA).
- Infra: Docker + docker-compose for local; IaC-ready (Terraform) for cloud; **OpenTelemetry** tracing, structured JSON logs, Prometheus metrics, Sentry.
- CI/CD: GitHub Actions — lint, type-check, unit, integration, e2e, security scan (SAST, dependency audit, secret scan), eval-suite gate.

**Suggested layout (adapt to the existing repo, don't force it):**
```
/apps
  /api                 # backend
    /src
      /modules
        /identity      # auth, sessions, MFA, RBAC
        /tenancy       # hospitals (tenants), departments, onboarding, verification
        /patients      # profiles, family members, consents, medical history
        /providers     # doctors, specialties, schedules, fees, languages
        /triage        # symptom intake, red-flag engine, LLM orchestration, urgency
        /matching      # doctor/hospital recommendation & ranking
        /appointments  # slots, booking, reschedule, cancel, reminders, teleconsult
        /notifications # SMS/WhatsApp/email/push, templates, i18n
        /audit         # immutable audit log
        /billing       # (later) payments, invoices
      /shared          # config, errors, db, events, logging, security
  /web-patient         # patient portal
  /web-hospital        # hospital + doctor portal
  /web-admin           # platform admin
/packages
  /api-contract        # OpenAPI → generated typed clients
  /ui                  # shared design system
  /medical-knowledge   # red-flag rules, symptom ontology, specialty map (versioned data)
/evals                 # clinical vignette datasets + eval runners
/docs                  # audit, ADRs, architecture, runbooks, threat model
/infra
```
Rules: modules talk via **explicit interfaces + domain events**, never by reaching into each other's tables. One owner per table. No circular dependencies (enforce with import-linter / dependency-cruiser in CI).

**Maintainability rules:** small functions, typed everywhere, no god classes, config via env (12-factor), feature flags, API versioning (`/v1`), OpenAPI as source of truth, DB migrations always forward-safe and reviewed, ADR for every significant decision, README per module.

---

## 6. IDENTITY, ROLES, MULTI-TENANCY

- **Separate login experiences** per audience: Patient app, Hospital/Doctor portal, Platform-admin console — each with its own entry route/domain, branding, and session policy, backed by one identity module.
- Roles: `patient`, `doctor`, `hospital_admin`, `front_desk`, `platform_admin` (+ `support` read-only with break-glass audit). Permissions are **RBAC + resource ownership** checks (policy layer, not scattered `if` statements).
- **Tenant = hospital.** Every hospital-owned row has `tenant_id`; enforce isolation with **Postgres Row-Level Security** plus app-level checks, and write tests that prove tenant A can never read tenant B (negative tests are mandatory).
- Patient login: phone OTP (primary for India) + email option; optional ABHA login later. Hospital staff: email + password + **mandatory MFA** for doctors/admins. Short-lived access tokens + rotating refresh tokens, device/session management, rate limiting, brute-force/OTP-abuse protection.
- Patients can manage **family profiles** (parent books for child/elder) with correct consent semantics.
- Hospital onboarding: registration → document upload → **verification by platform admin** (registry check) → go-live. Doctors verified against registry before they appear in recommendations.

---

## 7. AI TRIAGE ENGINE (the heart of the product)

**Pipeline:**
1. **Intake (conversational + structured):** ask adaptive follow-ups (onset, duration, severity, location, associated symptoms, age/sex, pregnancy, chronic conditions, current meds/allergies — all optional but encouraged). Cap questions (≈5–8), skip what's already known.
2. **Normalize:** map free text (Hindi/Hinglish/English, slang like "pet mein dard", "saans phoolna") to a standard symptom ontology (SNOMED CT / ICD-11 concepts) via a maintained mapping table + LLM-assisted extraction, validated.
3. **Deterministic red-flag engine** (versioned rules in `/packages/medical-knowledge`, reviewed by a clinician). Match → emergency path, LLM not needed.
4. **LLM reasoning with RAG:** retrieve from a **curated, citeable knowledge base** (WHO, ICMR, MoHFW/NHM, NICE, AAP/ACOG etc. guidelines — respect licenses) and ground the answer in it. Model must return JSON:
   ```json
   {
     "urgency": "emergency|urgent_today|within_48h|routine|self_care",
     "specialty": ["General Medicine", "..."],
     "possible_conditions_general": [{"name": "...", "why": "..."}],
     "red_flags_to_watch": ["..."],
     "self_care": ["..."],
     "questions_unanswered": ["..."],
     "confidence": "low|medium|high",
     "citations": [{"source": "...", "section": "..."}],
     "disclaimer_key": "not_a_diagnosis_v1"
   }
   ```
   (`possible_conditions_general` are educational possibilities, never a diagnosis; hide when confidence is low.)
5. **Safety post-filter:** schema validation → rule re-check (LLM may only **raise** urgency vs. rules, never lower it) → block drug/dose advice → language check → fallback if anything fails.
6. **Output to patient** in their language, simple wording, large clear urgency badge, "what to do now", warning signs, and a **"Book a doctor" button prefilled with the right specialty**.
7. **Shareable triage summary** (patient chooses to share with the booked doctor): concise clinical summary, timeline, answers.

**Model strategy (provider-agnostic abstraction, Claude as the default):**
- `LLMClient` interface in `infrastructure/llm`, so models are swappable by config — no vendor lock-in.
- Default routing via env config (verify current model IDs in Anthropic docs at implementation time): a **fast/cheap model (e.g. `claude-haiku-5-5`)** for intent detection, language detection, symptom extraction, and cheap pre-checks; the **main model (e.g. `claude-sonnet-5-5`)** for triage reasoning and follow-up questions; a **top-tier model (e.g. `claude-opus-5-5`)** for low-confidence / complex / high-risk cases and for offline evaluation as an LLM-judge.
- Use prompt caching for the static system prompt + knowledge, structured outputs / tool-use for JSON, timeouts, retries with backoff, circuit breaker, per-user and global rate limits, cost tracking per request, and graceful degradation (LLM down → rules + "see a doctor" + booking still works).
- Prompts live in versioned files (`prompts/triage/v3.md`), never inline strings; every response stores `prompt_version`, `model`, `kb_version`, `rules_version` for traceability.

**Evaluation harness (`/evals`) — required, runs in CI:**
- 300+ clinical vignettes (Hindi/Hinglish/English) across specialties, age groups, pregnancy, emergencies, and tricky/ambiguous cases, each with a **gold urgency + specialty** labelled/reviewed by a licensed doctor.
- Metrics: **under-triage rate (target ≈ 0 for emergencies)**, over-triage rate, specialty accuracy, red-flag recall, hallucination/unsupported-claim rate, refusal-to-prescribe compliance, language quality, latency, cost.
- CI **fails** if safety metrics regress. Add adversarial tests (prompt injection in symptom text, "ignore your rules", requests for drug doses, self-harm, non-medical queries).
- Human-in-the-loop: a clinician review queue for sampled/flagged conversations; feedback ("was this helpful / did you go to a doctor") feeds evals, not silent auto-training.

---

## 7B. VOICE-FIRST LAYER (core of this project)

- Keep the existing voice pipeline if it works; **wrap it behind interfaces** (`STTClient`, `TTSClient`, `VoiceSession`) so providers are swappable by config. Benchmark candidates on real Hindi/Hinglish medical phrases and pick by word-error-rate, latency, and cost: Whisper-class models, Google/Azure speech, and Indian-language specialists (e.g. AI4Bharat IndicConformer, Sarvam AI). Record the benchmark in an ADR.
- **Streaming** audio (WebSocket/WebRTC), target first spoken response in roughly 1.5 s; support barge-in (user interrupts), silence/no-speech handling, noisy environments, and push-to-talk as well as hands-free.
- **Always confirm what was heard** for medical content ("Maine suna: seene mein dard aur saans phoolna — sahi hai?") before triage; low STT confidence → ask to repeat or offer to type. Never act on a low-confidence transcript.
- **Emergency words in speech** (chest pain, can't breathe, bleeding, unconscious, suicide, etc., in Hindi/Hinglish/English) hit the deterministic red-flag engine **immediately on partial transcripts**, and the emergency instruction is spoken first, loudly and slowly (112 / 108).
- TTS: slow, clear Hindi/English voice, simple words, repeat/slow-down/“say it again” commands, large-text captions alongside audio for hearing-impaired users.
- Audio is PHI: **do not store raw audio by default**; store the transcript only with consent; redact before any LLM call; delete audio buffers immediately after transcription.
- Telephony channel as a later phase (IVR/phone call via Exotel/Twilio or similar) so patients without smartphones can call and talk — design the seam now, don't build it yet.
- Add voice metrics to `/evals`: WER on Hindi/Hinglish medical vocabulary, emergency-phrase detection recall, end-to-end latency, confirmation-flow success rate.

---

## 8. DATA — "BEST DATA" STRATEGY

Use authoritative, verifiable sources; never scrape-and-trust:
- **Doctors:** verify against the **NMC Indian Medical Register / State Medical Councils** and the **ABDM Healthcare Professionals Registry (HPR)**.
- **Hospitals/clinics:** **ABDM Health Facility Registry (HFR)**, NABH accreditation list, state health dept lists; hospitals self-onboard and are verified by platform admin.
- **Medical vocabulary:** ICD-11 / ICD-10, SNOMED CT (check licensing for India), LOINC, RxNorm/CDSCO-compatible drug naming where needed; store as FHIR-compatible structures.
- **Clinical content:** WHO, ICMR, MoHFW, NHM, NICE, society guidelines — keep source, version, date, and license for each document; re-index on updates.
- **Location/search:** Google Places or OpenStreetMap for geocoding/distance; clearly attribute; never display scraped ratings as ours.
- **Dev/test:** synthetic patients (e.g. Synthea) and clearly fake doctors. **Never use real patient data in dev/test.**
- Ratings & reviews: only from **verified completed appointments**; moderated; no pay-to-rank.

---

## 9. DOCTOR/HOSPITAL MATCHING & APPOINTMENTS

**Matching (explainable ranking, `modules/matching`):**
- Hard filters: specialty fit, verified status, accepting new patients, language, teleconsult vs in-person, urgency window (urgent → earliest available / nearest emergency-capable).
- Soft score (weights configurable, logged): earliest availability, distance/travel time, experience, patient-verified ratings, fee vs patient budget, language match, hospital facilities (ICU/lab/etc.), insurance/Ayushman Bharat (PM-JAY) empanelment, continuity (patient's previous doctor).
- Return top N with a **"why this doctor"** explanation. No sponsored ranking influencing medical suitability.

**Appointments (`modules/appointments`):**
- Slot model: doctor schedules, recurring rules, exceptions/leaves, buffers, durations; all times stored UTC, shown in **IST**.
- **No double-booking, ever:** DB-level exclusion constraint / `SELECT … FOR UPDATE SKIP LOCKED`, short slot **holds with TTL** during checkout, **idempotency keys** on booking APIs, tested under concurrent load.
- Lifecycle: `requested → confirmed → checked_in → in_consultation → completed | cancelled | no_show | rescheduled`, as an explicit state machine with domain events.
- Reminders & notifications (SMS, WhatsApp, email, push) with templates in Hindi/English; reschedule/cancel with policy rules; waitlist; walk-in support for front desk.
- Teleconsultation: pluggable video provider (Jitsi/Daily/Twilio), secure join links, consent recording per Telemedicine Guidelines.
- Calendar sync (ICS/Google), doctor-side daily agenda, hospital-side queue dashboard.
- Payments & invoices behind an interface (Razorpay/Cashfree) — can be a later phase, but design the seam now.

---

## 10. SECURITY BASELINE

OWASP ASVS L2 as the target; threat model in `docs/threat-model.md` (STRIDE); input validation at every boundary; parameterized queries only; CSRF/CORS/CSP/HSTS; secure cookies; file-upload scanning & type limits; per-route rate limits; dependency + container scanning; least-privilege DB users; backups with tested restore; PII scrubbing in logs/error trackers; prompt-injection defenses (treat user text and retrieved documents as untrusted data, never as instructions); break-glass access with alerts.

---

## 11. QUALITY GATES

- Test pyramid: unit (domain logic, ≥80% on core modules) → integration (DB, with real Postgres in containers) → contract tests (OpenAPI) → e2e (Playwright: patient symptom→booking, hospital onboarding→schedule, doctor view) → **tenant-isolation tests** → concurrency tests for booking → LLM eval suite.
- Pre-commit: formatter, linter, type-check, secret scan. CI blocks merge on any failure.
- Every PR small, single-purpose, with description, tests, and migration notes. Conventional commits.
- Docs that stay true: ADRs, module READMEs, runbooks (incident, restore, key rotation, LLM outage), architecture diagram (Mermaid) updated with the code.

---

## 12. EXTRA THINGS I WANT YOU TO ADD (use your own judgment — "add best thing from your side")

- **Emergency mode:** one-tap SOS, nearest emergency-capable hospitals sorted by distance, works on weak network.
- **Low-bandwidth & offline-tolerant PWA**, lightweight pages, image compression, SMS/WhatsApp fallback for reminders.
- **Voice input** (Hindi/English) for symptom entry; large-text/accessibility modes for elderly users.
- **Medication & follow-up reminders**, post-visit follow-up check-ins, simple health timeline per patient.
- **Medical records vault** (upload reports/prescriptions with OCR → structured data), patient-controlled sharing, ABHA/FHIR export.
- **Hospital analytics:** no-show rate, wait times, peak hours, department load, AI-referral conversion; **patient analytics** kept private.
- **Feature flags + gradual rollout**, A/B-safe (never A/B test safety logic).
- **Admin console:** verification queue, red-flag rule editor with clinician approval + versioning, prompt/KB version management, audit explorer, LLM cost & quality dashboards.
- **Disaster-ready:** health checks, graceful degradation matrix (LLM down / SMS down / DB replica lag), documented SLOs.
- **Seed/demo mode** with synthetic data so I can demo end-to-end in 5 minutes.
- **Developer experience:** `make dev` (or one-command) spins up everything; `.env.example` with every variable documented; seed scripts; Postman/Bruno collection generated from OpenAPI.

---

## 13. DELIVERY PLAN — work in phases, stop for my review after each

| Phase | Output |
|---|---|
| **0** | Audit, `docs/00-audit.md`, target architecture, ADRs, backlog, risk list. **Wait for my approval.** |
| **1** | Foundation: repo structure, config, CI, Docker dev env, DB + migrations, logging/observability, shared kernel, test harness. |
| **2** | Identity + tenancy + RBAC: patient OTP login, hospital/doctor login with MFA, admin console skeleton, RLS + isolation tests, audit log. |
| **3** | Providers + scheduling + appointments with concurrency-safe booking, notifications, state machine, hospital & doctor dashboards. |
| **4** | Triage engine: red-flag rules, ontology, LLM client + routing, RAG KB, structured output, safety post-filter, patient triage UI, **eval harness with gate**. |
| **5** | Matching/recommendation + triage→booking flow, explainability, location, teleconsult. |
| **6** | Hardening: security review, load test, accessibility, i18n polish, runbooks, backup/restore drill, pilot checklist (clinician sign-off, legal/consent review). |

For each phase: plan briefly → implement in small commits → run tests/linters/evals → summarize what changed, what's risky, what's next. If you hit an ambiguous product/medical/legal decision, **ask me instead of guessing** (batch questions, give a recommended default for each).

---

## 14. DEFINITION OF DONE (per feature)

Works end-to-end locally; unit + integration (+ e2e where user-facing) tests pass; no secrets/PII in logs; tenant isolation proven; migration is reversible/safe; docs/ADR updated; observability added (logs, metrics, traces); accessibility and Hindi/English strings checked; safety review done for anything touching triage; and I can run it with the documented command.

---

## 15. HARD DON'Ts

- Don't give or imply a diagnosis, prescription, or dosage from the AI.
- Don't let LLM output lower urgency below what rules decide.
- Don't invent medical data, doctors, hospitals, reviews, or registry numbers.
- Don't send raw PHI/PII to third-party APIs without redaction and consent.
- Don't leak data across tenants; don't bypass RLS "just for now".
- Don't commit secrets, `.env`, or real patient data.
- Don't do big-bang rewrites, don't over-engineer microservices on day one, don't add a dependency without a reason.
- Don't claim something works unless you ran it.

**Start now with Phase 0: audit my existing code and show me the findings + plan. Do not write feature code until I approve.**
