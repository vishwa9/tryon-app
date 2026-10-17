# ADR-0005: Cloudflare Pages / Python Workers / D1 / R2

- Status: Accepted
- Date: 2026-10-17

## Context
The stack is FastAPI + React, and the owner wants to deploy on Cloudflare at near-zero cost.
The workload is image-heavy, but GPU work happens elsewhere (ADR-0002).

## Decision
- Web on **Pages**.
- API on **Python Workers** (FastAPI on Pyodide). The API is kept free of native and ML dependencies to fit.
  Fall back to **Cloudflare Containers** (Docker + uvicorn) if a dependency or limit blocks this. The app code stays the same.
- **D1** for metadata and the job table, **R2** for all images through presigned URLs,
  **Cron Triggers** for lease sweeps and cleanup, **Queues** only when v1 needs push to serverless GPU.
- A repository layer and an S3-compatible storage client keep D1/R2 swappable for SQLite/MinIO locally,
  or for Postgres/S3 later.

## Alternatives considered
- A VPS (e.g. Fly, Render, Railway) running FastAPI + Postgres: simpler Python runtime, but not Cloudflare, and costs money sooner.
- Next.js on Vercel: not the chosen stack.

## Consequences
- Very low fixed cost, global edge, no egress fees on images.
- Python Workers' constraints (Pyodide packages, CPU limits) shape the API: no image processing there.
- D1 size and write-throughput limits are acceptable at v0/v1 scale. Revisit if they become a constraint.
- Cloudflare limits and pricing change; re-check before each phase.
