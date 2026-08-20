# Flutter — impact recipes

What `kerbe:bug` checks per **artifact kind** before a fix is written. Same purpose as the
Symfony set: find every downstream consumer in one pass. Search only under the workspace's
app root.

## data model (freezed / json_serializable model, field)

| Check | How | Why it bites |
|---|---|---|
| generated sources | `*.freezed.dart` / `*.g.dart` regenerated and committed with the change | the app compiles against stale generated code until a test deserializes it |
| API contract | does the backend actually send the field, with that name and type? | a required field missing from the payload throws at parse time, far from the fix |
| nullability | can the field be absent — first launch, offline cache, older API version, partial payload? | a non-nullable field is a crash on the first old response |
| copyWith / equality | manual `copyWith`, `==`, `hashCode` if not generated | a field left out of `copyWith` silently reverts on every update |
| local persistence | Drift/Isar/Hive schema + its migration, or a versioned JSON cache | an old cached row parsed by the new model crashes on launch |
| state holders | grep providers / blocs / notifiers reading the model | state that never re-reads the field renders stale forever |
| widgets | grep the field name under the UI layer | a widget reading a removed field fails to compile — or worse, defaults silently |
| route arguments | does any route pass this model or field as an argument? | typed route args break at navigation, not at build |
| serialization back out | request bodies built from the model | a renamed field is accepted by the client and rejected by the server |
| fixtures & goldens | fixture builders, fakes, golden test data | goldens go stale the moment layout-affecting fields change |

## permission boundary

Route guards, auth-state listeners, and platform permissions (camera, notifications,
storage) plus secure-storage reads. A screen reachable only after a guard must be tested
from **both** sides of the guard.

## state transition

For a bug about "the user can do X in state S": find the guard in the notifier/bloc and
check that some real path produces S in the shape the guard accepts — the emitted state,
not merely a method with the right name.

## schema migration

**n/a** for the app itself (the schema is server-side). When the project ships a local
store, its migration and a migration test are part of the fix; when it does not, say so
rather than skipping the row silently.

## Required test paths for any model change

| Test | Covers |
|---|---|
| parse a payload with the field | round-trips through fromJson/toJson |
| parse a payload without it | absent/null path does not throw |
| widget renders with it populated | the UI actually shows it |
| widget renders with it null/empty | no layout crash, no "null" text |
| cached old-shape record read | persistence migration or version bump handles it |
