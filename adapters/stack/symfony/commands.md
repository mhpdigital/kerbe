# Symfony — commands

Every command below runs inside `kerbe.stack.exec` when that template is configured
(`{cmd}` is substituted), otherwise directly in the workspace's app root. Nothing here
names a container, a project, or a path outside the app root — that belongs in the config.

| Capability | Command |
|---|---|
| full test suite | `php vendor/bin/phpunit` |
| single test file | `php vendor/bin/phpunit <path>` |
| single test | `php vendor/bin/phpunit --filter <TestName>` |
| static analysis | `php vendor/bin/phpstan analyse` *(when the project configures it)* |
| template lint | `php bin/console lint:twig templates` |
| container lint | `php bin/console lint:container` |
| schema validate | `php bin/console doctrine:schema:validate` |
| migrate (dev) | `php bin/console doctrine:migrations:migrate --no-interaction` |
| migrate (test) | `php bin/console doctrine:migrations:migrate --no-interaction --env=test` |
| generate migration | `php bin/console make:migration` |
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

## Repair, never bypass

When the migration runner refuses because of an unrelated pre-existing failure, **repair the
runner** — e.g. record an already-applied version so the chain advances — and say what you
repaired. Never document a per-command bypass: a workaround written down is a defect
entrenched in every future session, and the agent that reads it stops short of the full run.
