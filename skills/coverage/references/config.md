# kerbe.yml — the config seam

Shared by every kerbe skill (coverage, start, figma, …). No skill body names a project
path, doc filename, stack probe, or design-tool call — all of that resolves through
`kerbe.yml` at the **target project root**. A missing `kerbe.yml` is a hard stop: tell the
user to create one from `kerbe.yml.example` — never guess defaults.

The file is read by the agent (no YAML library involved); keep it simple and flat.

## Keys

| Key | Type | Required | Meaning |
|---|---|---|---|
| `kerbe.planning_root` | path | yes | Slice folders live at `{planning_root}/{slice}` relative to the project root; the slice registry is `{planning_root}/INDEX.md`. |
| `kerbe.timezone` | IANA tz name | yes for start | Local timezone for `TIMING.md` lifecycle stamps (e.g. `Pacific/Auckland`). |
| `kerbe.legacy_root` | path | optional | Root of a legacy system slices may migrate from. When set AND a legacy counterpart verifiably exists there, `kerbe:start` includes `IMPORT.md`/`CODEMAP.md`; when unset, those docs are omitted. |
| `kerbe.promise_sources.spec_globs` | list of globs | yes | Spec docs inside the slice folder. Glob wide (`*.md`) and **classify by content, not filename** — new slices invent new doc names. Docs are read as the record of WHAT MUST EXIST, never audited for accuracy. |
| `kerbe.promise_sources.plan_glob` | glob | yes | The frozen task list (union of matches). A mutable progress/execution ledger is never the plan — exclude it even when the glob matches it. No match ⇒ `plan: none-yet` rows (valid pre-impl state). |
| `kerbe.design.adapter` | `figma` \| `none` | yes | Which file in `adapters/design/` governs the design leg. `none` ⇒ no design-sourced rows; `spec: n/a` becomes legal; ledger header records `design@n/a`. |
| `kerbe.design.cache_dir` | path | for figma | Snapshot dir relative to the slice folder. Fetched once per extraction, read-only afterwards. |
| `kerbe.design.file_key` | string | for figma | The design file key. Never assume a default. |
| `kerbe.design.token_env` | string | one of the two | Env var holding the API token. Wins over `token_cmd` when both are set. |
| `kerbe.design.token_cmd` | string | one of the two | Shell command that prints the token (e.g. a secrets-manager read). |
| `kerbe.design.checklist` | path | optional | Project's design handoff checklist doc; `kerbe:figma grade` reports against it when set. |
| `kerbe.design.freshness_cmd` | string | optional | Project command checking `@figma` tag coverage/staleness of built UI. When unset, `kerbe:figma` does the check manually and says the tooling is missing. |
| `kerbe.stack.adapter` | `symfony` \| `flutter` | yes | Which `adapters/stack/<name>/verify.md` defines "present and wired". |
| `kerbe.stack.code_roots` | list of paths | yes | Where the slice's implementation lives. Used for mode auto-detect (substantially no slice artifacts under these roots ⇒ pre-impl) and as the search space for verification. May contain `{slice}`, which interpolates the slice id — for projects where each slice's code lives in its own sibling worktree (e.g. `../<repo>-{slice}/src/`). Resolve it before use and verify the resulting path exists (and, when it is a git checkout, that it is on the slice's branch) — a missing or wrong-branch code root is a hard stop, not an `absent` verdict. |

| `kerbe.constraints` | list of strings | optional | Environment rules that hold for **every** dispatch this skill makes (e.g. "do not run any test command — the test database is shared"). The skill appends them verbatim to every extractor/verifier prompt. Constraints state what agents must not do to the environment; they never narrow what is searched. |

## Resolution rules

1. `kerbe.yml` is read from the root of the target project (the repo the slice belongs to).
2. Adapter names resolve to files shipped with the plugin: `adapters/design/{name}.md`,
   `adapters/stack/{name}/verify.md`. An unknown name is a hard stop naming the valid options.
3. Relative paths in the config are relative to the project root, except `design.cache_dir`,
   which is relative to the slice folder.
4. When a recipe cannot run because a configured path is missing, the affected rows stay `?`
   with the reason in evidence — never silently `present`, never silently skipped.
