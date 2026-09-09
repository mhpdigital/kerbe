# cards — implementation plan

Dependency graph (the scheduler's input — `kerbe:implement` runs everything the graph leaves
free at the same time, up to `workspace.lanes`):

| Task | Depends | Case levels |
|---|---|---|
| T1 | none | http |
| T2 | T1 | http |
| T3 | T2 | http |
| T4 | T2 | http |
| T5 | T1 | unit |
| T6 | T3 | kernel |

T3 and T4 are the diamond: both consume T2, neither consumes the other, and they own
different files. A schedule that runs them one after the other has ignored the graph. T5 is
lane-free — every case is `unit` — so it needs a worktree and dependency install, not a lane.

- [x] **T1 index page** — route `card_index` at `/cards`, controller `CardController::index`,
  template `card/index.html.twig` rendering the card grid per `figma:1:3`.
- [x] **T2 detail page** — route `card_detail` at `/cards/{id}`, controller
  `CardController::detail`, template `card/detail.html.twig` with the description block.
- [ ] **T3 Download row** — render the download action row (`figma:2:2`) on the detail page:
  primary download button, file-size hint.
- [ ] **T4 Export toolbar link** — "Export as PDF" (`figma:2:3`) in the detail toolbar,
  linking the export route.
- [ ] **T5 hover style** — `.card-hover` elevation shadow per REQ-CARD-005 in the card
  stylesheet, imported by the app manifest.
- [ ] **T6 email receipt** — send the receipt email after a completed download
  (REQ-CARD-006), `CardController::emailReceipt`.
