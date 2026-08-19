# Promise ledger — cards
LEDGER_VERSION: 1
MODE: audit
STATUS: FROZEN
SOURCES: docs@fixture · design@fixture-1
EXTRACTION: converged (passes=3)

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
| P-001 | Card grid on index page | figma:1:3 | doc:UI_ELEMENTS.md#cards-ui-elements | task:T1 index page | present | templates/card/index.html.twig:5 .card-grid; _card.scss:1 rule; app.scss:1 imports card; src/Controller/CardController.php:12 route card_index |
| P-002 | Card detail page with description | req:REQ-CARD-002 | origin | task:T2 detail page | present | templates/card/detail.html.twig:9 .card-description; src/Controller/CardController.php:24 route card_detail |
| P-003 | Filter chips row on index | figma:1:4 | GAP | ? | ? | no spec doc mentions filter chips; UI_ELEMENTS.md has no entry for figma:1:4 |
| P-004 | Download action row on detail | figma:2:2 | req:REQ-CARD-002 | task:T3 Download row | absent | no template renders a download row; detail.html.twig has no download markup |
| P-005 | Export as PDF from detail toolbar | figma:2:3 | req:REQ-CARD-003 | task:T4 Export toolbar link | partial | templates/card/detail.html.twig:6 links /cards/export; no route defines that path in src/ — dead link |
| P-006 | Share-by-email popup on detail | figma:2:4 | req:REQ-CARD-004 | GAP | absent | no plan task covers the share popup; no template renders share markup |
| P-007 | Card hover elevation style | req:REQ-CARD-005 | origin | task:T5 hover style | partial | index.html.twig:6 renders .card-hover; _hover.scss:1 defines it; app.scss imports only card — unimported stylesheet |
| P-008 | Email receipt after download | req:REQ-CARD-006 | origin | task:T6 email receipt | partial | src/Controller/CardController.php:31 emailReceipt() body is a TODO stub with no route |
| P-009 | Index route reachable at /cards | doc:REQUIREMENTS.md#req-card-001 | req:REQ-CARD-001 | task:T1 index page | present | src/Controller/CardController.php:12 Route /cards name card_index |
