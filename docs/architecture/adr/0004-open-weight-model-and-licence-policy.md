# ADR-0004: Open-weight model choice and licence policy

- Status: Proposed (confirm after Phase-0 evaluation)
- Date: 2026-10-17

## Context
The product is meant to become commercial, and v0 should cost nothing to run. Several strong open image
models have non-commercial or research-only licences, which would block a commercial launch or force a rewrite.

## Decision
- **Policy:** only use models, LoRAs and auxiliary networks (segmentation, face embedding, upscalers)
  whose licence allows commercial use of both weights and outputs. Record each in
  `docs/architecture/licence-register.md` (name, official source, licence, commercial OK, date checked)
  before it's used in `packages/engine`. Download weights only from the publisher's official repository.
- **Default candidate:** FLUX.2 [klein] 4B (Apache 2.0), which supports multi-reference editing and fits
  on free-tier 16 GB GPUs (quantised versions on smaller cards).
- **To evaluate behind the same `TryOnEngine` interface:** dedicated open virtual try-on models
  (e.g. CatVTON, Leffa, Oxygen-TryOn) once their licences are checked, and a paid API as a quality baseline.

## Alternatives considered
- Non-commercial models (e.g. FLUX dev-licence variants) for v0: better quality now, but a rewrite or
  licence purchase before launch.
- Paid API only: best quality per effort, but per-image cost from day one.

## Consequences
- Possibly lower quality than closed frontier models; mitigated by candidates + ranking + curated bases.
- A licence check is a required step before any model change.
- Note: licences for auxiliary models (human parsing, face embeddings) are often the restrictive ones. Check them too.
