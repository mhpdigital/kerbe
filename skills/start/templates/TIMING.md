# {Slice Name} — Timing

> Local time (`{kerbe.timezone}`) each lifecycle step was run. Timestamps only — no hours.
> Each kerbe skill stamps its own row when it runs
> (`TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'`). A step run more than once keeps the
> **latest** run time (append re-runs in Notes if it matters).

| Step | Skill | Run at (local) | Notes |
|------|-------|----------------|-------|
| 1. Start | `/kerbe:start` | {YYYY-MM-DD HH:MM} | |
| 2. Design | `/kerbe:figma` | — | |
| 3. Specify | manual | — | |
| 4. Scaffold | `/kerbe:scaffold` | — | |
| 5. Plan impl. | `/kerbe:plan` | — | |
| 6. Implement | `/kerbe:implement` | — | |
| 7. Coverage | `/kerbe:coverage` | — | |
| 8. Verify | `/kerbe:audit` | — | |
