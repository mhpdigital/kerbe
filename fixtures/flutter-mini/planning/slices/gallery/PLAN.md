# gallery — implementation plan

Dependency graph (the scheduler's input — `kerbe:implement` runs everything the graph leaves
free at the same time, up to `workspace.lanes`):

| Task | Depends | Case levels |
|---|---|---|
| T1 | none | http |
| T2 | T1 | unit, http |
| T3 | T1 | http |

T2 and T3 are the diamond's free pair: both consume T1, neither consumes the other. A
schedule that runs them one after the other has ignored the graph.

- [x] **T1 gallery screen** — `GalleryScreen` with the item grid, route `/gallery` in the
  router table.
- [ ] **T2 favorite button** — favorite toggle on each grid item (REQ-GAL-002).
- [ ] **T3 detail screen** — `GalleryDetailScreen`, route `/gallery/detail` in the router
  table, opened from a grid item tap.
