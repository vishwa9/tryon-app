# 02 — Components

Each component has one job. The boundaries matter most where heavy ML code meets
the lightweight web stack, so **only `packages/engine` and `apps/worker` import ML libraries.**

## Web: `apps/web`

- React + Vite + TypeScript, deployed as static assets on Cloudflare Pages.
- Screens:
  1. **Upload garment:** front photo (required), back photo (required for the back view), category, optional SKU/name. Checks size, type and orientation on the client, shows tips ("plain background, lay flat, no shadows").
  2. **Pick model:** grid of approved house models with attribute filters (gender presentation, height, skin tone, body type).
  3. **Pick angles:** front, 3/4 left, 3/4 right, back, side (beta). Shows which are unavailable (e.g. no back photo).
  4. **Job status:** queued / processing / done, with an ETA.
  5. **Gallery:** candidates per angle, pick favourites, download ZIP, regenerate one angle.
  6. **Admin (role-gated):** house-model and pose approval, failed-job review.
- Talks to the API with JSON only. Uploads to and downloads from R2 through presigned URLs.
- **Does not** hold secrets or call model providers.

## API: `apps/api`

- FastAPI, Pydantic models, versioned under `/v1`.
- Owns: authentication, authorisation (seller owns garment/job), validation, presigned URL issuing, the job state machine, credits, the house-model catalog.
- Data access through a small repository layer, so D1 (production) and SQLite (local/tests) share code. D1 is SQLite, so the SQL is the same.
- Storage access through an S3-compatible client (R2 speaks the S3 API; MinIO locally).
- **Does not** import torch, diffusers or opencv, and does not touch image bytes beyond a header check.
- Stateless, so any instance can serve any request.

Module sketch:
```
apps/api/
  app/main.py            FastAPI app, middleware (request id, CORS, errors)
  app/routers/           garments.py, jobs.py, house_models.py, worker.py, admin.py
  app/services/          job_service.py (state machine), credit_service.py
  app/repositories/      d1.py, sqlite.py (same interface)
  app/storage/           r2.py (presign, head)
  app/auth/              session.py, worker_token.py
  app/schemas/           Pydantic request/response models
  tests/
```

## Worker: `apps/worker`

- Long-running Python process: **lease → process → upload → complete**, in a loop.
- Runs anywhere with a GPU and outbound HTTPS: Kaggle/Colab notebook cell, home PC, later a Modal/RunPod serverless function.
- Sends a heartbeat during long steps so the lease doesn't expire.
- Loads model weights once per process, keeps them warm, and processes many jobs.
- Config through env vars: `API_BASE_URL`, `WORKER_TOKEN`, `ENGINE=mock|klein|...`, `DEVICE`, `MAX_CANDIDATES`.

## Engine: `packages/engine`

The image pipeline as a plain Python library, used by **both** the worker and the research notebooks.
Experiments therefore turn into production code with no rewrite.

```
packages/engine/
  tryon_engine/
    interfaces.py   TryOnEngine protocol, dataclasses (GarmentInput, PoseBase, Candidate)
    segment.py      garment segmentation on flat-lays, clothing masks on bases
    swap/           mock.py, klein_multiref.py, (later) vton_<model>.py
    rank.py         fidelity / identity / artefact scoring
    postprocess.py  upscale, background, crop to catalog ratios
    label.py        visible watermark + IPTC/C2PA "AI-generated" metadata
  tests/
```

See [03](03-generation-pipeline.md) for the algorithms.

## Data stores

| Store | Holds | Why |
|---|---|---|
| D1 | sellers, garments, house models, poses, jobs, results, credits | Relational, transactional job leasing, free tier |
| R2 | all image bytes | S3 API, zero egress fees, presigned URLs |
| Hugging Face / worker disk | model weights | Too large for R2 at our scale; cached per worker |

## Cross-cutting

- **Request/job id** passed through web → API → worker logs.
- **Feature flags** in a small `config` table (e.g. enable side view, choose default engine).
- **Error taxonomy** shared by API and worker: `INPUT_INVALID`, `SEGMENTATION_FAILED`, `LOW_FIDELITY`, `GPU_OOM`, `TIMEOUT`, `INTERNAL`.
