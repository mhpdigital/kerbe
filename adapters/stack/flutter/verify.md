# Flutter — what "present and wired" means

> **Status: drafted, pending validation on a real Flutter app.** These are the Flutter
> equivalents of the Symfony recipes; tighten them against the first real project.

Wiring recipes for kerbe:coverage verification on a Flutter stack. Existence is never
enough: every recipe checks reachability through the chain that ships it. Search only under
the configured `stack.code_roots`.

Verdicts: all checks hold ⇒ `present`. Artifact exists but a wiring check fails ⇒ `partial`
(name the broken link in evidence). Nothing exists ⇒ `absent`.

## 1. Widget wired

A promise of a visible UI element. The widget class (or the inline widget subtree) exists
AND is reachable from the widget tree: imported and constructed by a screen that a
registered route builds. An exported widget nothing constructs is `partial`.

## 2. Route registered

A promise that a user can navigate somewhere. The route path/name appears in the router
table — `GoRouter(routes: [...])`, `MaterialApp.routes`, or the project's `onGenerateRoute`
switch. Planned/spec'd route absent from the table ⇒ `partial` even if the screen widget
exists (screen with no way in). Navigation calls (`context.go`, `pushNamed`) to an
unregistered route ⇒ `partial` — dead link.

## 3. Asset declared

A promise of an image/font/file. The file exists in the repo AND is declared under
`flutter:`/`assets:` (or `fonts:`) in `pubspec.yaml`. Referenced in code but undeclared, or
declared but the file missing ⇒ `partial` (evidence says which half).

## 4. Handler stub

`onPressed: null` where the design promises an action, an empty callback body, a
`// TODO`, a hardcoded value where computed data is promised ⇒ `partial`.

## 5. State wiring

A promise whose screen depends on app state. The provider/bloc/notifier the screen reads is
registered above it in the tree (`MultiProvider`/`BlocProvider`/scope) on the route that
shows it. Screen reads a provider nothing registers ⇒ `partial`.

---

**Shared rule (all recipes):** every `present` cites `file:line` for BOTH existence and
wiring in the evidence cell. When a recipe cannot run (directory absent, tool missing), the
row stays `?` with the reason in evidence — never silently `present`, never silently skipped.
