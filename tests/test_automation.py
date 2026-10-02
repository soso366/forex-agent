"""Validation locale du workflow GitHub Actions du cycle Manager (.github/workflows/agents-cycle.yml)."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agents-cycle.yml"


class TestAgentsCycleWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WF.read_text(encoding="utf-8")
        cls.wf = yaml.safe_load(cls.text)
        cls.job = cls.wf["jobs"]["cycle"]
        cls.steps = cls.job["steps"]

    def _triggers(self):
        # PyYAML (YAML 1.1) lit la clé `on` comme le booléen True.
        return self.wf.get("on", self.wf.get(True))

    def _step(self, needle):
        for s in self.steps:
            if needle in (s.get("name", "") + s.get("uses", "")):
                return s
        self.fail(f"étape introuvable : {needle}")

    def test_triggers(self):
        t = self._triggers()
        self.assertIn("workflow_dispatch", t)
        self.assertEqual(t["schedule"][0]["cron"].split()[1], "*/6")

    def test_concurrency_permissions_timeout(self):
        self.assertEqual(self.wf["concurrency"]["group"], "agents-cycle")
        self.assertEqual(self.wf["permissions"], {"contents": "write", "issues": "write"})
        self.assertEqual(self.job["timeout-minutes"], 300)

    def test_secret_check_first(self):
        first = self.steps[0]
        self.assertIn("secret", first["name"].lower())
        self.assertIn("ANTHROPIC_API_KEY", first["env"]["HAS_API_KEY"])
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", first["env"]["HAS_OAUTH"])
        self.assertIn("GITHUB_STEP_SUMMARY", first["run"])
        self.assertIn("exit 1", first["run"])

    def test_checkout_work_branch(self):
        s = self._step("actions/checkout")
        self.assertEqual(s["with"]["ref"], "multi-agent-research")
        self.assertEqual(s["with"]["fetch-depth"], 0)

    def test_order_bootstrap_pause_guard_claude(self):
        runs = [s.get("run", "") + s.get("uses", "") for s in self.steps]
        idx = lambda k: next(i for i, r in enumerate(runs) if k in r)
        self.assertLess(idx("bootstrap.sh"), idx("PAUSED"))
        self.assertLess(idx("PAUSED"), idx("orchestrator guard"))
        self.assertLess(idx("orchestrator guard"), idx("claude-code-action"))

    def test_claude_action(self):
        s = self._step("anthropics/claude-code-action@v1")
        w = s["with"]
        self.assertIn("anthropic_api_key", w)
        self.assertIn("claude_code_oauth_token", w)
        self.assertIn("--max-turns", w["claude_args"])
        self.assertIn("Task", w["claude_args"])
        self.assertIn(".claude/agents/manager.md", w["prompt"])
        self.assertIn("main", w["prompt"])

    def test_push_only_work_branch_never_main(self):
        self.assertIn("git push origin HEAD:$WORK_BRANCH", self.text)
        self.assertNotIn("HEAD:main", self.text)
        self.assertNotIn("push origin main", self.text)
        self.assertEqual(self.job["env"]["WORK_BRANCH"], "multi-agent-research")

    def test_lock_released_on_failure(self):
        s = self._step("échec")
        self.assertIn("failure()", s["if"])
        self.assertIn("lock release", s["run"])

    def test_doc_exists(self):
        self.assertTrue((ROOT / "orchestrator" / "AUTOMATION.md").exists())


if __name__ == "__main__":
    unittest.main()
