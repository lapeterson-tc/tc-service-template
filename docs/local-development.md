# Local development

The app is designed to run inside ThreatConnect, which makes local iteration
awkward in one specific way: the UI has no idea what URL it will be served
from. Everything below exists to work around that.

## The two loops

### 1. UI-only, against a static build

Fastest way to check layout, theming, routing and empty/error states. No
ThreatConnect, no Python.

```sh
cd ui && npx ng build && cd ..
python3 -m http.server 8137 --directory ui_build/browser
# open http://localhost:8137/#/dashboard
```

API calls fail, so every page renders its error or empty state — which is the
point: those states are real UI that usually goes untested. It also catches
the two bugs that matter most in this app: a broken `<base href>` and a route
that white-pages.

`.claude/launch.json` has this as the `static-build` configuration.

### 2. Full stack, `ng serve` + the Python service

```sh
# terminal 1 -- the service (needs TC credentials in the environment)
python3 run.py

# terminal 2 -- the Angular dev server
cd ui && npx ng serve
# open http://localhost:4200/#/dashboard
```

`ui/src/proxy.conf.json` forwards everything under `/api` from the dev server
(port 4200) to the service on **port 8052**.

## How the UI finds the backend

There is no base-URL constant, environment variable or injection token
anywhere. `HttpInterceptorService`
(`ui/src/app/interceptors/http-interceptor-service/`) rewrites every request
at send time, and it branches on a `//` prefix:

**A relative URL** (`api/example/dashboard`) — the app's own API. The service
root is derived from the `<base>` tag:

```ts
document.getElementsByTagName('base')[0].href
    .replace(/ui\/.*/, '')
    .replace(/(\/v\d+\/).*/, '$1');
```

Both replaces trim SPA route segments back to the TC service prefix ending in
`/v1/`, so the request lands on `/api/services/{userPath}/v1/api/example/...`
no matter which route the user is on. **This is the entire per-instance-prefix
mechanism.**

**A `//`-prefixed URL** (`//api/v3/security/owners`, see `TcService`) — the
ThreatConnect *platform* API, not this app. Deployed, it becomes a same-origin
call straight to the platform. On `localhost` it is rewritten to this app's
`/api/tc/proxy-local` with the original path in an `X-Original-Path` header;
the Python side (`api/endpoint/tc/tc_proxy_local.py`) replays it using the
caller's session. That shim exists purely so `ng serve` can reach the platform
API without CORS or auth gymnastics.

## Authentication

The app authenticates back to ThreatConnect as **the calling user**, via their
session. Every `self.tcex.session.tc` call runs with that user's permissions —
which is why endpoints never need to do their own authorization for TC data,
and why you must never substitute a service identity to "make a query work".

The one boundary the app enforces itself is storage: records are namespaced by
the caller's organization (`api/storage/disk_store.py`), resolved per request
and failing closed.

## Things that will waste your afternoon

**A page that scrolls to nowhere.** `styles.scss` sets `body { overflow:
hidden }` so the document never scrolls; each routed page must set
`overflow-y: auto` on its own `:host`. Without it, content past the fold is
silently clipped with no scrollbar.

**A white page after adding a route.** Add its top-level segment to
`App.spa_route_prefixes` in `app.py` as well as to `app-routing.module.ts`.

**A config flag that reads as `undefined`.** `/api/tc/app-config` serializes
with `by_alias=False`, so multi-word fields arrive **snake_case**
(`schema_version`, not `schemaVersion`). "Correcting" the TypeScript interface
to camelCase silently disables whatever the flag gates.

**An upgrade that appears to do nothing.** `index.html` is not cache-busted;
an open tab keeps the old bundle. Hard-reload first.

**`tcex deps` ignoring your `requirements.txt` edit.** It prefers
`requirements.lock`. `rm -rf deps requirements.lock && tcex deps`.
