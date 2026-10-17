# ADR-0001: Monorepo layout

- Status: Accepted
- Date: 2026-10-17

## Context
One developer builds a web app, an API, a GPU worker, and research notebooks that share
the same image pipeline. Keeping them in sync across repositories would cost more than it saves.

## Decision
One repository with `apps/web`, `apps/api`, `apps/worker`, `packages/engine`, `research/`, `infra/`, `docs/`.
`packages/engine` is an installable Python package used by both the worker and the notebooks.
The API never depends on `packages/engine`.

## Alternatives considered
- Separate repos per app: more overhead, harder atomic changes to API + worker protocol.
- Notebook-only pipeline copied into the worker: guarantees drift between research and production.

## Consequences
- One PR can change the protocol on both sides.
- CI must run per-path jobs so web changes don't trigger Python tests and vice versa.
