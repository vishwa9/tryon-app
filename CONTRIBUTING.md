# Contributing

## Branches

- `main` is the default branch. It is always deployable and only changes through pull requests.
- Work happens on short-lived branches named:

  ```
  <type>/<short-kebab-description>
  <type>/<issue-number>-<short-kebab-description>   # once issues are used
  ```

| Type | Use for | Example |
|---|---|---|
| `feat/` | New user-facing behaviour | `feat/garment-upload-api` |
| `fix/` | Bug fixes | `fix/job-lease-expiry` |
| `docs/` | Documentation only | `docs/architecture-system-design` |
| `refactor/` | Code change with no behaviour change | `refactor/engine-interface` |
| `test/` | Tests only | `test/rank-scoring` |
| `chore/` | Tooling, dependencies, config | `chore/add-ruff` |
| `infra/` | Deployment, CI, Cloudflare config | `infra/wrangler-preview-env` |
| `research/` | Notebooks, experiments, eval sets | `research/klein-garment-swap` |

Rules: lowercase, hyphens only, no spaces or underscores, under ~50 characters,
one topic per branch. Delete the branch after merge.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/) with the same types as branches:

```
feat(api): add presigned upload endpoint for garments
fix(worker): renew lease before long swap step
docs(architecture): add job lifecycle state machine
```

Scope is optional and is usually the folder: `web`, `api`, `worker`, `engine`, `infra`, `architecture`.

## Pull requests

- One topic per PR, kept small enough to review in one sitting.
- **Squash merge** into `main`. The PR title becomes the commit message, so it follows the commit format above.
- The PR description says *what* changed, *why*, and *how it was tested*.
- An architectural change comes with a new or updated ADR in `docs/architecture/adr/`.

## Releases

Tag `main` with SemVer: `v0.1.0`, `v0.2.0`, … Pre-1.0 minor bumps may break things.
