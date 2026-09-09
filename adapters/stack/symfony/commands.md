# Symfony — commands

Every command below runs inside `kerbe.stack.exec` when that template is configured
(`{cmd}` is substituted), otherwise directly in the workspace's app root. Nothing here
names a container, a project, or a path outside the app root — that belongs in the config.

| Capability | Command |
|---|---|
| full test suite | `php vendor/bin/phpunit` — but see **Which suite is the gate** below when the project defines more than one |
| single test file | `php vendor/bin/phpunit <path>` |
| single test | `php vendor/bin/phpunit --filter <TestName>` |
| static analysis | `php vendor/bin/phpstan analyse` *(when the project configures it)* |
| template lint | `php bin/console lint:twig templates` |
| container lint | `php bin/console lint:container` |
| schema validate | `php bin/console doctrine:schema:validate` |
| migrate (dev) | `php bin/console doctrine:migrations:migrate --no-interaction` |
| migrate (test) | `php bin/console doctrine:migrations:migrate --no-interaction --env=test` |
| generate migration | `php bin/console make:migration` |
| migrate one version up/down (round-trip evidence for a migration's `down()`) | `php bin/console doctrine:migrations:execute '<FQN\Version>' --up|--down --no-interaction` |
| ad-hoc SQL for evidence (idempotence counts, seed-row checks) | `php bin/console dbal:run-sql "<sql>"` — evidence queries only, never schema changes |
| clear cache | `php bin/console cache:clear` |
| asset entries | `php bin/console importmap:install` *(when the project uses AssetMapper)* |
| run app | project-owned (`kerbe.workspace.setup_cmds`) — the adapter does not start containers |

Test database: the test kernel uses its own database. **A migration applied to dev is not
applied to test.** Both commands, every time the schema moves.

## Global-effect artifacts (the full-suite trigger)

A diff touching any of these has effects that only *other* components' tests can observe,
so a scoped test run cannot evidence "no regressions" — `kerbe:implement`'s per-task gate
and `kerbe:bug`'s validation step both require the full suite plus schema validation here:

- anything under `src/Entity/` (mapping attributes, new/renamed/removed columns, relations)
- anything under `migrations/`
- `config/packages/doctrine.yaml` and any ORM mapping config
- service wiring: `config/services.yaml`, compiler passes, event subscribers, listeners
- `config/packages/security.yaml`, firewalls, access control, voters
- shared test fixtures, base test cases, the test kernel
- widely-referenced constants and enums
- **a behavioural change to a service or repository method that has callers outside the
  diff.** Grep the callers before deciding: one consumer and the scoped run covers it; more
  than one and the effect surfaces in files this task never opened. This row is the
  behavioural sibling of the artifact rows above — a class list alone lets a shared service
  through on per-file evidence.

## Which suite is the gate

When `phpunit.dist.xml` defines several testsuites, a bare `php vendor/bin/phpunit` runs
**all** of them, including any browser/e2e suite the project deliberately keeps out of the
everyday run. Read the config before quoting a command:

- the **gate** is the suite that runs everywhere without external prerequisites, named
  explicitly: `php vendor/bin/phpunit --testsuite '<name>'`
- a browser/e2e suite is a **separate** claim with its own prerequisites (a working driver,
  seeded reference data). It is reported separately, never folded into the no-regression
  number, and never silently dropped either

Getting this wrong reads as a regression in both directions: run everything and a missing
ChromeDriver looks like broken code; run the default and an e2e failure never surfaces at
all. Name the suite, and say which one the evidence covers.

## Which level a case runs at

`PLAN.md` declares a level per case; this is what each one means here. The rule the planner
applied is **boot the kernel only when the kernel is part of the claim** — if the case would
pass with the subject constructed directly and its collaborators stubbed, it is `unit`.

| Level | Base class | Costs | Use when the claim is |
|---|---|---|---|
| `unit` | `extends TestCase` | no kernel, no database | pure logic: a guard, a transition allow-list, a normaliser, a calculation |
| `kernel` | `extends KernelTestCase` | kernel boot + database | the wiring, the mapping, the SQL, a computed read that only the database produces |
| `http` | `extends WebTestCase` | kernel boot + request | the response, the security configuration, the route, the rendered template |
| `browser` | Panther (its own suite) | a real browser | client-side behaviour — a control mounting, a dropdown opening |

Two mistakes this table exists to prevent:

- **Booting the kernel to reach a service.** `self::bootKernel()` followed by
  `getContainer()->get(SomeService::class)` in order to assert pure logic is a `unit` case
  wearing a `kernel` harness. Construct the service and stub its collaborators instead. On a
  real slice this pattern cost ~60× per test, on tests whose subject needed none of it.
- **Reaching for `WebTestCase` because it can assert anything.** It can assert status codes,
  HTML *and* database rows, which makes it the path of least resistance for a planner who has
  not decided what the seam is. Decide the seam.

**`kernel` and `http` cases need a lane** (a container and a test database); `unit` cases need
neither, which is why `kerbe:implement` can schedule a unit-only task without one. That is a
scheduling consequence of the level, never a reason to choose it — see the acceptance floor
in the plan spec for the cases that must stay at `http` whatever it costs.

## Repair, never bypass

When the migration runner refuses because of an unrelated pre-existing failure, **repair the
runner** — e.g. record an already-applied version so the chain advances — and say what you
repaired. Never document a per-command bypass: a workaround written down is a defect
entrenched in every future session, and the agent that reads it stops short of the full run.
