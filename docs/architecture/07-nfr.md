# 07 — Non-functional requirements

## Performance targets

| Metric | v0 (free, batch) | v1 (paid GPU) |
|---|---|---|
| API p95 latency (non-upload) | < 300 ms | < 200 ms |
| Job turnaround (4 angles × 4 candidates) | < 6 h when a worker is online | < 5 min |
| GPU time per candidate (1024 px) | measure in Phase 0 | measure in Phase 0 |
| Availability | best effort | 99.5% for the API; GPU degrades to "queued" |

## Cost model

```
cost per job ≈ angles × candidates × GPU-seconds per candidate × GPU price per second
             + storage (≈ negligible at small scale; R2 has no egress fees)
```

Example *to be replaced with measured numbers*: 4 angles × 4 candidates × 20 s = 320 GPU-s.
On a ~$1/h GPU that's ≈ $0.09 per job, about $0.02 per delivered angle. Levers:
fewer candidates once ranking is trusted, caching prepared garments, smaller
resolution + upscale, batching angles on one warm GPU.

v0 infrastructure target: **₹0/month** (Cloudflare free tiers, free notebooks or a home GPU).
The first paid line item is likely serverless GPU, then possibly the Workers paid plan.

## Scaling path

1. **v0:** 1 API, 1–2 pull workers, D1 job table. Fine for tens of jobs a day.
2. **v1:** Serverless GPU (Modal/RunPod) triggered by Cloudflare Queues; autoscale on queue depth; keep the D1 job table as the source of truth.
3. **Later:** Sharded or separate queues by priority (paid vs free), regional R2 buckets, read replicas if D1 limits bite, or move metadata to Postgres (the repository layer isolates this).

What scales independently: the **pose library** (curator work), **GPU capacity** (workers), and **sellers** (stateless API).

## Security

- **Auth:** email magic link + HttpOnly, Secure, SameSite=Lax session cookie. Admin routes need `role=admin` and optionally Cloudflare Access.
- **Authorisation:** every query is scoped by `seller_id`. R2 keys are prefixed by seller id and only ever exposed as presigned URLs valid for ≤ 15 minutes.
- **Worker tokens:** random 256-bit, hashed at rest, scoped to `/v1/worker/*`, revocable, one per worker.
- **Uploads:** content-type allow-list (JPEG, PNG, WebP), size limit (e.g. 15 MB), dimension limits; decoded and re-encoded on the worker, never served as uploaded.
- **Abuse:** rate limits per seller and IP; credits cap GPU spend; garments only (the pipeline segments clothing and rejects inputs with a person or face in them).
- **Supply chain:** pinned dependencies, weights only from official model repos with checksums recorded in the licence register.

## Privacy & compliance

- Seller images are used **only** to fulfil their jobs. No training on them without explicit opt-in.
- Seller can delete a garment or their whole account; deletion removes D1 rows and the R2 prefix.
- **AI disclosure:** visible label + IPTC/C2PA metadata on every output, and a terms-of-use clause asking sellers to keep the disclosure when they publish.
- House models are synthetic. Never generate a likeness of a real person, and never accept seller uploads of real people as models until there is a consent flow.
- Model/LoRA **licence register** (`docs/architecture/licence-register.md`, created in Phase 0) records each model's name, source, licence, whether commercial use is allowed, and the date checked.
- Not legal advice: get the India IT Rules / ASCI and data-protection (DPDP Act) position reviewed before onboarding real sellers.

## Observability

- Structured JSON logs with `request_id`, `seller_id`, `job_id`, `worker_id`.
- Per-job metrics stored on the job: queue wait, GPU time per angle, candidate scores, engine version.
- Simple admin dashboard: jobs by state, failure codes, mean scores by engine version, worker last-seen.
- Alerts (later): no worker seen for > 1 h while jobs are queued; failure rate > 30% over 1 h.

## Reliability

- Lease + heartbeat + retry (max 3) handles workers that disappear.
- Partial success per angle; credits only for delivered angles.
- Idempotent writes (deterministic result keys, idempotency keys on job creation).
- D1 backups through Time Travel; R2 contents are reproducible except originals, so originals are never auto-deleted.
