# {Slice Name} — Slice Settings

> **Machine-read switches for this slice.** Every key below is REQUIRED and must carry an
> explicit value. There is **no default and no "absent means false"** — a missing key is a
> broken slice, not a `false` one. `/kerbe:start` asks the question and records the answer
> here; later lifecycle steps read this file and refuse to run against an unanswered key.

```settings
design_required: <true|false>
```

## Keys

### `design_required`

Does this slice's UI come from a design file (via the project's design adapter)?

| Value | Meaning | What it obliges |
|-------|---------|-----------------|
| `true` | Design-driven slice — the design file is the source of truth for its UI | `UI_ELEMENTS.md` MUST exist and MUST carry a populated **Design sources** block (file key, page, per-leaf node ids, `measured=` dates). `/kerbe:plan` refuses to write `PLAN.md` until that block is populated and fresh. |
| `false` | No design leg — backend, CLI, infra, or a UI slice deliberately built without a design | `UI_ELEMENTS.md` is omitted. **State the reason in Notes below** — "no UI at all" and "has UI but no design exists yet" are different situations, and the second usually wants a design question raised, not a silent `false`. |

**Choosing `false` is a decision, not an omission.** It is recorded, dated, and visible in
review. If the honest answer is "there's no design frame *yet*", set `false`, write that in
Notes, and flip it to `true` when the design lands — do not leave it unanswered.

## Notes

| Key | Set on | Reason / context |
|-----|--------|------------------|
| `design_required` | {YYYY-MM-DD} | {why this value — for `false`, say which kind of `false`} |

## Changing a setting

Edit the value, add a dated row to Notes saying what changed and why, and re-run whichever
step the setting gates (`/kerbe:figma` then `/kerbe:plan` for `design_required`). Never
change a value without a Notes row — the point of this file is that the decision is
attributable.
