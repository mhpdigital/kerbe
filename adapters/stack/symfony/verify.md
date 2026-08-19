# Symfony — what "present and wired" means

Wiring recipes for kerbe:coverage verification on a Symfony stack. Battle-tested on the
reference project. Existence is never enough: every recipe checks that the artifact is
**reachable through the chain that ships it**. Search only under the configured
`stack.code_roots`.

Verdicts: the recipe's checks all hold ⇒ `present`. The artifact exists but a wiring check
fails ⇒ `partial` (name the broken link in evidence). Nothing exists ⇒ `absent`.

## 1. Route wired

A promise that a user can navigate somewhere.

1. Find where the UI offers it: grep templates for `path('route_name')`, `url('route_name')`,
   or a literal `href`.
2. Find the definition: grep controllers for `#[Route(` with that name/path (or the routes
   YAML if the project uses one).
3. Read the controller method body — it must do real work (see recipe 5).

- Linked in a template but no definition ⇒ `partial` — dead link.
- Defined but linked from nowhere the promise's frame reaches ⇒ the *promise* is unmet
  (`partial`), because the designed entry point does not exist. A route that is merely
  unused, with no promise pointing at it, is drop-file material, not a row.

## 2. Template served

A promise of a page or panel. The template file must exist AND some controller `render()`s
it (grep the template path in `src/`). An orphan template is `partial`.

## 3. Stylesheet wired

A promise of styled UI. Three links, all required:

1. **The class the template actually renders** — read the template, note the literal class.
2. A rule on **that exact class** in authored CSS/SCSS (grep the selector).
3. The defining file is reachable from the entry stylesheet via the `@use`/`@import` chain
   (follow it from `app.scss` or the configured entry).

- File exists but nothing imports it ⇒ `partial` — unimported stylesheet.
- Template renders `.card-share` but CSS only defines `.card-email` ⇒ `partial` — class-name
  mismatch. Always grep the rendered class, never the class you expect.

## 4. JS behaviour wired

A promise of client-side behaviour. The entry must appear in `importmap.php` (or the bundler
config) AND be imported by the app entrypoint (`app.js` chain). Auto-start params
(`?do=...`) need a handler that reads them.

## 5. Stub

An empty method body, a `// TODO`, a handler that returns a placeholder, a hardcoded value
where the promise requires computed data ⇒ `partial` — the shell ships, the feature doesn't.

## 6. Entity / field

A promise of stored data. The field exists on the entity class AND a migration creates the
column. Spec'd field missing from either ⇒ `partial` (evidence says which half).

---

**Shared rule (all recipes):** every `present` cites `file:line` for BOTH existence and
wiring in the evidence cell. When a recipe cannot run (directory absent, tool missing), the
row stays `?` with the reason in evidence — never silently `present`, never silently skipped.
