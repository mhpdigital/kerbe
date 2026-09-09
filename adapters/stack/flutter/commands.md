# Flutter — commands

Every command below runs inside `kerbe.stack.exec` when that template is configured
(`{cmd}` is substituted), otherwise directly in the workspace's app root.

| Capability | Command |
|---|---|
| full test suite | `flutter test` |
| single test file | `flutter test <path>` |
| single test | `flutter test --plain-name "<test name>"` |
| static analysis | `flutter analyze` |
| formatter | `dart format --set-exit-if-changed lib test` |
| code generation | `dart run build_runner build --delete-conflicting-outputs` |
| integration tests | `flutter test integration_test` *(needs a device/emulator — say so when unavailable)* |
| build (debug) | `flutter build apk --debug` / `flutter build ios --simulator --no-codesign` |
| dependencies | `flutter pub get` |
| schema validate | **n/a** — no server-side schema in the app. A local store (Drift/Isar) declares its own migration test instead; if the project has none, that is stated, not assumed away. |
| migrate | **n/a** — see above |
| run app | project-owned (`kerbe.workspace.setup_cmds`) |

## Which level a case runs at

`PLAN.md` declares a level per case; this is what each one means here. The rule the planner
applied is **reach for the framework only when the framework is part of the claim** — if the
case would pass with the subject constructed directly and its collaborators stubbed, it is
`unit`.

| Level | Shape | Costs | Use when the claim is |
|---|---|---|---|
| `unit` | plain `test()` over a directly constructed subject | none | pure logic: a mapper, a validator, a state reducer, a use case with fake repositories |
| `kernel` | `test()` with the provider/DI graph or a real local store (Drift/Isar) | container or DB setup | the wiring, an override, a migration, a query |
| `http` | `testWidgets()` with the router and providers mounted | a pumped widget tree | the screen, the route, the guard, what the user actually sees |
| `browser` | `flutter test integration_test` (its own suite) | a device or emulator | end-to-end behaviour on a real device |

`http` is named for the seam it crosses, not for a protocol: in Flutter it is the widget +
router boundary — the level at which a route guard or a rendered screen becomes observable.
The acceptance floor in the plan spec applies unchanged: audience reachability, action chains
and observable state transitions need a case at this level, whatever it costs.

**`kernel`, `http` and `browser` cases need a lane**; `unit` cases need none, which is why
`kerbe:implement` can schedule a unit-only task without one. That is a consequence of the
level, never a reason to choose it.

## Global-effect artifacts (the full-suite trigger)

Flutter has no schema migration, but it has the same **class** of change: one whose effect is
only observable through other components' tests. A diff touching any of these requires the
full `flutter test` run (plus regeneration where relevant), never a scoped one:

- generated model sources and their inputs (`freezed` / `json_serializable` annotated
  classes) — a stale generated file compiles until another test deserializes it
- the app's dependency-injection / provider graph (Riverpod providers, Bloc registration,
  `GetIt` wiring) and any override used by tests
- the router table and route argument types
- `ThemeData` / design-token definitions consumed by golden tests
- shared test harnesses, fakes, and fixture builders
- widely-referenced constants and enums
- **a behavioural change to a notifier/bloc, repository or use-case method with callers
  outside the diff** — grep the callers; more than one consumer means widget and golden
  tests this task never opened can observe the change
- `pubspec.yaml` dependency or asset-declaration changes

**Codegen is part of the diff.** A task that changes an annotated model is not done until
`build_runner` has run and the regenerated files are committed with it — an ungenerated
model is the Flutter shape of "the migration was never applied".
