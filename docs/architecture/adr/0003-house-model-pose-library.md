# ADR-0003: House models + pose library instead of text-to-person

- Status: Accepted
- Date: 2026-10-17

## Context
Sellers need the same model to look the same across angles and SKUs, the garment to stay exact,
and photos to look like a real studio shoot. Generating a full person per request gives
inconsistent faces and lighting, and changes the garment.

## Decision
- A curator creates a small set of synthetic **house models**, each with a fixed **pose set**
  (front, 3/4 left, 3/4 right, side, back) in a neutral base outfit, same light and background,
  with precomputed clothing masks. Only approved bases are offered to sellers.
- Per job, only the clothing region of the matching base is regenerated, using the seller's flat-lay
  as reference. Pixels outside the mask are copied back.
- The back view requires a back photo of the garment; it is never inferred.

## Alternatives considered
- Text-to-image per job: inconsistent identity, garment drift.
- Per-seller identity LoRA from day one: more GPU cost and curation; deferred to "brand model" later.
- Real human models from sellers: consent and likeness risk; deferred until there's a consent flow.

## Consequences
- Consistency and realism come mostly from curated bases, which are produced once and reused.
- Pose variety is limited to the library; new poses mean curator work.
- Silhouettes very different from the base outfit (long dresses) need category-specific bases.
