# Releases and tag-only Cloud Build deployment

[Back to README](../README.md)

For local setup, tests and external data checks, see the
[development guide](development.md). For consumer-facing changes, see the
[API guide](api-guide.md#version-policy-and-30-migration).

The API maintains one live version. GitHub Actions checks pull requests and main.
`cloudbuild.yaml` validates release tags, builds and publishes container images,
then updates the existing Cloud Run service using the supplied GCP configuration.
Trigger filters are managed in GCP. Preparing a version, merging a PR, publishing
an image, creating a GitHub Release, and deploying are separate operations.

## Contents

- [Version source and compatibility](#version-source-and-compatibility)
- [Prepare a version](#prepare-a-version)
- [Configure the Cloud Build trigger in GCP](#configure-the-cloud-build-trigger-in-gcp)
- [Publish the initial 3.0.0](#publish-the-initial-300)

## Version source and compatibility

`pyproject.toml` is the source of the package version. Python `__version__`,
FastAPI/OpenAPI, discovery and MCP server metadata read installed distribution
metadata. The local package entry in `uv.lock` must match. Never patch a version
inside a build or deploy a different commit from the one tagged.

The [API guide](api-guide.md#version-policy-and-30-migration) documents compatibility
and the 3.0 breaking changes. The offline suite pins structured REST and MCP
contracts. PR CI also compares checked-in contracts with the base commit as data,
without executing base-commit code. Removals, changed schemas/defaults/constraints
and newly required inputs require a higher major version after publication, even
if a baseline was regenerated. Optional additions and enum extensions are allowed.

**Unreleased initial 3.0.0:** the course migration is part of 3.0.0, not 4.0.0.
When both PR base and head are exactly 3.0.0, CI passes `--check-publication` to
the release checker. It queries the exact `refs/tags/v3.0.0` ref in the fixed
authoritative `NTHU-SA/NTHU-Data-API` remote with `git ls-remote --exit-code --refs`.
Only a successful query establishing that the tag is absent permits same-version
contract changes. A stable tag freezes the contract even without a GitHub Release
page. Network/permission failures or unexpected output fail closed; missing local
tags in a shallow checkout are not evidence. Without this explicit publication
check, the ordinary strict major guard remains in effect. Other versions do not
receive this initial-release exception. Version decreases always fail.

The comparison is deliberately conservative: some safe schema changes may require
manual redesign or a major release. It cannot identify behavioral changes hidden
behind unchanged schemas, so retain query/error regression tests and review
migration notes. Do not disable the guard or refresh baselines to hide accidental
changes. Regenerate only for intentional reviewed changes:

```sh
uv run --locked python -m data_api.checks.openapi --write
uv run --locked python -m data_api.checks.mcp --write
```

## Prepare a version

Run **Prepare Release** from main with a stable `X.Y.Z` input. It rejects
non-increasing versions and existing tags, runs checks, updates the package and
lock metadata, and opens a version PR using the repository template.
It does **not** tag, merge or deploy.

`GITHUB_TOKEN`-created PRs do not normally trigger PR Actions. Preparation therefore
runs validation itself and explicitly dispatches Test and Lint on the resulting
branch so required checks can attach to the prepared commit. Only preparation
needs `contents: write`, `pull-requests: write`, and `actions: write`; normal CI
remains read-only. The repository must allow Actions to create PRs. Failures are
not silently bypassed; no personal access token is required.

Manual alternative, on a reviewed release-preparation branch:

```sh
uv run --locked python -m data_api.checks.release --next-version 3.0.1
uv version 3.0.1
uv lock --check
uv run --locked pre-commit run --all-files
uv run --locked --group test pytest -n auto tests --cov=src --cov=tests --cov-fail-under=85
uv run --locked python -m data_api.checks.openapi
uv run --locked python -m data_api.checks.mcp
uv run --locked python -m data_api.checks.release --tag v3.0.1
```

Replace the example version with the intended release. Inspect the diff: a normal
version preparation should change project metadata, not upgrade dependencies.
Review/merge only after required checks pass.
Protect main with required Test/Lint checks and require an up-to-date branch
(or a merge queue), so a successful check against an older base cannot authorize
a version decrease after another release PR merges.

## Configure the Cloud Build trigger in GCP

Use the existing repository connection; first-generation GitHub connections do
not need to be recreated just to switch from branch to tag events.

| Setting | Required value |
| --- | --- |
| Event | **Push new tag**, not branch push or GitHub Release |
| Tag RE2 expression | Stable `vX.Y.Z` only; copy the expression below |
| Invert expression | Disabled |
| Build configuration | Repository root `cloudbuild.yaml` at the tagged commit, not an inline configuration |
| Artifact Registry | Defaults to `asia-east1-docker.pkg.dev/nthusa-data-api/cloud-run-source-deploy/nthu-data-api/nthu-data-api` |
| Cloud Run | Defaults to existing `nthu-data-api` in `asia-east1` |

```text
^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$
```

No matching tags is expected until a release tag is pushed. Adding this YAML
does not change an existing trigger's event filters or disable old integrations.
Disable old branch-based deployment triggers before merging release changes.
Verify that ordinary main/PR events do not deploy.

The YAML preserves the provided `_AR_*`, `_SERVICE_NAME`, `_DEPLOY_REGION`,
`_PLATFORM`, `REPO_NAME` and `_TRIGGER_ID` substitutions. Keep the existing build
identity and verify any trigger-level overrides. If creating a new trigger instead
of editing the existing one, update `_TRIGGER_ID` to match.

The build identity needs source access, Artifact Registry Writer on the target
repository, permission to write Cloud Logging entries, permission to update the
existing Cloud Run service, and Service Account User on its runtime account.
No release-lock bucket or smoke-account token impersonation is required.

The configuration rejects missing tags and commits, and checks that
the stable release tag matches `pyproject.toml` and `uv.lock`. It installs locked
dependencies, runs formatting, full offline tests with the 85% coverage threshold,
and REST/MCP contract checks before building the existing Dockerfile with the
original `--no-cache` option. It pushes both `$TAG_NAME` and `$COMMIT_SHA` image
tags before updating Cloud Run to the commit-tagged image. The `images` setting
also records the published artifacts in Cloud Build. Source versions are never
rewritten during a build.

Deployment preserves the existing service configuration except for the image and
the existing Cloud Build tracking labels. The YAML does not add candidate
revisions, GCS locks, custom traffic promotion, authenticated smoke tokens or
automatic rollback. Monitor the deployment in GCP and use its service revision
controls if rollback is needed. The existing external API smoke check remains
available separately:

```sh
uv run --locked python -m data_api.checks.smoke --api-url https://api.nthusa.tw
```

Restrict release-tag creation/update/deletion to maintainers and prevent image
tag overwrites in Artifact Registry. If an immutable tag already exists with
different contents, investigate and prepare a new patch release; do not overwrite
it. A tag regex validates naming, not commit review or main-branch ancestry.

## Publish the initial 3.0.0

Do not tag the feature branch. After confirming the GCP trigger configuration,
merge and wait for successful checks. Fetch main and tags, inspect the exact
release commit and verify it is on main. Ensure `v3.0.0` does not already exist
locally or remotely. In a checkout of that reviewed main commit, run:

```sh
uv run --locked python -m data_api.checks.release --tag v3.0.0
git tag -a v3.0.0 -m "Release 3.0.0"
git push origin v3.0.0
```

Do not force-update a published tag. Follow Cloud Build through deployment,
verify the deployed image digest and discovery version, then
publish GitHub Release notes linking the migration guide. Publishing those notes
does not itself run this tag-triggered build. A successful image build alone does
not confirm a production release.

For subsequent releases follow the same procedure with the prepared version.
