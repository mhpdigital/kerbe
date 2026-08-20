# Symfony — impact recipes

What `kerbe:bug` checks per **artifact kind** before a fix is written. Each row is a grep or
a read with a stated reason; the point is one commit that fixes everything, not three
commits chasing the same root cause. Search only under the workspace's app root.

## data model (Doctrine entity / property)

| Check | How | Why it bites |
|---|---|---|
| mirror entities | does another entity hold the same data (revision/draft twin, a shared trait)? | a property on one and not its twin 500s every page using the twin |
| copy methods | grep `copy`, `->set` clusters in services that move data between the twins | a new property outside the shared trait needs an explicit copy line |
| nullability | can the value be null on **any** path — new draft, empty form, publish, import, CLI? | a non-nullable setter TypeErrors the first time a path produces null |
| migration exists | grep the column name across `migrations/` | never map to a column a migration is dropping |
| column-name match | compare the mapping's `name:` against the column after **all** migrations | mapping and DB disagree only on a fresh deploy, never locally |
| form types | grep the property in `src/Form/` | a form rendering a property that no longer exists crashes on load |
| templates | grep `entity.propertyName` under `templates/` | Twig on a missing property crashes at render |
| serialization | grep API responses / normalizers / `jsonSerialize` | a dropped field breaks clients silently |
| test fixtures | do fixture helpers and factories set the new field? | fixtures that skip a required field fail everything that uses them |
| cache/computed | any cached projection, ES/Meilisearch document, or denormalized column carrying it? | stale projections outlive the fix |

## permission boundary

`#[IsGranted]` attributes, `security.yaml` access control, voters, and the **audience** of
every route the fixed flow links to. A CTA that points at a route the promised audience
cannot reach is a defect of the same class as a missing route — follow the link one hop and
check who may enter.

## state transition

For a bug about "the user can do X in state S": find the guard, and check the **producing**
side too — that some real path actually creates state S in the shape the guard accepts. A
cancel that writes a flag while leaving the status the guard tests unchanged is a deadlock
that no unit test of either half will show.

## schema migration

1. grep the column across `migrations/` — no second migration may touch it
2. uncommitted migration ⇒ edit it in place; committed ⇒ write a new one
3. apply to **dev and test** (`commands.md`), then `doctrine:schema:validate`
4. re-run the **full** suite — a mapping change is a global-effect artifact

## Required test paths for any data-model change

| Test | Covers |
|---|---|
| edit with the field populated | renders in the form, round-trips through save |
| edit with the field null/empty | the null path does not crash form or controller |
| publish/copy with it populated | copies twin → live correctly |
| publish/copy with it null | null propagates without a TypeError |
| create fresh | default works, no required-field crash |

Keep two fixture builders — one fully populated, one minimal — and run both through every
workflow path.
