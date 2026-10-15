# Provider profiles and directory

Provider profiles are stored in PostgreSQL. Migration `0005_provider_profiles` is additive: it preserves existing provider and appointment rows, maps legacy `verified = true` records to a verified status, and leaves all other records pending review. Existing legacy language and consultation-mode fields remain readable.

## Directory and trust rules

- `GET /api/v1/providers/doctors` and `/hospitals` accept `limit` (1–100), `offset`, and search filters. Responses contain `items`, `total`, `limit`, and `offset`.
- Doctor filters include `search`, `specialty`, `city`, `language`, and `consultation_type`; hospital filters include `search`, `city`, and `state`.
- Detail routes return only active, verified profiles. A doctor attached to a hospital is discoverable only when that hospital is also verified. Unverified records are omitted and return 404 from public detail routes.
- Qualifications retain their awarding institution, completion year, and separate verification status. Only platform administrators may change profile or qualification verification status.
- Doctor schedules are recurring weekly local-time intervals (`day_of_week` 0 is Monday) with an IANA timezone and consultation type. Overlapping active intervals are rejected.
- Appointment booking is accepted only if it fits an active published schedule, uses a supported consultation type, is in the future, and does not overlap another appointment. A recurring schedule is not a real-time availability guarantee. Recommendation responses therefore return no fabricated appointment slots.

## Roles and management

- Doctors may edit only their linked profile and recurring schedule.
- Hospital administrators may update their own hospital and create/update clinician profiles only within their assigned hospital.
- Hospital staff have a read-only hospital dashboard and cannot edit profiles.
- Platform administrators can create hospitals and review pending doctor/hospital/qualification verification.
- Patient and other authenticated accounts can browse the verified directory. Hospital tenant boundaries are checked on management endpoints independently of the UI.

`GET /api/v1/providers/dashboard` returns role-scoped counts or the caller's own provider profile. `GET /api/v1/providers/review-queue` is platform-admin-only. Profile changes and verification actions are written to the audit log.

## Recommendations

`POST /api/v1/providers/recommendations` accepts optional symptom text, specialty, city, language, and consultation type. The API applies deterministic rules against verified, active directory records and returns the matched criteria in `match_reasons`. Scores are a ranking aid, not a clinical recommendation or evidence of provider quality. Criteria weights default to specialty (55%), city (20%), language (15%), and consultation type (10%), and can be adjusted with the corresponding `PROVIDER_MATCH_*_WEIGHT` backend settings. Scores are normalized over criteria supplied or derived from supported symptom keywords. Ratings and real-time availability are not collected or displayed.
