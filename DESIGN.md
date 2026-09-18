---
name: TC Service Template
description: Base visual system for a ThreatConnect API Service App
colors:
  accent: "#3e89f9"
  accent-night: "#6aa6ff"
  severity-low: "#34c759"
  severity-medium: "#f5a623"
  severity-high: "#e53935"
  severity-critical: "#b71c1c"
  night-canvas: "#141a2a"
  night-surface: "#1e2738"
  night-border: "#2d3548"
  night-ink: "#d0d5e0"
  slate-muted: "#657086"
  day-canvas: "#f5f6f8"
  day-surface: "#ffffff"
  day-border: "#d8dce3"
  day-ink: "#1b2132"
typography:
  title:
    fontFamily: "inherit (ThreatConnect platform font)"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "inherit (ThreatConnect platform font)"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "inherit (ThreatConnect platform font)"
    fontSize: "11px"
    fontWeight: 700
    letterSpacing: "0.04em"
  data:
    fontFamily: "monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  xs: "2px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  pill: "10px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
components:
  button:
    backgroundColor: "{colors.day-surface}"
    textColor: "{colors.day-ink}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
  card:
    backgroundColor: "{colors.day-surface}"
    rounded: "{rounded.lg}"
    padding: "14px"
  pill:
    rounded: "{rounded.pill}"
    padding: "1px 7px"
---

# Design System

## 1. Overview

**North star: a well-kept instrument panel.** Quiet, flat, legible at a
glance; every mark on it means something. Nothing decorative competes with the
data.

### Two token layers

| Layer | Where | Authority |
|---|---|---|
| `--tcl-*` | `ui/src/assets/styles/tcl-variables.css` | The **host's voice**. Links, focus rings, error/warning, base surfaces, the spacing scale. |
| `--app-*` | `ui/src/assets/styles/app-tokens.css` | Everything the platform does not style. |

Inside ThreatConnect the `--tcl-*` values properly belong to the platform's
own global stylesheet. That stylesheet is not reachable from this app's
service path, so the app ships a close approximation — but treat the tokens as
borrowed, not owned.

**Every colour token is defined twice**: once in `:root` (light) and once in
`body.dark`. `app.component.ts` is the single writer of that class.

## 2. Named rules

These exist because each one has a failure mode that is easy to reintroduce.

### The Host's Voice Rule
Never hardcode what a `--tcl-*` token provides — `--tcl-textLink`,
`--tcl-error`, `--tcl-borderFocus`, `--tcl-base01`. An app that hand-picks its
own link blue stops matching the platform the moment the platform changes.

### The No Raw Hex Rule
A component stylesheet contains **zero** hex colours. If you reach for one, a
token is missing: add it to `app-tokens.css` in both blocks. The corollary:
**a component should never need its own `:host-context(body.dark)` colour
override.** One appearing is the symptom, not the fix.

### The Severity Stays In Its Lane Rule
The four-step ramp (`--app-sev-low/med/high/crit`) is for **scores, status and
ratings only** — never decoration, never encoding a category. Categories use
`--app-cat-*`, which is ordered so the first few stay distinguishable in both
themes and for the common colour-vision deficiencies.

Severity as *text* needs more contrast than severity as *fill*, which is why
`--app-sev-crit-text` exists separately. Text sitting **on** a severity fill
uses `--app-on-severity`, which is deliberately the same in both themes — the
fills don't flip, so the text on them must not either.

### The One Gesture Rule
The uppercase tracked 11px label (`.app-label`) is the **only** styled type
treatment in the app. Using it everywhere a section needs a name is what keeps
the UI quiet; adding a second decorative treatment is what makes it loud.

### The Machine Text Rule
Anything copy-pasteable — an indicator, a hash, an id, a timestamp — is
monospace (`.app-mono`). Anything with digits that align in a column gets
`tabular-nums` (`.app-num`), so values don't jitter as they update.

### The Floaters-Only Rule
Shadows (`--app-shadow-float`) are for surfaces that genuinely float: drawers,
modals, menus, tooltips. Everything else is flat with a 1px
`--app-border` hairline. A page of shadowed cards reads as noise.

## 3. Typography

Family is **inherited from the platform**; the app ships no typefaces.

| Role | Size | Weight | Use |
|---|---|---|---|
| title | 15px | 600 | panel and section headings |
| body | 13px | 400 | default |
| label | 11px | 700, 0.04em, uppercase | the one gesture |
| data | 12px | 400, monospace | machine text |

Page titles (20px/600) are the one exception, and there is one per page.

## 4. Spacing, radius, elevation

Spacing steps 4 / 8 / 12 / 16 / 20. Radius xs 2 / sm 4 / md 6 / lg 8 / pill
10 — cards and panels use `lg`, controls use `sm`, pills use `pill`.
Elevation: see the Floaters-Only Rule.

## 5. Components

**Buttons** — flat, 1px border, `--app-radius-sm`, 6px/10px padding, hover
darkens the border rather than the fill. A primary action may take
`--app-accent` as a fill with `--app-on-accent` text; there is at most one per
view.

**Pills** — `--app-radius-pill`, tight padding, `tabular-nums` when numeric.
A severity pill takes its fill from the ramp.

**Cards and panels** — `--app-surface` on `--app-canvas`, 1px border,
`--app-radius-lg`. A panel has a header row separated by a hairline.

**Inputs and selects** — same border and radius as buttons; focus shows
`--tcl-borderFocus` at 2px with `outline-offset`.

**Tables** — `table-layout: fixed`, hairline row separators, `.app-label`
column headers, hover row tint from `--tcl-hoverMain`. Truncate with an
ellipsis and a `title`; never wrap a data cell.

**Charts** — grid lines from `--app-grid`, series from `--app-cat-*`,
magnitudes from the accent. Any non-zero value must remain visible: a bar
below the minimum visible width reads as "no data" rather than "very small",
which is a different fact (see `util/bar-scale.ts`).

**Navigation** — plain text items, muted until active, accent underline flush
to the header's bottom edge. Weight stays constant across states so the active
item doesn't shift its neighbours. Nav is not a toolbar; actions belong in the
header's action cluster.

### Your signature component

Every app has one surface that is the reason it exists — a graph canvas, a
timeline, a workbench. Document it here: what it is, what it must never do,
and which tokens are reserved for it.

## 6. Do's and don'ts

**Do**

- Reach for a `--tcl-*` token before an `--app-*` one, and an `--app-*` one
  before a literal.
- Give every state a real design: loading, empty, partial, error.
- Distinguish "nothing matched" from "the lookup failed", in words.
- Keep the layout working at phone width with a 16px side gutter and no
  horizontal page scroll.
- Respect `prefers-reduced-motion`.

**Don't**

- Add a colour without adding its dark counterpart in the same commit.
- Use the severity ramp to make something look important.
- Introduce a second font, a second label treatment, or a gradient.
- Animate anything the user has to wait for.
- Put a control far from the thing it acts on.
