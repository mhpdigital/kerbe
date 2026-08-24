# Symfony — risk tiers

Classification rules for kerbe:review. Every changed file lands in exactly one tier; the
tier decides how a human reads it. Extracted from a reference project's review practice;
generalise further with care — the rules encode where bugs were actually found.

## Tier 1 — business-logic: read every line

Files that decide who can do what, what data changes, and what rules are enforced. A bug
here is a security hole or a broken business rule.

- security: voters, `UserChecker`, anything under `src/Security/`, firewall/access-control
  config
- authorization at the data layer: **any repository overriding or bypassing the base query
  builder** — custom `createQueryBuilder()` overrides, unrestricted/unscoped query methods
  (projects on `mhpdigital/cross-tenant-security-bundle`: everything touching
  `CrossTenantRepository` or `createUnrestrictedQueryBuilder()` is always tier 1)
- state transitions and workflow rules (status fields, guards, lifecycle services)
- data-mutation services (copy/publish/import, money, anything with side effects)
- form types that **enforce rules**: custom validation logic, security-relevant options,
  `getBlockPrefix(): ''` (a signal the form bypasses normal field namespacing)
- event listeners/subscribers that change state
- payment and external-money API integration

## Tier 2 — glue: read signatures and flow, skip the syntax

Check: does this controller call the right service? Route, role, template wired correctly?
Does the data flow make sense? Do not read loops, formatting, or template-variable
assembly. ~30 seconds per file.

- controllers, service wiring, DI configuration, route definitions
- form types that are pure field-to-entity mapping
- commands/crons that only orchestrate services reviewed as tier 1

## Tier 3 — boilerplate: don't read; trust a FULL-suite run

- entities (getters/setters), migrations, Twig templates, YAML/config, CSS, JS with no
  business logic, test fixtures, translations

**The exemption is narrower than it looks.** "Trust the tests" is only sound when *the
tests* means the whole suite. When the diff touches a **global-effect artifact**
(`commands.md` → Global-effect artifacts: entities, migrations, ORM config, service
wiring, security config, shared fixtures…) and the evidence shows only a scoped run, the
tier-3 skip does not apply — read the migration/mapping, because a scoped green run is
exactly how an unapplied migration ships. One mapped column that never reached the test
database has turned a green report into 46 failures.

## Always-tier-1 overrides (checked last, they win)

- any diff line matching `createQueryBuilder(` or an unrestricted query method
- anything under `src/Security/`
- anything touching authentication, session, or password/reset flows
