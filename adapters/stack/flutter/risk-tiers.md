# Flutter — risk tiers

Classification rules for kerbe:review. Every changed file lands in exactly one tier; the
tier decides how a human reads it.

## Tier 1 — business-logic: read every line

- route guards, auth state listeners, anything reading/writing secure storage
- permission handling (camera, notifications, location) and platform channels
  (`MethodChannel` handlers on both the Dart and native side)
- state machines in notifiers/blocs: transitions, guards, anything deciding what a user
  may do in which state
- repositories/use-cases that **mutate** data or money, sync logic, conflict resolution
- request signing, token refresh, API-client interceptors
- local persistence migrations (Drift/Isar schema changes)

## Tier 2 — glue: read signatures and flow, skip the syntax

- widgets that wire providers to presentation (does it watch the right provider? navigate
  to the right route with the right arguments?)
- router table entries, DI/provider registration
- read-only repositories and simple API-client methods

## Tier 3 — boilerplate: don't read; trust a FULL-suite run

- **generated sources** (`*.g.dart`, `*.freezed.dart`) — with the caveat below
- pure presentation widgets, theme/token definitions, goldens, assets, l10n files,
  `pubspec.lock`

**The exemption is narrower than it looks.** Generated sources are trusted only when the
diff shows them **regenerated together with their annotated inputs** and the evidence is a
full `flutter test` run — a stale generated file compiles until another test deserializes
it (`commands.md` → Global-effect artifacts). A scoped run is not evidence for tier-3
trust on any global-effect file: provider-graph changes, router table, theme tokens under
golden tests, shared fakes.

## Always-tier-1 overrides (checked last, they win)

- anything touching secure storage, auth tokens, or payment
- both sides of any platform channel
- any persistence schema/migration change
