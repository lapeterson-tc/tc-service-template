# Architecture

## What an "API Service App" is

ThreatConnect runs this app as a **persistent micro-service**, not a one-shot
job. It stays alive and answers HTTP requests that the platform proxies to it
under a per-app path:

```
https://<tc-instance>/api/services/{userPath}/v1/...
```

`{userPath}` is the **API Path** an administrator chose when creating the
service. The app never knows its own absolute URL — every design decision
about routing and asset paths follows from that one fact.

The platform forwards each request to the app over a WSGI callback, carrying
the calling user's session. The app then authenticates back to ThreatConnect
as that user, so everything it reads or writes runs with their permissions.

## How a request flows

1. **`run.py`** — the entrypoint (`programMain` in `install.json`). Inserts
   `deps/` at the front of `sys.path`, builds `TcEx()`, constructs `App`,
   registers the service event callback, and loops forever.
2. **`app.py` (`App`)** — the concrete app. Subclasses `ApiServiceFalcon`.
   Declares the route table, the middleware, the injected objects, the
   preflight checks, and the SPA route prefixes.
3. **`core/app/api_service_falcon.py`** — wires routes + middleware into a
   `FalconApp`, registers the OpenAPI spec, and **hard-exits at boot if
   `ui_build/browser` is missing**.
4. **`core/api/falcon_app.py` (`FalconApp`)** — a `falcon.App` subclass. Serves
   the Angular build at `/`, installs the routing sinks, a JSON media handler
   that can serialize datetimes, and an error handler that writes unhandled
   exceptions to the **app log** (Falcon's default writes them to stderr,
   where they never reach the log file and a 500 looks silent).
5. **`App.api_event_callback`** normalizes the path and calls the Falcon WSGI
   app.

## Middleware (order matters)

Assembled in `ApiServiceFalcon._middleware`: the app's own `middleware`
property runs first, then the base class appends `TcExMiddleware`,
`ErrorMiddleware`, `ValidationMiddleware`.

- **`InjectableMiddleware`** — sets each `kwarg` from `app.py:App.middleware`
  onto the resource instance **by name**. This is how endpoints get
  `self.app_config`, `self.bedrock`, and anything else you add.
- **`TcExMiddleware`** — sets `self.tcex`, `self.log`, `self.args`.
- **`ErrorMiddleware`**, **`ValidationMiddleware`**.

Because of this, endpoint classes declare bare class-level annotations and
have **no `__init__`** — the framework populates them per request. The
contract lives in `api/endpoint/endpoint_base.py` (app-level) and
`core/api/endpoint/endpoint_base.py` (framework). Keep the app-level
annotations in sync with `App.middleware`, or an endpoint will read an
attribute that nothing sets.

Two consequences of resources being **singletons**:

- Never store per-request state on `self`.
- Anything you cache on the class is shared **across users**. Cache
  instance-wide metadata only; per-user data must be computed per request.

## Routing and the SPA

The Angular app uses **hash routing** (`useHash: true`) with
`<base href="./">`. This is not a preference:

The app lives under `/api/services/{userPath}/v1/`. With path-based routing, a
reload of `/v1/dashboard/42` makes the browser resolve the page's *relative*
asset URLs against `/v1/dashboard/`, the static route's `index.html` fallback
answers those requests with HTML, and the app never boots — a white page with
no error. With the route in the fragment, the document URL always stays at the
service root.

`FalconApp` installs three kinds of sink (falcon matches sinks **before**
static routes, which is what lets them win over the `index.html` fallback):

| Sink | Purpose |
|---|---|
| `/ui` | legacy: bounce back to the SPA root |
| each entry in `App.spa_route_prefixes` | 308 a path-style deep link to its hash form: `/v1/dashboard/42` → `/v1/#/dashboard/42` |
| each entry in `App.spa_entry_redirects` | external entry point: `/open_item?id=7` → `./#/items/new?id=7` |

Redirects are **relative** because the app cannot know its absolute prefix.
Entry redirects put the query **inside** the fragment, and read the raw
`query_string` rather than `req.params` so falcon's `auto_parse_qs_csv` cannot
split comma-containing values.

**Add every new top-level client route to `spa_route_prefixes`.** Forgetting
is the single most common way to ship a broken deep link.

## Storage

Persisted data lives as plain JSON files:

```
{tc_out_path}/app-data/{org_key}/{data_type}/{encoded_rid}.json
```

- `org_key` is resolved from the **calling user's** session
  (`/v2/owners/mine` → `org-{id}`) and is the **only access-control boundary**
  this storage has. Resolution **fails closed**: an unresolvable org returns
  `None` and never falls back to a shared or default namespace.
- Writes are atomic (temp file + `os.replace`), so a reader sees either the
  complete new file or the previous one.
- Record ids are percent-encoded by a hand-rolled encoder that makes `.`,
  `..`, dotfiles and `/` structurally impossible in a filename.

Always go through `safe_datastore(tcex, log, data_type)`; never construct a
`DiskStore` directly. It returns `None` on failure, and callers must degrade:
**defaults on read, an explicit 503 on write.** A write that silently
no-ops is worse than one that fails loudly.

Register every `data_type` in `api/storage/registry.DATA_TYPES` — that list
drives backup/restore, and an unregistered type is silently absent from every
export.

Two accepted limitations, both consequences of using container disk: storage
is not shared between instances of the same service, and it is not backed up
with the platform. Hence `/api/storage/export` and `/api/storage/import`.

## Conventions

**Never 500.** A failed upstream call returns HTTP 200 with a populated
`error` field and whatever partial data exists. The UI can render a degraded
panel; it cannot render a stack trace. Reserve real error statuses for the
caller's own mistakes (400) and refused writes (503).

**Query ThreatConnect as the caller.** Use `self.tcex.session.tc` (raw
session) or `self.tcex.api.tc.v3.*` (SDK objects). Don't mix the two in one
code path — the raw session exists for response shapes the SDK doesn't
expose.

**Build TQL literals with `tql_quote`.** Escaping only the double quote is not
enough: a trailing backslash escapes the escape and breaks out of the literal.
Prefer the SDK's `filter.*(TqlOperator.EQ, value)` where a v3 collection
object is in hand.

**Log both ways.** `debug_print(...)` for container stdout, `log.info(...)`
for the durable app log. The `[APP-DEBUG]` prefix makes them greppable.

## Adding a feature

1. Create `api/endpoint/<feature>/` with an endpoint class extending
   `EndpointBase`. Define spectree request/response models and decorate the
   handler with `@spec.validate(..., tags=[...])`.
2. Add a `Tag` in `api/spec_tags.py` (once per feature area).
3. Register the route in `app.py:App.routes`.
4. If it persists anything, add the `data_type` to
   `api/storage/registry.DATA_TYPES`.
5. For a UI page: add the component, declare it in **both** `app.module.ts`
   and `app-routing.module.ts`, and add its top-level path segment to
   `App.spa_route_prefixes`.
6. Put any real logic in a pure module (`util/` in the UI, module-level
   functions in Python) so it can be unit-tested without a browser or tcex.

The `example` feature exists as a worked reference for all of this. Delete it
once your own feature has replaced it.
