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
| `kerbe.editor_cmd` | command template | optional | Per-finding open command for `kerbe:review` rows — `{line}` and `{file}` (absolute) are substituted (e.g. `phpstorm --line {line} {file}`; works equally for `code -g {file}:{line}`). Unset ⇒ review rows carry plain `file:line` references, which stay clickable in most terminals. |
| `kerbe.legacy_root` | path | optional | Root of a legacy system slices may migrate from. When set AND a legacy counterpart verifiably exists there, `kerbe:start` includes `IMPORT.md`/`CODEMAP.md`; when unset, those docs are omitted. |
| `kerbe.promise_sources.spec_globs` | list of globs | yes | Spec docs inside the slice folder. Glob wide (`*.md`) and **classify by content, not filename** — new slices invent new doc names. Docs are read as the record of WHAT MUST EXIST, never audited for accuracy. |
| `kerbe.promise_sources.plan_glob` | glob | yes | The frozen task list (union of matches). A mutable progress/execution ledger is never the plan — exclude it even when the glob matches it. No match ⇒ `plan: none-yet` rows (valid pre-impl state). |
| `kerbe.design.adapter` | `figma` \| `claude-design` \| `none` | yes | Which file in `adapters/design/` governs the design leg. `none` ⇒ no design-sourced rows; `spec: n/a` becomes legal; ledger header records `design@n/a`. `claude-design` ⇒ artboards (`*.dc.html`) committed under the slice folder are the source; the pin is their git commit. |
| `kerbe.design.dir` | path | for claude-design | Directory of `*.dc.html` artboards, relative to the slice folder (default `design`). Node ids are element `id` attributes; `dc_extract.py --lint` enforces them. |
| `kerbe.design.cache_dir` | path | for figma | Snapshot dir relative to the slice folder. Fetched once per extraction, read-only afterwards. |
| `kerbe.design.file_key` | string | for figma | The design file key. Never assume a default. |
| `kerbe.design.token_env` | string | one of the two | Env var holding the API token. Wins over `token_cmd` when both are set. |
| `kerbe.design.token_cmd` | string | one of the two | Shell command that prints the token (e.g. a secrets-manager read). |
| `kerbe.design.checklist` | path | optional | Project's design handoff checklist doc; `kerbe:figma grade` reports against it when set. |
| `kerbe.design.freshness_cmd` | string | optional | Project command checking `@figma` tag coverage/staleness of built UI. When unset, `kerbe:figma` does the check manually and says the tooling is missing. |
| `kerbe.stack.adapter` | `symfony` \| `flutter` | yes | Which `adapters/stack/<name>/verify.md` defines "present and wired". |
| `kerbe.stack.code_roots` | list of paths | yes | Where the slice's implementation lives. Used for mode auto-detect (substantially no slice artifacts under these roots ⇒ pre-impl) and as the search space for verification. May contain `{slice}`, which interpolates the slice id — for projects where each slice's code lives in its own sibling worktree (e.g. `../<repo>-{slice}/src/`). Resolve it before use and verify the resulting path exists (and, when it is a git checkout, that it is on the slice's branch) — a missing or wrong-branch code root is a hard stop, not an `absent` verdict. |
| `kerbe.stack.exec` | command template | optional | Wrapper for every command an adapter's `commands.md` defines — `{cmd}` is substituted, and `{slice}` interpolates like it does in `code_roots` (e.g. a per-slice container exec). Unset ⇒ commands run directly in the workspace. |
| `kerbe.workspace.root` | path | for implement/bug | Parent directory for slice workspaces; the workspace is `{root}/{prefix}{slice}`. **Unset ⇒ no worktree is created**: the resolved `stack.code_roots` entry is the workspace, and the skill never runs `git worktree add`. |
| `kerbe.workspace.prefix` | string | with `root` | Workspace directory prefix (keeps sibling slice checkouts distinguishable). |
| `kerbe.workspace.branch_prefix` | string | for implement/bug | Feature-branch prefix; the slice branch is `{branch_prefix}{slice}`. |
| `kerbe.workspace.review_prefix` | string | optional | Integration-branch prefix. A `{review_prefix}{slice}` workspace **supersedes** the slice one — it has already absorbed it. |
| `kerbe.workspace.base_branch` | branch | for implement | Branch a fresh slice branch is cut from when neither workspace exists. A base named in `PLAN.md`'s Global Constraints wins over this. |
| `kerbe.workspace.planning_branch` | branch | optional | Set **only** when the planning root lives in the code repo on another branch — the slice folder is then materialised into the workspace from it. Omit when planning is its own repository (nothing to materialise). |
| `kerbe.workspace.progress_file` | filename | optional | Live tracker written at the workspace root (default `claude-progress.md`). Never a hidden dotfolder — see the rule in `kerbe:implement`. |
| `kerbe.workspace.setup_cmds` | list of strings | optional | Commands run **once**, after a workspace is created, to stand its environment up (containers, database, seed data). Never re-run on an existing workspace without saying so. |
| `kerbe.executor.adapter` | `claude` \| `inline` | for implement | Which file in `adapters/executor/` supplies the dispatch mechanism. Skill bodies state worker *intent* only; the adapter owns the tool call. |
| `kerbe.executor.routing` | map | optional | Task-class overrides, `task-class: executor@effort` (e.g. `test-authoring: claude@deep`). A route records task class + executor + effort — never a bare vendor name. |
| `kerbe.constraints` | list of strings | optional | Environment rules that hold for **every** skill and every dispatch it makes (e.g. "never run a destructive database command"). Appended verbatim to every worker prompt. Constraints state what agents must not do to the environment; they never narrow what is searched. |
| `kerbe.constraints_by_skill` | map skill → list | optional | Constraints that hold for **one** skill only. A review-only rule ("do not modify application code") belongs here under `coverage`, never in the global list — `implement` and `bug` exist to change code, and a global rule forbidding it either blocks them or gets silently ignored, which is worse. |

## Resolution rules

1. `kerbe.yml` is read from the root of the target project (the repo the slice belongs to).
2. Adapter names resolve to files shipped with the plugin: `adapters/design/{name}.md`,
   `adapters/stack/{name}/{verify,commands,impact}.md`, `adapters/executor/{name}.md`. An
   unknown name is a hard stop naming the valid options. A capability an adapter declares
   `n/a` is **skipped and said aloud**, never silently substituted with another stack's.
3. Relative paths in the config are relative to the project root, except `design.cache_dir`,
   which is relative to the slice folder.
4. When a recipe cannot run because a configured path is missing, the affected rows stay `?`
   with the reason in evidence — never silently `present`, never silently skipped.
