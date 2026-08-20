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
