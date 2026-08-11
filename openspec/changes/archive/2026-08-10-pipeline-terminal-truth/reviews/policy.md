# Review Policy — pipeline-terminal-truth

- Operation: `review/start(target=pipeline-terminal-truth)` — bounded, detached, read-only, terminal after one result.
- Risk tier: **High** → exactly four initial lens sweeps: review-risk, review-resilience, review-readability, review-reliability. No extra sweeps, no three-refuter pattern.
- Findings freeze after the initial lens sweeps. Lens reviewers are read-only: no edits, no lifecycle routing, one result each, then terminate.
- Evidence routing: deterministic severe → corroborated (no refuter). Inferential severe → merged into exactly ONE refuter batch (one result per finding). Insufficient → inconclusive (never auto-fixed).
- Correction: at most one correction transaction; work units map to frozen accepted/blocking IDs only. If correction occurred: exactly one scoped fix-delta validator (approve | escalate).
- Final verification: independent requirements/runtime verification → approved | escalated (terminal).
- Persistence: transaction.json, policy.md, ledger.json, receipt.json, chain-bundle.json, gate-context.json under openspec/changes/pipeline-terminal-truth/reviews/.
- WARNING/SUGGESTION rows are `info`; never drive correction or block approval.
- Approval source: session preflight (execution_mode auto; delivery chained stacked-to-main; size:exception APPROVED; review_budget_lines 400).
