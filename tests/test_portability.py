"""Portability gates that hold for every kerbe skill and adapter.

These are the invariants the ROADMAP calls load-bearing: skill bodies name no
harness mechanism, and every stack/executor adapter declares the full capability
set (supported or explicitly n/a) so an asymmetry between stacks is stated
rather than silently missing.
"""
import pathlib
import re
import unittest
import json

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
STACKS = REPO / "adapters" / "stack"
EXECUTORS = REPO / "adapters" / "executor"
PLUGIN_VERSION = "0.9.0"

# Mechanism names that belong in adapters/, never in a skill body.
HARNESS_TOKENS = re.compile(r"Agent\(|isolation:|spawn_agent|TaskCreate|add-dir|additionalDirectories")

STACK_FILES = ("verify.md", "commands.md", "impact.md", "risk-tiers.md")
REQUIRED_COMMANDS = (
    "full test suite",
    "single test file",
    "static analysis",
    "schema validate",
    "migrate",
    "run app",
)
REQUIRED_KINDS = (
    "data model",
    "permission boundary",
    "state transition",
    "schema migration",
)


def skill_bodies():
    return sorted(SKILLS.glob("*/**/*.md"))


class HarnessNeutralityTest(unittest.TestCase):
    def test_no_harness_tool_names_in_skills(self):
        offenders = []
        for path in skill_bodies():
            for n, line in enumerate(path.read_text().splitlines(), start=1):
                if HARNESS_TOKENS.search(line):
                    offenders.append("%s:%d: %s" % (path.relative_to(REPO), n, line.strip()))
        self.assertEqual(offenders, [], "mechanism belongs in adapters/executor/: " + "\n".join(offenders))

    def test_executor_adapters_exist(self):
        names = {p.stem for p in EXECUTORS.glob("*.md")}
        self.assertIn("claude", names)
        self.assertIn("inline", names)

    def test_executor_adapters_declare_capabilities_and_limits(self):
        for path in EXECUTORS.glob("*.md"):
            text = path.read_text()
            self.assertIn("## Capabilities", text, path.name)
            self.assertTrue(re.search(r"^## Limits", text, re.M),
                            path.name + " must state its limits")


class StackAdapterParityTest(unittest.TestCase):
    def stacks(self):
        return sorted(p for p in STACKS.iterdir() if p.is_dir())

    def test_every_stack_ships_the_full_file_set(self):
        for stack in self.stacks():
            for name in STACK_FILES:
                self.assertTrue((stack / name).is_file(),
                                "%s is missing %s" % (stack.name, name))

    def test_commands_declare_every_capability(self):
        for stack in self.stacks():
            text = (stack / "commands.md").read_text().lower()
            for cap in REQUIRED_COMMANDS:
                self.assertIn(cap, text,
                              "%s/commands.md must declare %r (a command or n/a)"
                              % (stack.name, cap))

    def test_commands_declare_global_effect_artifacts(self):
        for stack in self.stacks():
            text = (stack / "commands.md").read_text()
            self.assertIn("Global-effect artifacts", text,
                          "%s/commands.md must list what forces a full-suite run"
                          % stack.name)

    def test_impact_covers_every_artifact_kind(self):
        for stack in self.stacks():
            text = (stack / "impact.md").read_text().lower()
            for kind in REQUIRED_KINDS:
                self.assertIn(kind, text,
                              "%s/impact.md must cover %r (recipe or n/a)"
                              % (stack.name, kind))

    def test_risk_tiers_cover_all_three_tiers(self):
        for stack in self.stacks():
            text = (stack / "risk-tiers.md").read_text()
            for tier in ("Tier 1", "Tier 2", "Tier 3"):
                self.assertIn(tier, text,
                              "%s/risk-tiers.md must define %s" % (stack.name, tier))
            self.assertIn("full", (stack / "risk-tiers.md").read_text().lower(),
                          "%s tier-3 exemption must be bound to a full-suite run"
                          % stack.name)

    def test_unsupported_capabilities_are_declared_not_omitted(self):
        """A stack that cannot do something says n/a in the file that owns it."""
        flutter = (STACKS / "flutter" / "commands.md").read_text().lower()
        self.assertIn("n/a", flutter, "flutter must declare its schema asymmetry")


class SkillConfigSeamTest(unittest.TestCase):
    """No skill body may hardcode a project path the config seam owns."""

    FORBIDDEN = (
        re.compile(r"~/projects/\w"),
        re.compile(r"\bplanning/slices/"),
        re.compile(r"origin/review/main"),
    )

    def test_no_hardcoded_project_paths(self):
        offenders = []
        for path in skill_bodies():
            for n, line in enumerate(path.read_text().splitlines(), start=1):
                for pat in self.FORBIDDEN:
                    if pat.search(line):
                        offenders.append("%s:%d: %s" % (path.relative_to(REPO), n, line.strip()))
        self.assertEqual(offenders, [],
                         "resolve through kerbe.yml instead:\n" + "\n".join(offenders))


class PluginPackagingTest(unittest.TestCase):
    def test_portable_and_host_manifests_share_identity_and_version(self):
        manifests = [
            json.loads((REPO / "plugin.json").read_text()),
            json.loads((REPO / ".codex-plugin" / "plugin.json").read_text()),
            json.loads((REPO / ".claude-plugin" / "plugin.json").read_text()),
        ]
        self.assertEqual({manifest["name"] for manifest in manifests}, {"kerbe"})
        self.assertEqual({manifest["version"] for manifest in manifests}, {PLUGIN_VERSION})

    def test_every_skill_has_matching_codex_invocation_policy(self):
        for skill_dir in sorted(path for path in SKILLS.iterdir() if path.is_dir()):
            skill = (skill_dir / "SKILL.md").read_text()
            metadata_path = skill_dir / "agents" / "openai.yaml"
            self.assertTrue(metadata_path.is_file(), metadata_path)
            metadata = metadata_path.read_text()
            self.assertIn("display_name:", metadata, metadata_path)
            self.assertIn("short_description:", metadata, metadata_path)
            self.assertNotIn("disable-model-invocation: true", skill, skill_dir)
            self.assertIn("allow_implicit_invocation: false", metadata, metadata_path)

    def test_codex_marketplace_publishes_the_root_plugin(self):
        marketplace = json.loads(
            (REPO / ".agents" / "plugins" / "marketplace.json").read_text()
        )
        entry = marketplace["plugins"][0]
        self.assertEqual(marketplace["name"], "kerbe-marketplace")
        self.assertEqual(entry["name"], "kerbe")
        self.assertEqual(entry["source"]["source"], "url")
        self.assertEqual(entry["source"]["url"], "https://github.com/mhpdigital/kerbe.git")
        self.assertEqual(entry["source"]["ref"], "main")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")


if __name__ == "__main__":
    unittest.main()
