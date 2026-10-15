# Releases and tag-only deployment

[Back to README](../README.md)

The API maintains one live version. GitHub Actions checks pull requests and main;
Cloud Build alone builds and deploys release tags. Preparing a version, merging a
PR, creating a GitHub Release, and deploying are separate operations.

**One-time GCP migration is required.** Adding `cloudbuild.yaml` does not disable
the existing branch trigger. Disable the old main-push deployment trigger
**before merging 3.0.0**, otherwise that merge can still deploy automatically.
Do not push `v3.0.0` until the tag trigger and its permissions have been verified.
This repository does not contain the live GCP trigger, service or IAM configuration.

## Version source and compatibility

`pyproject.toml` is the source of the package version. Python `__version__`,
FastAPI/OpenAPI, discovery and MCP server metadata read installed distribution
metadata. The local package entry in `uv.lock` must match. Never patch a version
inside a build or deploy a different commit from the one tagged.

The [API guide](api-guide.md#version-policy-and-30-migration) documents compatibility
and the 3.0 breaking changes. The offline suite pins structured REST and MCP
contracts. PR CI also compares checked-in contracts with the base commit as data,
without executing base-commit code. Removals, changed schemas/defaults/constraints
and newly required inputs require a higher major version, even if a baseline was
regenerated. Optional additions and enum extensions are allowed.

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

## Migrate the Cloud Build trigger

First export/inspect the existing trigger in the correct project and region.
Identify whether it is a first- or second-generation GitHub connection, its build
identity, and all other branch-based deployment integrations. Preserve the existing
Cloud Run service's runtime account, environment/secrets, ingress, resources,
scaling and network settings. Do not recreate the service.

Configure a trigger using the existing repository connection:

| Setting | Required value |
| --- | --- |
| Event | **Push new tag**, not branch push or GitHub Release |
| Tag RE2 expression | Stable `vX.Y.Z` only; copy the expression below. |
| Build configuration | Repository `cloudbuild.yaml` at the tagged commit |
| `_REGION` | Existing Cloud Run service region |
| `_SERVICE` | Existing Cloud Run service name |
| `_IMAGE` | Full Artifact Registry image path, without a tag, e.g. `asia-east1-docker.pkg.dev/PROJECT/REPOSITORY/nthu-data-api` |
| `_LOCK_BUCKET` | Private GCS bucket name for atomic per-region/service release locks |
| `_SMOKE_ACCOUNT` | Service account allowed to invoke the existing service |
| `_API_URL` | Canonical production API base URL; default `https://api.nthusa.tw` |

For copying into the console, the tag expression is:

```text
^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$
```

Use a dedicated build identity. Grant only the required repository/image access,
Artifact Registry writer, Cloud Run deployment/update access, ability to act as
the **existing** runtime service account, logging access and lock-bucket object
create/read/delete permissions. Scope storage permissions to that private bucket,
not project-wide storage administration.

The build identity also needs permission to mint an identity token by impersonating
`_SMOKE_ACCOUNT` (the appropriate service-account token-creation permission), and
that account needs Cloud Run Invoker on the service. Internal-only ingress requires
a compatible build worker network/private pool; IAM alone does not bypass ingress.
Do not make a private service public to pass smoke checks. Token audience is the
service's canonical Cloud Run URL; candidate and production checks use the token
without printing it or following redirects.

Enable immutable tags on the Artifact Registry repository to prevent overwriting
published version/commit image tags. Restrict creation, update and deletion of
GitHub `v*` tags with a ruleset. These are external administrator settings, not
effects of adding the YAML. Allow only release maintainers to create tags, and
verify their commit belongs to main with successful Test/Lint checks before pushing.
A tag regex validates naming, not review/ancestry.
With immutable image tags, rebuilding an already-pushed release can be rejected
if the new image digest differs. Do not force-overwrite it: inspect the previous
build and use a new patch release, or have an operator redeploy its verified
existing digest without rebuilding.

Disable the old main-push deployment trigger before merging. Once merged, point
the tag trigger at this config and verify its service account and substitutions.
Confirm ordinary main/PR events do not start a deployment. Keep scheduled offline
tests, external data checks and coverage upload; they do not deploy.

## What a release build does

1. Reject missing/malformed tags and mismatched `pyproject.toml`/`uv.lock` versions.
   Install locked dependencies with source builds enabled for jieba/local project;
   run formatting, full offline tests with the 85% coverage threshold, and both
   contract snapshots.
2. Build the existing Dockerfile once; push version and commit image tags. Read
   the pushed immutable digest and deploy that digest, never `latest`.
3. Atomically acquire a GCS lock with `if-generation-match=0`. Concurrent builds
   fail without touching the other build's lock or production traffic. Record
   the existing resolved revision allocation; first-ever service bootstrapping
   is intentionally out of scope and fails explicitly.
4. Deploy a tagged, no-traffic candidate revision without changing runtime
   configuration. Validate its discovery version and existing snapshot smoke
   checks via its authenticated tagged URL.
5. Only promote after candidate smoke passes and the previous production traffic
   allocation remains unchanged. Check the production URL's version and smoke.
   If that fails, restore the saved revision percentages and keep the build failed.
   Rollback pins the prior resolved revisions rather than floating to a future
   `LATEST` revision.
6. Remove the temporary candidate tag, delete the lock with its recorded generation
   precondition, and remove the temporary identity-token file.

The two smoke steps use Cloud Build `allowFailure` only to reach their mandatory
decision/rollback step. A missing success marker makes that step fail the whole
build; smoke failure is never treated as a successful release.
There are no automatic upstream retries. Dataset readiness can fail on a new
instance if the publisher is unavailable. `/ping` remains a smoke/readiness
inspection, never a startup or liveness probe.

If a build is canceled or killed while holding a lock, it intentionally leaves
the lock rather than allowing a second build to race unknown deployment work.
Inspect the owner/build ID in the lock object, verify the build has stopped and
the service traffic is safe, then delete **that exact object with its observed
generation precondition**. Never clear locks with a wildcard or automatically
steal a supposedly old lock. Cleanup/rollback permission failures keep the build
failed and require operator intervention.

## Publish the initial 3.0.0

Do not tag the feature branch. After the trigger migration, merge and successful
checks, fetch main and tags, inspect the exact release commit and verify it is
on main. Ensure `v3.0.0` does not already exist locally or remotely. In a checkout
of that reviewed main commit, run:

```sh
uv run --locked python -m data_api.checks.release --tag v3.0.0
git tag -a v3.0.0 -m "Release 3.0.0"
git push origin v3.0.0
```

Do not force-update a published tag. Follow Cloud Build through deployment,
verify the image digest/revision and discovery version, then publish GitHub
Release notes linking the migration guide. Publishing those notes does not
trigger another deployment. A version change in source or a successful image
build alone is not confirmation that production has been released.

For subsequent releases follow the same procedure with the prepared version.
For manual incident rollback, inspect the recorded allocation from the failed
build and restore those explicit revision percentages using
`gcloud run services update-traffic` with the correct project/service/region;
do not blindly deploy a moved tag or guess `LATEST`.
