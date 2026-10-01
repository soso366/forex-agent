"""Orchestrateur multi-agents : étapes, verrous, pause, garde-fous (dans un dossier temporaire)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from orchestrator import core

REAL = Path(core.__file__).resolve().parents[1]


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "orchestrator").mkdir()
        shutil.copytree(REAL / "orchestrator" / "templates", self.tmp / "orchestrator" / "templates")
        shutil.copy(REAL / "orchestrator" / "control.yaml", self.tmp / "orchestrator" / "control.yaml")
        for d in ("experiments", "memory", "reports", "forex_agent/risk", "config"):
            (self.tmp / d).mkdir(parents=True)
        (self.tmp / "forex_agent/risk/manager.py").write_text("RISK = 1\n")
        (self.tmp / "config/settings.yaml").write_text("risk: 1\n")
        (self.tmp / "memory/REJECTED_HYPOTHESES.md").write_text("| Opening range breakout Londres | négatif |\n")
        self.saved = {k: getattr(core, k) for k in ("ROOT", "ORCH", "EXP", "MEM", "REPORTS", "STATE", "CONTROL", "PROTECTED")}
        core.ROOT, core.ORCH = self.tmp, self.tmp / "orchestrator"
        core.EXP, core.MEM, core.REPORTS = self.tmp / "experiments", self.tmp / "memory", self.tmp / "reports"
        core.STATE, core.CONTROL = core.ORCH / "state.json", core.ORCH / "control.yaml"
        core.PROTECTED = core.ORCH / "protected.json"
        core.lock_protected("test")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(core, k, v)
        shutil.rmtree(self.tmp)

    def test_stage_machine_requires_files(self):
        d = core.new_experiment("Test hypothèse")
        eid = d.name.split("-")[0]
        with self.assertRaises(SystemExit):           # pas de precritique.md → pas de passage
            core.advance(eid, "PRECRITIQUED", "critic")
        core.template(eid, "precritique.md")
        core.advance(eid, "PRECRITIQUED", "critic")
        with self.assertRaises(SystemExit):           # pas de retour en arrière
            core.advance(eid, "PROPOSED", "manager")

    def test_protocol_lock_detects_changes(self):
        d = core.new_experiment("Verrou")
        eid = d.name.split("-")[0]
        core.template(eid, "precritique.md")
        core.advance(eid, "PRECRITIQUED", "critic")
        core.template(eid, "protocol.md")
        core.advance(eid, "PROTOCOL_LOCKED", "quant")
        self.assertEqual(core.guard(), [])
        (d / "protocol.md").write_text("critères changés après coup")
        self.assertTrue(any("protocole modifié" in i for i in core.guard()))

    def test_guard_protected_files(self):
        (self.tmp / "forex_agent/risk/manager.py").write_text("RISK = 2\n")
        self.assertTrue(any("forex_agent/risk/manager.py" in i for i in core.guard()))

    def test_pause_stops_plan(self):
        core.set_mode("PAUSED")
        self.assertEqual(core.plan()["tasks"], [])
        core.set_mode("RUNNING")
        self.assertTrue(core.plan()["tasks"])

    def test_reject_before_test_and_caps(self):
        d = core.new_experiment("A")
        eid = d.name.split("-")[0]
        core.template(eid, "precritique.md")
        s = core.advance(eid, "PRECRITIQUED", "critic", verdict="REJECT")
        self.assertEqual((s["stage"], s["verdict"]), ("DECIDED", "REJECT"))
        core.new_experiment("B"), core.new_experiment("C"), core.new_experiment("D")
        with self.assertRaises(SystemExit):           # max 3 expériences actives
            core.new_experiment("E")

    def test_dupcheck(self):
        self.assertTrue(core.dupcheck(["opening", "range"]))
        self.assertFalse(core.dupcheck(["zzz-introuvable"]))

    def test_cycle_report_format(self):
        core.save_state({"cycle": 0, "cycle_open": False, "history": []})
        core.open_cycle()
        txt = core.report("RAS", "aucune", "aucun", "E001", close=True)
        for k in ("CYCLE #1", "Hypothèses testées", "Rejetées", "En validation", "En OOS", "Meilleure piste",
                  "Problème principal", "Décision du Manager", "Prochaine expérience", "Fichiers/branches modifiés"):
            self.assertIn(k, txt)
        self.assertFalse(json.loads(core.STATE.read_text())["cycle_open"])


if __name__ == "__main__":
    unittest.main()
