# Design adapter: figma

The design leg is a **Figma snapshot taken once per extraction** and read from disk by every
pass afterwards. No extraction or verification pass ever calls the Figma API — a live fetch
is a moving input.

## Snapshot (once, before the first extractor)

```bash
python3 <plugin>/skills/coverage/scripts/figma_cache.py \
  --file <kerbe.design.file_key> \
  --out {planning_root}/{slice}/<kerbe.design.cache_dir> \
  [--token-cmd "<kerbe.design.token_cmd>"]
```

Token: `$FIGMA_API_TOKEN` (from `kerbe.design.token_env`), else `--token-cmd`. The script
writes `file.json` (full node tree, render geometry stripped), `manifest.json`, and
`MANIFEST.md`, and **refuses to overwrite an existing snapshot** without `--refetch` —
re-fetching starts a new extraction with a new ledger `SOURCES` pin.

**Commit the snapshot together with the ledger.** It is the evidence base; the diff between
two extractions' snapshots is a precise record of what the design did in between.

If a snapshot already exists in the slice's cache dir, use it and record its
`figma_version` from `manifest.json` as the `design@` pin. Do not refetch unless the user
asks for a new extraction.

## Enumerating promises from the snapshot

Extract from `file.json` **leaf-to-leaf** — this is the #1 blind spot:

- Recurse every frame's full subtree down to leaves. A page-sized frame is **never** a
  promise row by itself: its interactive leaves are the rows.
- Every interactive leaf is its own row: buttons, links, toggles, tabs, pickers, action
  rows, inputs, cards, edit links, preview panels — each with `promised-by: figma:<node-id>`.
- Expand component sets and instances; every variant/state that promises distinct behaviour
  (success/error states of a popup, empty states) is its own row.
- Pure decoration (background shapes, spacers, stray zero-size nodes) is not a promise.

When in doubt whether a leaf is a promise or decoration, make it a row — verification is
cheap, and a wrong row is deleted by the quality pass with its reason recorded.
