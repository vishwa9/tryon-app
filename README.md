# TryOn App

AI-generated **on-model catalog photos** for small online clothing sellers.

Studio shoots are expensive, so most small sellers use flat-lays or no photos at all.
TryOn App turns a garment photo into realistic photos of a model wearing it, from
several angles, with a simple flow: **pick garment → pick model → pick angles → download**.

> Status: **design phase**. No application code yet. Start with the
> [architecture docs](docs/architecture/00-overview.md).

## Repository layout

```
apps/
  web/        React + Vite + TypeScript seller app (Cloudflare Pages)
  api/        FastAPI service (Cloudflare) — no ML dependencies
  worker/     GPU job runner (Kaggle/Colab/local GPU → serverless GPU later)
packages/
  engine/     Shared Python image pipeline (segment, swap, rank, post-process)
research/     Notebooks and evaluation sets used to validate model quality
infra/        Wrangler config, Dockerfiles, CI helpers
docs/
  architecture/   System design documents and ADRs
```

## Documentation

| Doc | What it covers |
|---|---|
| [00 Overview](docs/architecture/00-overview.md) | Problem, users, goals, non-goals, constraints |
| [01 System context](docs/architecture/01-system-context.md) | C4 context and container diagrams |
| [02 Components](docs/architecture/02-components.md) | What each component does and does not do |
| [03 Generation pipeline](docs/architecture/03-generation-pipeline.md) | How realistic multi-angle photos are produced |
| [04 Data model](docs/architecture/04-data-model.md) | Entities, schema, object storage layout |
| [05 API contracts](docs/architecture/05-api-contracts.md) | REST endpoints, job lifecycle, worker protocol |
| [06 Deployment](docs/architecture/06-deployment-cloudflare.md) | What runs where on Cloudflare, environments, CI |
| [07 Non-functional](docs/architecture/07-nfr.md) | Cost, scaling, security, privacy, observability |
| [ADRs](docs/architecture/adr/) | Architecture decision records |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit messages and PR rules.
