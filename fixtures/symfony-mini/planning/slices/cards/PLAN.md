# cards — implementation plan

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
