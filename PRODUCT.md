# Product

> Replace the specifics below with your app's. The structure — who it's for,
> what it refuses to be, and the principles that settle arguments — is what
> makes this file worth keeping.

## Register: product

An analyst tool embedded inside the ThreatConnect platform. Not a marketing
site, not a consumer app, not a standalone product with its own brand.

## Users

Security and threat-intelligence analysts working inside a ThreatConnect
Threat Intelligence Platform. They arrive already signed in, already holding a
question, and already fluent in the platform's vocabulary. They are not here
to explore the app; they are here to answer something and move on.

Two things follow from that:

- **They did not choose this tool.** It was installed for them. It has to earn
  its place in the first ten seconds.
- **They are interrupted constantly.** Any state that is expensive to rebuild
  after a tab switch is a design failure.

## Product purpose

State, in one sentence, the question this app answers that the platform
cannot answer on its own. If that sentence needs an "and", the app is doing
two things.

## Brand personality

**Modern, approachable, clear.** It should look like it belongs to the
platform that hosts it — not like a plugin bolted on, and not like a rival
design language competing for attention.

## Anti-references

- **Hacker-dark SOC aesthetic.** Neon on black, terminal fonts as decoration,
  animated threat maps. Reads as theatre to people who do this work.
- **Dense enterprise legacy.** Grey-on-grey toolbars, twelve-column forms,
  nested tabs. Volume of controls is not capability.
- **Consumer dashboard gloss.** Big friendly gradients and celebratory empty
  states. The subject matter is someone's bad day.

## Design principles

1. **Feel native to the host.** When the platform provides a colour, a focus
   ring, or a spacing step, use it. The app should be indistinguishable from
   its surroundings at a glance and distinguishable by what it *does*.

2. **Verdict before evidence.** Lead with the answer — a count, a status, a
   score — and let the supporting rows sit underneath. An analyst scanning for
   "is this bad?" should not have to read a table to find out.

3. **Reflow, don't shrink.** At narrower widths, drop the least important
   column or stack the row. Never scale type down to fit; unreadable data is
   worse than absent data.

4. **Missing data is information.** "No results in this window" and "the
   lookup failed" are different states and must look different. Never render
   an empty container and let the user guess which one happened. This is why
   the backend never 500s — a soft error carries a message the UI can show.

5. **Actions where the eyes are.** Put a control next to the thing it acts on.
   A toolbar at the top of a long page is a control the user has to go find.

## Accessibility and inclusion

No formal WCAG gate, best-effort in practice:

- Every interactive element is reachable and operable by keyboard, with a
  visible focus ring (`--tcl-borderFocus`).
- Colour is never the only carrier of meaning — a severity tier also shows its
  number, a status also shows its word.
- Respect `prefers-reduced-motion`; no animation is load-bearing.
- Text contrast targets 4.5:1 against its own surface in **both** themes,
  which is why every colour token is defined twice.
