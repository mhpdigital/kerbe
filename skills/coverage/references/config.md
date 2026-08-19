# kerbe.yml — the config seam

The skill body names no project path, doc filename, stack probe, or design-tool call. All of
that resolves through `kerbe.yml` at the **target project root**. A missing `kerbe.yml` is a
hard stop: tell the user to create one from `kerbe.yml.example` — never guess defaults.

The file is read by the agent (no YAML library involved); keep it simple and flat.

## Keys

| Key | Type | Required | Meaning |
|---|---|---|---|
| `kerbe.planning_root` | path | yes | Slice folders live at `{planning_root}/{slice}` relative to the project root. |
| `kerbe.promise_sources.spec_globs` | list of globs | yes | Spec docs inside the slice folder. Glob wide (`*.md`) and **classify by content, not filename** — new slices invent new doc names. Docs are read as the record of WHAT MUST EXIST, never audited for accuracy. |
| `kerbe.promise_sources.plan_glob` | glob | yes | The frozen task list (union of matches). A mutable progress/execution ledger is never the plan — exclude it even when the glob matches it. No match ⇒ `plan: none-yet` rows (valid pre-impl state). |
| `kerbe.design.adapter` | `figma` \| `none` | yes | Which file in `adapters/design/` governs the design leg. `none` ⇒ no design-sourced rows; `spec: n/a` becomes legal; ledger header records `design@n/a`. |
| `kerbe.design.cache_dir` | path | for figma | Snapshot dir relative to the slice folder. Fetched once per extraction, read-only afterwards. |
| `kerbe.design.file_key` | string | for figma | The design file key. Never assume a default. |
| `kerbe.design.token_env` | string | one of the two | Env var holding the API token. Wins over `token_cmd` when both are set. |
| `kerbe.design.token_cmd` | string | one of the two | Shell command that prints the token (e.g. a secrets-manager read). |
| `kerbe.stack.adapter` | `symfony` \| `flutter` | yes | Which `adapters/stack/<name>/verify.md` defines "present and wired". |
| `kerbe.stack.code_roots` | list of paths | yes | Where the slice's implementation lives. Used for mode auto-detect (substantially no slice artifacts under these roots ⇒ pre-impl) and as the search space for verification. |

## Resolution rules

1. `kerbe.yml` is read from the root of the target project (the repo the slice belongs to).
2. Adapter names resolve to files shipped with the plugin: `adapters/design/{name}.md`,
   `adapters/stack/{name}/verify.md`. An unknown name is a hard stop naming the valid options.
3. Relative paths in the config are relative to the project root, except `design.cache_dir`,
   which is relative to the slice folder.
4. When a recipe cannot run because a configured path is missing, the affected rows stay `?`
   with the reason in evidence — never silently `present`, never silently skipped.
