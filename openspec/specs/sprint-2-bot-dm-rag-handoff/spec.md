# sprint-2-bot-dm-rag-handoff Specification

## Purpose

Sprint 2: Conversational Sales Bot for Instagram DMs using Qdrant RAG context, purchase intent classification (`purchase_intent`), automatic booking link generation, and human handoff.

## Requirements

### Requirement: REQ-DM-01 — Intent Classification for Direct Messages
The DM node MUST classify incoming messages into intent types (`purchase_intent`, `objection`, `question`, `spam`, `unclear`).

#### Scenario: DM-01-1 — Purchase intent detected
- GIVEN a message containing purchase or pricing keywords (e.g. "precio", "comprar", "demo")
- WHEN `classify_intent` is invoked
- THEN the classification returned is `"purchase_intent"`.

### Requirement: REQ-DM-02 — Grounded Reply Generation & Booking Link Injection
For purchase intent messages, the reply generator MUST append a direct booking link and trigger `requires_human = True`.

#### Scenario: DM-02-1 — Booking link injected for purchase intent
- GIVEN a DM state with `intent: "purchase_intent"`
- WHEN `node_dm_response` executes
- THEN the `reply_text` includes a Calendly booking link and `requires_human` is set to `True`.
