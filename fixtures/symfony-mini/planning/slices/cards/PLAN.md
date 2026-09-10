# cards — implementation plan

Dependency graph (the scheduler's input — `kerbe:implement` runs everything the graph leaves
free at the same time, up to `workspace.lanes`):

| Task | Depends | Owns | Case levels |
|---|---|---|---|
| T1 | none | `templates/card/index.html.twig`, `src/Controller/CardController.php` | http |
| T2 | T1 | `templates/card/detail.html.twig` | http |
| T3 | T2 | `templates/card/detail.html.twig` | http |
| T4 | T2 | `templates/card/detail.html.twig` | http |
| T5 | T1 | `assets/styles/_hover.scss`, `assets/styles/app.scss` | unit |
| T6 | T3 | `src/Controller/CardController.php` | kernel |

**T3 and T5 are the free pair** — T3 depends on T2, T5 on T1, neither on the other, and they
own disjoint files. A schedule that runs them one after the other has ignored the graph.

**T4 is the trap.** The graph leaves T3 and T4 both free once T2 lands, so a scheduler reading
only `Depends` dispatches them together — onto the same template. `detail.html.twig` already
carries T4's toolbar link, so the two would collide. The file-ownership contract must hold one
back, and that hold is a Ruling: an ordering constraint the graph did not capture. A schedule
that runs T3 and T4 concurrently is wrong, and one that records no Ruling for holding T4 has
made the right move for no stated reason.

T5 is lane-free — every case is `unit`. In *this* fixture's config that changes nothing:
`workspace.lanes` and `workspace.worktree_setup_cmds` are both unset, so everything runs in
lane 0 and the run must say so rather than promise concurrency the project cannot host.

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
