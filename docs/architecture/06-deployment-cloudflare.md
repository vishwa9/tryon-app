# 06 — Deployment on Cloudflare

> Cloudflare product limits and free-tier allowances change often. Check every number here
> against the current Cloudflare docs before relying on it.

## What runs where

| Piece | Cloudflare product | Notes |
|---|---|---|
| Web (React) | **Pages** | Static build of `apps/web`; preview deployment per branch |
| API (FastAPI) | **Python Workers** (first choice) or **Containers** (fallback) | See decision below |
| Metadata + job table | **D1** | One database per environment |
| Images | **R2** | One bucket per environment; S3-compatible presigned URLs |
| Expiry sweep, cleanup | **Cron Triggers** | Every 5 min: reclaim leases; daily: lifecycle housekeeping |
| Push to serverless GPU (v1) | **Queues** | Not used in v0 |
| Auth for admin pages | **Access** (optional) | Zero-trust gate in front of `/admin` |
| GPU | *Not on Cloudflare* | Kaggle / Colab / local in v0; Modal / RunPod serverless in v1 |

### API runtime: Python Workers vs Containers

- **Python Workers** run Python on Pyodide (WebAssembly) and support FastAPI. They are cheap and have no cold-start cost to manage, **but** only pure-Python packages or packages Pyodide ships work, and there are CPU-time and memory limits per request. Our API is kept ML-free and moves no image bytes, so it should fit.
- **Containers** run an ordinary Docker image (uvicorn + FastAPI), so any Python dependency works. They need a paid Workers plan and have container start-up time.

**Decision:** design the API to be Pyodide-friendly (no native deps, D1 through bindings or
HTTP, S3 signing with a pure-Python implementation) and deploy to Python Workers. If a
dependency blocks this, switch to Containers. The FastAPI code is the same; only the entrypoint differs.
Recorded in [ADR-0005](adr/0005-cloudflare-platform.md).

## Environments

| Env | Web | API | D1 / R2 | GPU worker |
|---|---|---|---|---|
| `local` | `vite dev` | `uvicorn` | SQLite file + MinIO (docker compose) | `MockEngine` on CPU, or local GPU |
| `preview` | Pages preview per PR | `wrangler deploy --env preview` | `tryon-preview` | Mock or shared Kaggle worker |
| `production` | Pages production (`main`) | `wrangler deploy --env production` | `tryon-prod` | Real workers |

Configuration lives in `infra/wrangler.toml` with `[env.preview]` and `[env.production]` sections.
Secrets (`SESSION_SECRET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, email provider key) go in
`wrangler secret put` per environment, and locally in `.dev.vars` (git-ignored). Never commit them.

## CI/CD (GitHub Actions)

On every pull request:
1. `ruff` + `mypy` + `pytest` for `apps/api`, `apps/worker`, `packages/engine` (with `MockEngine`, no GPU).
2. `eslint` + `tsc` + `vitest` for `apps/web`.
3. OpenAPI drift check: regenerate the TS client and fail if it differs.
4. Deploy a preview (Pages + API `preview` env) and post the URL.

On merge to `main`:
1. Apply D1 migrations to production.
2. Deploy API, then web.
3. Tag the release when you choose to.

GPU-heavy evaluation is **not** in CI. It runs manually in notebooks against the fixed eval set,
and the results are committed as reports under `research/eval/reports/`.

## Running the v0 GPU worker on Kaggle / Colab

1. Notebook installs `packages/engine` and `apps/worker` from the repo.
2. Reads `API_BASE_URL` and `WORKER_TOKEN` from the notebook's secrets store (Kaggle Secrets / Colab userdata), never from the notebook text.
3. Downloads weights from the official Hugging Face repo and caches them in the session.
4. Runs the worker loop until the session ends. Leases left behind expire and are retried by another worker.

Check each platform's terms of service for long-running or service-like use before relying on it.
