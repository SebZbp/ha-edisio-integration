# Domain Docs

How the engineering skills should consume this repo's domain documentation.

## Before exploring, read these
- **`CONTEXT.md`** at the repo root
- **`docs/adr/`**: ADRs that touch the area you're about to work in
- **`docs/specs/`**: specs for the feature at hand

If any of these don't exist, **proceed silently**. `/domain-modeling` creates them lazily.

## Layout
Single-context repo: `CONTEXT.md` + `docs/adr/` + `docs/specs/` at the root.

## Use the glossary's vocabulary
Use terms as defined in `CONTEXT.md`; don't drift to synonyms it avoids.

## Flag ADR conflicts
If your output contradicts an existing ADR, surface it explicitly rather than silently overriding.
