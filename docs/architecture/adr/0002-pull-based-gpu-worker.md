# ADR-0002: Pull-based GPU worker, decoupled from the API

- Status: Accepted
- Date: 2026-10-17

## Context
Inference needs a GPU. v0 must be free, so GPUs come from Kaggle/Colab notebooks or a home PC.
These have no public endpoint, can stop at any time, and come and go. Cloudflare doesn't run our
custom PyTorch pipeline.

## Decision
- The API stores jobs in D1 with lease columns. Workers call `POST /v1/worker/lease` over outbound HTTPS,
  send heartbeats, and report completion. Expired leases are re-queued (max 3 attempts).
- All image transfer goes through presigned R2 URLs; the API only handles JSON.
- In v1, serverless GPUs (Modal/RunPod) may be triggered through Cloudflare Queues, with the same
  worker code and the D1 job table still the source of truth.

## Alternatives considered
- API calls GPU synchronously: impossible with free notebooks; fragile and slow requests.
- Cloudflare Queues from day one: extra moving part before it's needed; pull consumers are possible later.
- Hosted inference API only: simplest, but costs money per image and limits model choice.

## Consequences
- Free and ephemeral GPUs work, and adding capacity means starting another worker.
- Turnaround depends on a worker being online in v0. This is acceptable for a batch product.
- Need lease-expiry handling, idempotent result keys, and a stale-worker check.
