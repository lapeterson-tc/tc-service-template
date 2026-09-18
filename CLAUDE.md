# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Overview

A template for a ThreatConnect **API Service App** (Python 3.11): a Falcon
REST API that ships an Angular UI and runs *inside* a ThreatConnect Threat
Intelligence Platform instance.

It is a complete, buildable app, not a skeleton. It carries one **example
feature** (`api/endpoint/example/` + `ui/src/app/components/dashboard/`) whose
only job is to demonstrate every convention end to end. When a real feature
replaces it, delete it — including its tests.

- Min ThreatConnect server version: **7.2.0**
- Runtime level: `ApiService` (a long-running micro-service, not a one-shot job)
- Identity lives in `install.json` / `app_spec.yml`; `scripts/new_app.py`
  rewrites it.

## Commands

Python tests (`tests/`, pytest, dev-only — excluded from the packaged `.tcx`):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt   # once
.venv/bin/python -m pytest
```

UI, from `ui/`:

```sh
npm install
npx ng build     # -> ../ui_build/browser   (NOT ui/dist)
npx ng lint      # must stay clean; --fix handles prettier
npx ng test --watch=false --browsers=ChromeHeadless
npx ng serve     # dev server on :4200, proxies /api -> :8052
```

Full build and package:

```sh
cd ui && npm install && npx ng build && cd ..
tcex deps       # vendors Python deps into deps/
tcex package    # -> target/<app_name>_v1.tcx
```

There is **no Python linter**. For anything the test suite doesn't cover,
verify by reading/tracing code.

`conftest.py` puts the repo root and `deps/` on `sys.path`, mirroring
`run.py`. Endpoint tests need `deps/` and skip themselves with
`pytest.importorskip` otherwise; pure-logic tests always run. Both states
should be green — check with `mv deps deps.bak && pytest; mv deps.bak deps`.

## What an "API Service App" is

ThreatConnect runs the app as a persistent micro-service and proxies requests
to it under a per-app path, `/api/services/{userPath}/v1/`. The app
authenticates back to the platform using the **calling user's session**, so
every action runs with that user's permissions. The app never knows its own
absolute URL — most of the routing design follows from that.

Full detail in `docs/architecture.md`. The rules below are the ones that bite.

## Hard rules

**Never 500.** A failed upstream call returns HTTP 200 with a populated
`error` field and whatever partial data exists. The UI can render a degraded
panel; it cannot render a stack trace. Real error statuses are for the
caller's own mistakes (400) and refused writes (503).

**Query ThreatConnect as the caller**, via `self.tcex.session.tc` or
`self.tcex.api.tc.v3.*`. Never substitute a service identity to make a query
work — that silently escalates privilege. Don't mix raw-session and
v3-object calls in one code path.

**Build TQL literals with `api/tql.py:tql_quote`.** Escaping only the double
quote is not enough: a trailing backslash escapes the escape and breaks out of
the literal. Prefer `filter.*(TqlOperator.EQ, value)` when a v3 collection
object is already in hand.

**Endpoints are singletons with no `__init__`.** Middleware injects
`self.tcex` / `self.log` / `self.app_config` / anything in
`app.py:App.middleware` onto each resource instance, **by kwarg name**. Keep
`api/endpoint/endpoint_base.py`'s annotations in sync with that kwarg list.
Never hold per-request state on `self`, and remember anything cached at class
level is shared **across users** — cache instance metadata only.

**Storage goes through `safe_datastore(tcex, log, data_type)`.** Never
construct a `DiskStore`. It returns `None` on failure and callers must
degrade: **defaults on read, an explicit 503 on write**. A write that silently
no-ops loses the user's data without telling them. The org namespace
(resolved from the caller's session, failing closed) is the ONLY
access-control boundary — never fall back to a shared or default namespace.

**Register every `data_type` in `api/storage/registry.DATA_TYPES.`** That list
drives backup/restore; an unregistered type is silently missing from every
export.

**Add every new top-level client route to `App.spa_route_prefixes`** as well
as to `ui/src/app/app-routing.module.ts`. Miss it and a bookmarked or reloaded
link renders a white page with no error.

**`/api/tc/app-config` serializes with `by_alias=False`**, so multi-word
fields reach the UI **snake_case** (`schema_version`). Do not "correct" the
TypeScript interface to camelCase — it will read as `undefined` and quietly
disable whatever it gates.

**Pin anything that constrains pydantic.** tcex pins pydantic 1.x; a
dependency that moved to v2 kills the app at import with `cannot import name
'RootModel' from 'pydantic'`. `spectree` is pinned `>=1.5.8,<2` for exactly
this. After editing `requirements.txt`, `rm -rf deps requirements.lock &&
tcex deps` — `tcex deps` prefers the lock.

**Rebuild the UI before packaging.** `tcex.json` excludes `ui/`, so only
`ui_build/browser` ships. Forgetting means shipping a stale UI against fresh
backend code.

## Backend layout

```
run.py                  entrypoint; deps/ on sys.path, then loop forever
app.py                  routes, middleware, preflight checks, SPA prefixes
app_inputs.py           AppBaseModel -- one field per app_spec.yml param
app_config_model.py     the /api/tc/app-config payload (UI feature gates)
bedrock.py              AWS Bedrock client (MODEL_ID / REGION_NAME constants)
core/                   app-agnostic framework -- add features under api/, not here
api/
  spec_tags.py          OpenAPI tags, one per feature area
  tql.py, debug_log.py  shared helpers
  endpoint/endpoint_base.py    injected-attribute contract
  endpoint/example/     the worked example (delete when replaced)
  endpoint/storage/     GET /api/storage/export, POST /api/storage/import
  endpoint/tc/          /api/tc/proxy-local dev shim
  storage/              DiskStore, org resolution, DATA_TYPES registry
```

Adding an endpoint: class under `api/endpoint/<feature>/` extending
`EndpointBase`, spectree request/response models, `@spec.validate(...,
tags=[...])`, then register the route in `app.py:App.routes`.

## UI layout and rules

Angular 18, NgModule-based, **no lazy loading** — declare new components in
both `app.module.ts` and `app-routing.module.ts`.

```
ui/src/app/
  app.component.*       the shell: header, nav, theme, router outlet
  app-routing.module.ts hash routing (useHash: true) -- not optional
  interceptors/         base-URL rewriting + 401 handling
  error-handler/        global ErrorHandler -> snackbar
  tcl-stubs/            local stand-in for the private @tc-eng component library
  service/              data access, one folder per API surface
  util/                 pure, spec-able logic -- put real logic HERE
  components/           feature pages
```

**Routed pages must own their scroll.** `styles.scss` sets `body { overflow:
hidden }` so the document never scrolls; a page component without
`overflow-y: auto` on its `:host` silently clips everything past the fold.
That works only because the shell is pinned to the viewport —
`app.component`'s `:host` is `display: block; height: 100%` (it is inline by
default, which silently breaks every `height: 100%` below), `.parent` is
`height: 100%`, `.main-content` carries `min-height: 0`, and `router-outlet`
is `display: none` (Angular inserts the routed component as a *sibling*, and
an inline outlet contributes a stray line box). Change any of these and every
page stops scrolling.

**Never hardcode a colour.** Two token layers, both defined in dark/light
pairs in `ui/src/assets/styles/`: `--tcl-*` (the platform's voice — use it for
links, focus, error/warning, base surfaces) and `--app-*` (everything else).
A component needing its own `:host-context(body.dark)` override means a token
is missing; add it. See `DESIGN.md`.

**Put logic in `util/`.** Components are wiring. `util/bar-scale.ts` +
`bar-scale.spec.ts` is the pattern: pure functions, spec'd without TestBed.
The convention is to spec pure modules, not component scaffolds.

**Derived view state is a recomputed field, not a getter.** A getter that
builds a fresh array runs on every change-detection pass and rebuilds every
row.

`ng lint` passes clean and must stay that way. Prettier is enforced through
eslint (`ui/.prettierrc`: single quotes, 4-space indent, printWidth 100).
`tcl-stubs` waives the class-suffix rules; args/vars prefixed `_` may be
unused.

## Design context

Read before designing or restyling anything:

- `PRODUCT.md` — users, brand personality, design principles.
- `DESIGN.md` — the token palette, typography scale, elevation and component
  rules, and the named rules that keep the UI coherent.
