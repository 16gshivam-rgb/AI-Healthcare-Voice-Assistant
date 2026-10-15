# Deployment and operational checks

CareVoice is currently a local development stack, not a production-ready healthcare service. Use synthetic data only. Do not expose this Compose stack, PostgreSQL, Ollama, or pgAdmin directly to the internet.

## Start and validate the local stack

1. Copy `.env.example` to `.env`. Set separate random values for `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and `PGADMIN_DEFAULT_PASSWORD`; keep `.env` out of source control. URL-encode reserved characters in the database URL.
2. Validate Compose configuration and start the services:

   ```sh
   docker compose config --quiet
   docker compose up --build -d
   docker compose ps
   ```

3. Check database readiness, API liveness/readiness, and frontend reachability:

   ```sh
   docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
   curl -fsS http://localhost:8000/api/v1/health/live
   curl -fsS http://localhost:8000/api/v1/health/ready
   curl -fsS http://localhost:3000/
   ```

   API, frontend, database, Ollama, and pgAdmin ports are configured for host-loopback access. After changing a port binding, inspect both `docker compose config` and `docker compose port <service> <container-port>`; an already-running container may retain an older published binding until recreated.

4. Review the applied schema and run the available checks:

   ```sh
   docker compose exec -T backend alembic current
   docker compose exec -T backend alembic check
   docker compose exec -T backend python -m pytest -q
   docker compose exec -T frontend npm test
   docker compose exec -T frontend npm run build
   ```

   Backend tests use isolated synthetic fixtures. Payment-provider calls are mocked. The frontend is JavaScript/JSX and currently has no configured lint or type-check command.

## Database persistence and migrations

PostgreSQL data lives in the `postgres_data` named volume; Ollama model files use `ollama_data`. pgAdmin settings use `pgadmin_data`. `docker compose down` retains these volumes. Do not run `docker compose down -v` or remove volumes as part of routine upgrades, tests, or recovery.

Take and verify an encrypted, access-restricted backup before applying application changes to valuable data. A local SQL dump can be written with:

```sh
umask 077
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > carevoice-backup.sql
```

The backend container applies Alembic upgrades on startup. Review every migration before deployment; this repository's migrations are designed to retain existing application records and fail rather than silently resolve conflicting appointment history. Run `alembic check` after upgrades. Do not downgrade or restore over an existing database without an explicit, verified recovery plan.

## Optional integrations and current limits

| Integration | Current configuration | What remains unverified |
| --- | --- | --- |
| Local LLM | Ollama; configured quantized Llama model is installed and generated a test response in this environment | Clinical suitability, quality on representative Hindi/Hinglish cases, and production capacity |
| Hosted LLM | Not configured; no hosted API key is present | Provider account, privacy terms, latency/cost, and model quality |
| Razorpay | No key ID, key secret, or webhook secret is configured | Live order creation, signature checks against Razorpay, webhook delivery, and settlement/reconciliation |
| Email/SMS | No SMTP or SMS credentials are configured | Delivery, sender/domain configuration, recipient verification, and provider-specific semantics |
| Speech recognition | Browser Web Speech API selected | Browser support and browser-vendor audio/transcript handling; provider transcription is not configured |
| Medical RAG | Disabled by default; no approved documents are installed in the database | Source curation/licences, retrieval quality, citations, freshness, and grounded answer quality |

Synthetic test results are not a substitute for clinician review or clinical validation. Emergency triage rules are limited development safeguards and may miss red flags; always direct emergencies to local emergency services.

## Production readiness gates

Before any real patient use, require an independent threat model and security review, a clinical safety case and clinician-reviewed validation, privacy/data-protection and legal review for each operating jurisdiction, data minimization/retention and consent policies, verified contact channels, managed secrets, HTTPS and secure cookie/token policy, MFA for staff, centralized rate limiting, monitoring/alerting, least-privilege operations, tested encrypted backups and restoration, production-like migration/concurrency tests, provider contracts and privacy review, payment reconciliation, incident response, and a supported deployment/rollback runbook. This development Compose file does not provide those controls or establish regulatory compliance.
