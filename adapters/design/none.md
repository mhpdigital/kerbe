# Design adapter: none

The slice has **no design leg by configuration** (`kerbe.design.adapter: none`). This is a
recorded decision, not a gap.

- No design-sourced promise rows exist; promises originate in the spec docs and the plan
  (`spec: origin` / `promised-by: req:… | doc:… | plan:…`).
- `spec: n/a` is legal **only** under this adapter — and only for rows whose promise would
  otherwise need a design origin. Do not use it as "didn't check".
- The ledger header records the pin as `design@n/a`.
- If, during extraction, evidence of an actual design surfaces (a design link in a spec doc,
  design-tool node ids in the docs), stop and tell the user: the config says `none` but the
  slice appears to have a design. That contradiction is theirs to resolve — do not silently
  switch adapters.
