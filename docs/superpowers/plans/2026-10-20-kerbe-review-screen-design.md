# rwalk review screen — screen design

Companion to `2026-10-20-kerbe-review-screen.md` (Task 6). This file is the screen mockup
in text form. Behaviour, routes and recording rules are in
`docs/specs/2026-10-20-review-screen.md`. Where this file and the spec differ, the spec wins.

## Layout

One window, two panes. Reading order in the main column is top to bottom.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ cards · QR-1 · 4 items · 3 open · tier 3 accepted 20 Oct · reviewed at a41c9e2   │
│                                              [toast]   [Finish walk · commit]   │
├───────────────┬──────────────────────────────────────────────────────────────────┤
│ BUSINESS LOGIC│ WHY THIS ROW MATTERS              WHAT THE CODE DOES             │
│ B1 CardContr… │ The ownership check decides       detail() loads the card        │
│   [verified]  │ who can see a card.               through findVisibleFor() …     │
│ B2 CardRepo…  │ source line (spec ref or row kind)                               │
│   [open]      ├──────────────────────────────────────────────────────────────────┤
│ GLUE          │ src/Controller/CardController.php   L20–41   [Open in editor  e] │
│ G1 index rou… ├──────────────────────────────────────────────────────────────────┤
│   [open]      │ old new ± code (wrapped, never scrolls sideways)                 │
│ FLAGS         │  19  19    {                                                     │
│ F1 Medium: d… │  20     -      $card = $this->cards->find($id);                  │
│   [open]      │      20 +      $card = $this->cards->findVisibleFor(…);          │
│               ├──────────────────────────────────────────────────────────────────┤
│ Boilerplate:  │ DISCUSSION                                                       │
│ 1 file, tier 3│  You: What if the card's deck was deleted?                       │
│ accepted …    │  Agent: … Options:                                               │
│               │   O0  Keep it …                                       [Pick]     │
│               │   O1  Return 410 Gone …                               [Pick]     │
│               │   O2  Owner gets a restore page …                     [Pick] ◀   │
│               │  [ Ask about this row …                          ] [Ask]         │
│               ├──────────────────────────────────────────────────────────────────┤
│               │ VERDICT  [Verified a] [Queue fix f] [Raise bug b] [Defer d]      │
│               │          [Skip s]                         j k next / previous    │
│               │ ┌ Queue fix for B1 ───────────────────────────────────────────┐  │
│               │ │ Chosen option: O2 …                                         │  │
│               │ │ Decision detail [multi-line textarea, 6 rows]               │  │
│               │ │ Proves it       [textarea, 2 rows]                          │  │
│               │ │ Written to REVIEW.md as: <live preview>                     │  │
│               │ │ [Queue fix]                                                 │  │
│               │ └─────────────────────────────────────────────────────────────┘  │
└───────────────┴──────────────────────────────────────────────────────────────────┘
```

| Region | Content | Rules |
|---|---|---|
| Top bar | slice, QR id, item count, open count, tier-3 state, `Reviewed at` sha; toast; Finish | Toast confirms each write (`B1 → REVIEW.md`). |
| Rail (≈230 px) | rows grouped Business logic / Glue / Flags; id, title (one line, ellipsis), status pill; tier-3 summary at the bottom | Click or Enter selects. Current row highlighted. |
| Explanation | "Why this row matters" (QR Why cell, larger type) and "What the code does" (pre-read) side by side; a source line under both | Pre-read shows a pending state until ready. |
| File header | path (wraps), line range, Open in editor `e` | Button tooltip: runs only an allow-listed editor command. |
| Diff | four columns: old no., new no., sign, code | `white-space: pre-wrap; overflow-wrap: anywhere`, hanging indent. Added/deleted backgrounds; lines with `in: true` get a left accent bar and highlight. Hunk headers muted. |
| Discussion | caption: the agent reads the repo and does not change files; message list; ask box | Options render as cards `O#  text  [Pick]`. The picked option is highlighted. Elapsed time shows while a question runs (D11). |
| Verdict | five buttons with key hints, `j k` hint | Verified, bug, defer and skip write (skip writes nothing) and move to the next open row. |
| Fix panel | chosen option or "No option picked. Write the ruling in full below."; Decision detail; Proves it; preview; Queue fix | Opens on `f` or on Pick. Focus goes to Decision detail. Preview updates on every keystroke. |

Status pills: `open` (muted), `verified` (green), `fix queued` (amber), `bug pending` (red),
`deferred` (purple), `skipped` (muted). Tier colours on row ids: B red, G amber, F purple.

Before the B rows, while tier 3 is unanswered, the main column shows the tier-3 panel:
the Boilerplate file list, **Accept**, and **Challenge in the terminal** (D10).

## Keyboard

| Key | Action |
|---|---|
| `j` / `k` | next / previous row |
| `a` | Verified |
| `f` | Queue fix (opens the panel) |
| `b` | Raise bug |
| `d` | Defer |
| `s` | Skip |
| `e` | Open in editor |

Keys are ignored while focus is in a text field.

## Fixture data

The mockup used these four rows from the public `cards` slice. Reuse them as the manual-walk
fixture in Task 6.

| Id | Title | File · lines | Why | What the code does |
|---|---|---|---|---|
| B1 | `CardController::detail()` | `src/Controller/CardController.php` L20–41 | The ownership check decides who can see a card. | `detail()` loads the card through `CardRepository::findVisibleFor($user)`, not `find($id)`. A card the user cannot see comes back as null, which returns a 404, so the existence of other users' cards does not leak. |
| B2 | `CardRepository::findVisibleFor()` | `src/Repository/CardRepository.php` L14–30 | This query filter is the only place ownership is enforced. | Builds the query on card JOIN deck WHERE `deck.owner = :user AND deck.deletedAt IS NULL`. No row is returned without the owner predicate. |
| G1 | index route renders template | `src/Controller/CardController.php` L15 | Check that the index route renders the right template. | `index()` passes `findAllVisibleFor($user)` to `card/index.html.twig`. Flow only, no branching. |
| F1 | Medium: draft cards readable by id | `src/Repository/CardRepository.php` L18 | `findVisibleFor()` does not filter on `c.status`, so the owner can open a draft card by URL before it is published. | Whether this is a bug depends on the spec. `DECISIONS.md` does not say whether owners may preview drafts. |

## Worked example: a queued fix with a detailed decision

On B1 the human asks: *What if the card's deck was deleted?*

The agent answers:

> `findVisibleFor()` joins deck with `deck.deletedAt IS NULL` (CardRepository L19), so the
> card comes back as null and everyone gets a 404, the owner included.
> `CardControllerTest::testDeletedDeckIs404` covers this. Options:
>
> - **O0** Keep it. Everyone gets a 404 for a card in a deleted deck.
> - **O1** Return 410 Gone instead of 404 for cards in a deleted deck.
> - **O2** Non-owners keep the 404. The owner gets a page saying the deck was deleted, with
>   a Restore deck button.
> - **O3** Hard-delete the deck's cards when the deck is deleted, so the question goes away.

The human clicks **Pick** on O2. The fix panel opens with O2 as the chosen option and an
empty detail (D9). The human writes:

**Decision detail**

```
Owner only, and only inside the 30-day soft-delete window. After 30 days the owner gets the 404 like everyone else.
Restore puts the deck back with all its cards. It does not restore cards deleted one by one before the deck was deleted.
No change to findVisibleFor(). Add a separate findOwnedInDeletedDeck() so the ownership filter stays as it is.
```

**Proves it**

```
Owner GET /cards/{id} in a deck deleted 10 days ago returns 200 with the restore page. The same request at 31 days returns 404. A non-owner gets 404 at any age.
```

The preview shows the row exactly as `qr.write_verdict` will write it (syntax per
`skills/rwalk/references/recording.md` and the spec's Recording table):

```
| B1 | ~~`src/Controller/CardController.php` · `detail()` (L20–41)~~ **FIX QUEUED 2026-10-20** | ~~The ownership check decides who can see a card.~~ Ruled: O2: Non-owners keep the 404. The owner gets a page saying the deck was deleted, with a Restore deck button.<br>Owner only, and only inside the 30-day soft-delete window. After 30 days the owner gets the 404 like everyone else.<br>Restore puts the deck back with all its cards. It does not restore cards deleted one by one before the deck was deleted.<br>No change to findVisibleFor(). Add a separate findOwnedInDeletedDeck() so the ownership filter stays as it is. · proves it: Owner GET /cards/{id} in a deck deleted 10 days ago returns 200 with the restore page. The same request at 31 days returns 404. A non-owner gets 404 at any age. | ~~open~~ |
```

The exchange is appended to `REVIEW-discussion.md` under `## QR-1/B1 — CardController::detail()`.
After Finish, the fix worker for B1 receives the Ruled text as its brief.

## After Finish

The page shows "Walk handed back to the terminal" and makes no further requests. The
terminal reports the tally, for example `1 verified · 1 fix queued · 1 bug pending · 1 open`.

## Theme

Light and dark through `prefers-color-scheme`. Colour tokens from the mockup:

| Token | Light | Dark |
|---|---|---|
| background | `#f4f6f8` | `#0e1218` |
| surface | `#ffffff` | `#151b24` |
| ink | `#18202c` | `#e5e9ef` |
| muted | `#5a6474` | `#98a2b2` |
| line | `#dce1e8` | `#263040` |
| accent | `#0f6e66` | `#3cc7b8` |
| B / bug | `#b42318` | `#f97066` |
| G / fix | `#a15c07` | `#f5b546` |
| F / defer | `#6941c6` | `#a991fb` |
| verified | `#1f7a3d` | `#5bd18a` |
| diff add | `#e6f5ea` | `#10301d` |
| diff del | `#fcebea` | `#3a1618` |
| in-range highlight | `#fff4cf` | `#3a3214` |

System fonts only (`system-ui` and `ui-monospace`). The page loads nothing from the network.
