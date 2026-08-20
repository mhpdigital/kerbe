# {Slice Name} — UI Element Catalogue

## Design sources

> REQUIRED when `SETTINGS.md` has `design_required: true`. `/kerbe:figma` fills this in and
> keeps `measured=` current; `/kerbe:plan` reads it and STOPS if it is unfilled or stale.
> One row per screen — pin the **node id**, never just the frame name, because a file
> usually carries several stale iterations of the same frame.

- **Design file:** `{fileKey}` · **Page:** `{page name}`

| Screen / frame | Node id | Measured (YYYY-MM-DD) |
|----------------|---------|-----------------------|
| | | |

## Colour Palette Reference

_Copy relevant colours from the project's master palette._

---

## 1. {Page/Screen Name} (node `{node-id}`)

> **Leaf-level rule — one row per interactive leaf.** Every button, link, toggle, tab,
> picker, action row, input, badge, and state variant inside this frame is its own row with
> its own node id. A page-sized frame is never one row: completeness review builds its
> promise ledger at exactly this granularity, and a leaf missing here is a leaf nobody
> plans, builds, or verifies.

| # | Element (leaf) | Node id | Type | States | Colour / measurements | Notes |
|---|----------------|---------|------|--------|-----------------------|-------|
| 1 | | | | | | |

**Implementation notes:**
- ...

_Review code: {random 4-digit number}_

---
