# EB-Plum fork maintenance

## Branches and automation

- `main` is an exact mirror of `rangermix/TwitchDropsMiner:main`, including its
  workflow files. It is not the personal deployment branch. Update it only by
  fast-forward; investigate any upstream rewrite instead of forcing it automatically.
- `fork/production` is the fork's default branch and contains the GHCR workflow,
  personal Compose settings, and these operating instructions. Merge updates into
  it; do not squash upstream merges or force-push this shared branch.
- `codex/sync-upstream-YYYY-MM-DD` is a temporary integration/review branch.
- `backup/main-before-mirror-2026-11-01` retains the pre-migration main history.
  Keep an independently verified Git bundle as an additional recovery copy.

Repository configuration must disable these inherited workflows in this fork:
`validation.yml`, `contributors.yml`, `docker-release.yml`, `github-release.yml`,
`version-release.yml`, `wiki.yml`, and the retired `docker-ghcr.yml`.
Do not delete or modify inherited workflow files on the mirror. Keep
`login-helper.yml` enabled: `fork-ci.yml` invokes its read-only native helper builds.
Its inherited manual dispatch remains a read-only exception to production-branch CI.
Audit every upstream `.github/workflows` addition or change **before** updating the
mirror; a newly added workflow is not covered by an existing disabled-file list.
Never provide upstream publishing workflows with personal publishing credentials.
The contributor workflow can write to the default branch and must remain disabled.

`fork-ci.yml` automatically validates pushes to `fork/production` and PRs targeting
it. Python tests, Ruff, Mypy, language validation, lockfile checks, release-script
contracts, native helper builds, and both Docker architectures must succeed before
publication. PR runs cannot publish; only a push to this exact repository's
`fork/production` can obtain package-write permission in the publishing job.
Manual dispatch and tag pushes do not publish images. The job first pushes a uniquely
named candidate image, then checks the remote production head immediately before
promoting its digest to `latest`; stale reruns cannot intentionally roll deployment
back to an older commit. Do not rerun superseded commits to perform a rollback.

## Update procedure

Use a clean checkout; preserve any local edits before switching branches. Configure
`upstream` once as `https://github.com/rangermix/TwitchDropsMiner.git`.

```bash
git fetch origin
git fetch upstream
# Review upstream workflow changes and release/migration notes first.
git diff origin/main..upstream/main -- .github/workflows/
git switch main
git merge --ff-only origin/main
git merge --ff-only upstream/main
git push origin main

git switch -c codex/sync-upstream-YYYY-MM-DD origin/fork/production
git merge origin/main
# Resolve conflicts without losing personal settings, inspect, and test.
git push -u origin HEAD
```

Open the integration PR against **EB-Plum/TwitchDropsMiner:fork/production**, not
against upstream or the mirror. Use a merge commit so upstream ancestry remains
recorded. Review the complete change and final CI results before merging. The
subsequent production push reruns validation and publishes only if it passes.
Do not weaken tests or report a skipped/unrun check as successful. Existing upstream
failures still block publication until investigated and resolved or explicitly
handled through a separate reviewed decision.

The one-time mirror migration is different from routine updates: first create and
verify remote backup refs and a complete Git bundle, prepare the production branch,
disable inherited publishing/contributor workflows, then update `main` with an
explicit old-SHA lease. Never use unconditional `--force`, `push --mirror`, or delete
unrelated branches/tags. Protect the resulting mirror against future force pushes.

## Images, deployment, and rollback

The existing Compose file preserves the GHCR image, Asia/Seoul timezone, ports,
data/log mounts, and Watchtower. Continue using it from `fork/production`, **not**
from `main`, whose Compose file is the upstream source-build configuration.

A successful production run publishes:

- `ghcr.io/eb-plum/twitch-drops-miner:latest`, the moving deployment tag;
- `sha-<full-commit>-<run-id>-<attempt>`, a unique build tag that this workflow does
  not reuse across reruns;
- the registry digest in the job summary for exact rollback. Tags are not registry-
  enforced immutable references; use `ghcr.io/eb-plum/twitch-drops-miner@sha256:...`
  for an immutable image reference.

The configured Watchtower checks hourly and can replace the running container after
`latest` changes. Its `--cleanup` can remove old local images. Before migration or
riskier upgrades, pause Watchtower on the actual host, save the running image digest,
and back up the persistent data directory using a consistent stopped-app snapshot.
Repository changes do not themselves pause Watchtower or back up host data.
Do not publish a trial image under `latest`.

For rollback, pause Watchtower, set the Compose image to the saved digest, pull and
recreate the miner with the same mounts, then verify its health and login. Do not use
`down -v`. Image rollback does not reverse data-format migrations; consult release
notes and restore a compatible data backup only when needed. Resume automatic updates
only after deciding which image/tag should be followed.
