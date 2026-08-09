# Review Policy — wire-feature-views-to-real-data

- Mode: openspec. Lineage: `wire-feature-views-to-real-data`.
- Initial snapshot: `77d4ea1` (post-apply, pre-correction). Final candidate: current HEAD `b104974`.
- Risk tier: HIGH (auth/tenant-isolation/webhook-secret surface; authored lines > 400) → full 4R initial sweep.
- Corroboration: R1-001 and R1-002 were deterministic CRITICALs (code inspection + repro) → corroborated with proof, NO refuter launched (no inferential severe candidates existed).
- WARNING/SUGGESTION rows are non-blocking `info` and never drive correction.
- Correction: exactly ONE correction transaction; each work unit maps 1:1 to frozen blocking IDs (R1-001, R1-002). Scope: only main.py, routers/ingestion.py, tests.
- Scoped fix-delta validation: exactly ONE, verdict `approve`.
- Final verification: exactly ONE independent requirements/runtime verification, verdict `approved`.
- Terminal state: `approved`. Only `approved | escalated` are terminal.
- Pre-commit/pre-push/pre-PR lifecycle: validate THIS content-bound receipt with native review-validate; never create a new review budget.