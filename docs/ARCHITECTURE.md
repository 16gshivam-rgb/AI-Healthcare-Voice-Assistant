# CareVoice architecture

## Runtime

Browser (React/Vite) → FastAPI REST API → application services/repositories → PostgreSQL.

Docker Compose runs the UI, API, and database. The published development ports bind to loopback. The API applies Alembic migrations before Uvicorn starts; application startup does not mutate the schema.

## Backend modules

- **Routes** validate transport input and enforce authentication/role access.
- **Services and repositories** encapsulate patient domain operations and persistence.
- **Models** define users, owner-scoped patient profiles, invoices, and payment orders.
- **Provider adapters** are currently kept small: the assistant calls a local Ollama server or a configured OpenAI-compatible API with `httpx`; billing uses the Razorpay REST API and HMAC signatures. Provider secrets remain in backend environment variables.
- **Alembic** records schema revisions. When changing models, add and review a migration rather than relying on `create_all`.

The application is a modular monolith. Keep new domains in separate model/schema/service/repository/route modules; avoid splitting services until independent scaling or team ownership makes it necessary.

## Identity and data access

Patient routes require a valid bearer token and filter every read/write by the authenticated user ID. Patient registration always sets the role to `patient`; staff accounts are provisioned using the password-prompting CLI. Staff-only invoice creation does not make a patient a staff member.

The first migration adds nullable ownership to legacy patient rows and associates them to a user when their email matches. Unmatched legacy rows are not exposed through patient routes. Review and reconcile legacy records deliberately before any real-data deployment.

## AI and voice

The UI uses browser Web Speech APIs for voice capture and speech synthesis where available. The transcript is sent to the authenticated assistant route. Chat requests are not persisted in PostgreSQL. Local Ollama is the default and requires no API key; alternatively, the API forwards the conversation to the configured OpenAI-compatible provider, whose data policy applies.

## Payments

Invoices store integer minor units (INR paise). The browser never chooses the payable amount: the API loads it from the invoice, creates a Razorpay order, and verifies the signed order/payment tuple before changing invoice status. The optional webhook verifies the raw request-body signature and captured amount/currency. Card/bank information stays with Razorpay.

## Deliberate limitations

Appointment scheduling and medical-record exchange are clearly shown as unconnected rather than mocked. This codebase is for local development and synthetic data, not a compliant or clinically validated healthcare system.
