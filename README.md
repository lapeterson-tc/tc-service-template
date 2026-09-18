# ThreatConnect API Service App — Template

A working starting point for a **ThreatConnect API Service App**: a Python
3.11 Falcon micro-service that runs inside a ThreatConnect instance, serves an
Angular single-page UI, and calls the platform API as the signed-in user.

It is a complete, buildable, installable app. Clone it, rename it, replace the
example feature, ship it.

```
ThreatConnect  ──proxy──▶  Falcon service  ──▶  ui_build/browser (Angular SPA)
                                │
                                ├─▶ /api/<feature>/...     your endpoints
                                ├─▶ /api/storage/...       backup + restore
                                └─▶ /api/tc/app-config     UI feature gating
```

## What you get

| | |
|---|---|
| **App shell** | Angular 18 SPA with hash routing, header + section nav, light/dark theming driven by the user's ThreatConnect preference, snackbar alerts, and a global error handler. |
| **Platform integration** | The `<base href>`-derived API base URL, the `//`-prefix convention for calling the platform API directly, a localhost dev proxy shim, and local stubs for ThreatConnect's private component library (so it builds with no private registry). |
| **Deep-link routing** | Declarative SPA route prefixes that 308 path-style links to the hash form, so bookmarks and reloads work. |
| **Persistence** | Org-namespaced on-disk JSON storage with atomic writes and fail-closed access control, plus backup/restore endpoints. |
| **AI** | An AWS Bedrock client with a boot preflight that gates the feature in the UI, and an example one-shot summarization endpoint. |
| **Design system** | Two-layer CSS tokens (platform `--tcl-*`, app `--app-*`) defined in dark/light pairs, so components need no per-theme overrides. See [DESIGN.md](DESIGN.md). |
| **Tests** | 74 Python tests and 14 UI specs, green, with the patterns documented. |
| **Docs** | Architecture, build/package, local development, and an admin installation guide with screenshots. |

## Quickstart

```sh
# 1. Rename it (dry run first; it generates a fresh appId)
python3 scripts/new_app.py --name "Threat Dashboard" --path threat_dashboard
python3 scripts/new_app.py --name "Threat Dashboard" --path threat_dashboard --apply

# 2. Build the UI
cd ui && npm install && npx ng build && cd ..

# 3. Vendor the Python dependencies, then package
tcex deps
tcex package            # -> target/<app_name>_v1.tcx

# 4. Install the .tcx -- see docs/installation-guide.md
```

Tests:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest

cd ui && npx ng lint && npx ng test --watch=false --browsers=ChromeHeadless
```

## The example feature

One end-to-end vertical slice, present so you can see every convention
working rather than infer it:

| Endpoint | Shows |
|---|---|
| `GET /api/example/dashboard` | Querying ThreatConnect as the calling user, spectree models, TTL+cooldown caching of instance metadata, graceful fallback, and the never-500 rule. |
| `GET\|PUT /api/example/preferences` | Org-namespaced per-user persistence, and the read-degrades / write-refuses contract. |
| `POST /api/example/ask-ai` | Bedrock invocation with pure, testable context builders and capped payloads. |

The UI side (`ui/src/app/components/dashboard/`) is a routed page with stat
tiles, a dependency-free SVG bar chart, a sortable table, real loading/empty/
error states, and its chart math extracted to a spec'd `util/` module.

**Delete `api/endpoint/example/`, `ui/src/app/components/dashboard/`, the
`example-service`, and their tests once your own feature replaces them.**

## Repository layout

```
run.py                  entrypoint; puts deps/ on sys.path, loops forever
app.py                  routes, middleware, preflight checks, SPA prefixes
app_inputs.py           service-config inputs (declare params here)
app_config_model.py     the /api/tc/app-config payload (UI feature gates)
bedrock.py              AWS Bedrock client
install.json            TC app manifest (generated from app_spec.yml)
app_spec.yml            manifest source of truth + release notes
tcex.json               packaging config and exclusions

core/                   app-agnostic framework -- prefer adding under api/
api/
  spec_tags.py          OpenAPI tags, one per feature area
  tql.py                safe TQL string literals
  endpoint/
    endpoint_base.py    the injected-attribute contract
    example/            the worked example feature
    storage/            backup + restore endpoints
    tc/                 localhost dev proxy shim
  storage/              DiskStore, org resolution, data-type registry
ui/                     Angular source (NOT packaged)
ui_build/browser/       ng build output (IS packaged, and is what runs)
tests/                  pytest
docs/                   architecture, build, local dev, install guide
scripts/new_app.py      rename this template into a new app
```

## Backup and restore

App data lives on the service container's disk, namespaced per organization.

```sh
BASE="https://<tc>/api/services/<your-api-path>/v1"

# export everything for the caller's org
curl -s "$BASE/api/storage/export" > backup.json

# export a subset, with secrets stripped
curl -s "$BASE/api/storage/export?types=example-preferences&redactSecrets=true"

# restore (merge skips existing rids; overwrite replaces them)
curl -s -X POST "$BASE/api/storage/import" \
  -H 'Content-Type: application/json' \
  -d "{\"mode\":\"merge\",\"bundle\":$(cat backup.json)}"
```

A restore **always writes into the calling user's organization** — the
bundle's own `orgKey` is informational and is never used to choose a
destination. That is what stops a restore from crossing into another org's
storage.

Exports include secrets verbatim unless `redactSecrets=true`; treat the files
as sensitive.

## Documentation

- [docs/architecture.md](docs/architecture.md) — request flow, middleware,
  routing, storage, conventions, and how to add a feature.
- [docs/build-and-package.md](docs/build-and-package.md) — the build order and
  the traps in it.
- [docs/local-development.md](docs/local-development.md) — the two dev loops
  and how the UI finds the backend.
- [docs/installation-guide.md](docs/installation-guide.md) — the admin
  walkthrough, with screenshots.
- [CLAUDE.md](CLAUDE.md) — the same ground rules, written for a coding agent.
- [PRODUCT.md](PRODUCT.md) / [DESIGN.md](DESIGN.md) — product framing and the
  visual system.

## Requirements

- ThreatConnect **7.2.0+**
- Python **3.11**
- Node 18+ / npm (Angular 18)
- The `tcex` CLI (`pip install tcex`) for `tcex deps` and `tcex package`

## Release notes

### 1.0.0

- Initial release.
