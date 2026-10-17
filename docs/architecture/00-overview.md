# 00 — Overview

## Problem

Small online clothing sellers (Instagram shops, marketplace sellers, small D2C brands)
need photos of their products **on a person** to sell well, but a studio shoot with
a model, photographer and location is expensive for each new SKU. Today they:

- post flat-lays or hanger shots, which convert worse, or
- skip photos for many SKUs, or
- reuse supplier photos that don't match the actual product.

## Product in one sentence

Upload a photo of a garment (front and back), choose a ready-made AI model, choose the
angles, and get realistic catalog photos of that model wearing that exact garment.

## Users

| Persona | Needs |
|---|---|
| **Seller** (primary) | Fast, cheap, consistent catalog photos; little effort; photos that show the real product |
| **Curator / admin** (you, early on) | Create and approve the "house models" and pose sets; review failures; manage credits |
| **Shopper** (indirect) | Photos that show the product honestly, including colour, print and fit |

## Goals

**v0: prove it (free, batch)**
- G1. Generate on-model photos for **simple upper-body garments** (t-shirts, shirts, kurtas, tops) at catalog quality for at least 70% of attempts.
- G2. Support **front, 3/4 left, 3/4 right and back** views from one front + back upload.
- G3. The same model identity looks the same across all angles and SKUs.
- G4. Run at ~₹0 infrastructure cost, with results in hours.

**v1: first real sellers**
- G5. Results in minutes (serverless GPU).
- G6. More categories (dresses, bottoms, ethnic sets), more body types and skin tones.
- G7. Credits and billing; bulk upload.

## Non-goals (for now)

- Generating garments that don't exist, or "improving" the product's look. **Garment fidelity beats prettiness.**
- Video, 360° spins, or interactive try-on for shoppers.
- Seller-uploaded photos of real people as models (consent and likeness risk). Planned for later, with an explicit consent flow.
- Training models on sellers' images.

## Quality bar ("catalog quality")

A generated photo passes when **all** of these hold:
1. The garment matches the upload: colour, print/logo placement, neckline, sleeve length, buttons, pockets.
2. No obvious artefacts: hands, fingers, collar edges, text in prints.
3. The face and body are the approved house model's.
4. Studio look: even lighting, clean background, sharp at 1024 px or more.

Measured with the fixed evaluation set in `research/eval/` (see [03](03-generation-pipeline.md#evaluation)).

## Constraints

- **Cost:** Start on free tiers (Cloudflare free plan, free GPU notebooks or a local GPU).
- **Licensing:** Only models and LoRAs whose licence allows commercial use of the weights *and* outputs. Kept in a licence register ([ADR-0004](adr/0004-open-weight-model-and-licence-policy.md)).
- **Stack:** FastAPI (Python) + React, deployed on Cloudflare ([ADR-0005](adr/0005-cloudflare-platform.md)).
- **Disclosure:** Every output is labelled as AI-generated, visibly and in metadata (India IT Rules amendments 2026; ASCI guidance). Not legal advice; review before launch.

## Key ideas (details in later docs)

1. **House models + pose library**, created once and approved by a person, instead of generating a new person from text each time. This gives consistency and realism ([ADR-0003](adr/0003-house-model-pose-library.md)).
2. **Mask-based garment swap** on an approved base image, one per angle. Only the clothing pixels change.
3. **The back view needs a back photo.** The AI must not invent the back of a product.
4. **API and GPU are decoupled.** GPU workers *pull* jobs, so free and ephemeral GPUs work, and swapping to paid GPUs later is a config change ([ADR-0002](adr/0002-pull-based-gpu-worker.md)).
