# Promise ledger — gallery
LEDGER_VERSION: 1
MODE: audit
STATUS: FROZEN
SOURCES: docs@fixture · design@n/a
EXTRACTION: converged (passes=3)

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
| P-001 | Gallery grid screen | req:REQ-GAL-001 | origin | task:T1 gallery screen | present | lib/screens/gallery_screen.dart:3 GalleryScreen; lib/router.dart:7 route /gallery builds it |
| P-002 | Gallery route at /gallery | req:REQ-GAL-001 | origin | task:T1 gallery screen | present | lib/router.dart:7 GoRoute path /gallery |
| P-003 | Favorite button on each item | req:REQ-GAL-002 | origin | task:T2 favorite button | absent | no favorite widget anywhere under lib/ |
| P-004 | Detail screen at /gallery/detail | plan:T3 detail screen | origin | task:T3 detail screen | partial | lib/screens/gallery_detail_screen.dart:6 GalleryDetailScreen exists but lib/router.dart registers no /gallery/detail route and no grid item onTap opens it — screen with no way in |
| P-005 | Logo in the app bar from images/logo.png | req:REQ-GAL-003 | origin | GAP | partial | no plan task covers the logo; lib/screens/gallery_screen.dart:10 references Image.asset images/logo.png but pubspec.yaml declares no assets and the file does not exist — referenced but undeclared |
