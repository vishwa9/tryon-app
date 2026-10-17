# ADR-0006: Branch and commit conventions

- Status: Accepted
- Date: 2026-10-17

## Context
The project starts solo but should be easy to hand to collaborators later. Consistent names make
history, PR lists and changelogs readable.

## Decision
- `main` is the protected default branch and changes only through squash-merged PRs.
- Branches: `<type>/<short-kebab-description>` (optionally with an issue number), where type is one of
  `feat, fix, docs, refactor, test, chore, infra, research`.
- Commits and PR titles: Conventional Commits, e.g. `feat(api): add job lease endpoint`.
- Releases: SemVer tags on `main`.

Details in [CONTRIBUTING.md](../../../CONTRIBUTING.md).

## Consequences
- A changelog can be generated from history later.
- Tool-generated branch names (e.g. from automation) are renamed to this format before opening a PR.
