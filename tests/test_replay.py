"""End-to-end audit replay (charter section 8) — codex diff-gate 1, finding 4.

Builds a real run in a throwaway `runtime/` tree by driving
`aliasbreaker.cli.main` in process, then proves that
`aliasbreaker.replay.replay` accepts the untouched bundle and rejects every
independent edit of it: the action log, the materialized state, the recorded
verdict, and the fixture itself.

Temp layout mirrors the repo so cli.py's containment rules hold:

    <tmp>/data/cases/dev/case-101.json     (--case must live under ../data/cases)
    <tmp>/runtime/runs/<run>/              (--run must live under ./runs)
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aliasbreaker import cli  # noqa: E402
from aliasbreaker.replay import replay  # noqa: E402

SOURCE_FIXTURE = _REPO / "data" / "cases" / "dev" / "case-101.json"
CASE_ARG = "../data/cases/dev/case-101.json"
SLOTS = (2, 10, 25)


class ReplayTestBase(unittest.TestCase):
    """Shared throwaway runtime tree with one pristine finalized run."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="ab-replay-")
        cls.root = Path(cls._tmp).resolve()
        (cls.root / "data" / "cases" / "dev").mkdir(parents=True)
        cls.fixture = cls.root / "data" / "cases" / "dev" / "case-101.json"
        shutil.copy(SOURCE_FIXTURE, cls.fixture)
        cls.fixture_bytes = cls.fixture.read_bytes()
        cls.runtime = cls.root / "runtime"
        (cls.runtime / "runs").mkdir(parents=True)
        cls._old_cwd = os.getcwd()
        os.chdir(cls.runtime)
        cls._counter = 0
        cls.pristine = cls.make_run("base")

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls._old_cwd)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def run_cli(*argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(list(argv))
        return json.loads(buf.getvalue())

    @classmethod
    def make_run(cls, name, slots=SLOTS, finalize=True):
        run = f"runs/{name}"
        cls.run_cli("start", "--case", CASE_ARG, "--run", run)
        for slot in slots:
            cls.run_cli("observe", "--run", run, "--slot", str(slot),
                        "--why", f"slot {slot} separates the leading pair")
        if finalize:
            cls.run_cli("finalize", "--run", run,
                        "--why", "budget spent, reporting the evaluator result")
        return Path(run)

    def clone(self, label):
        """Fresh copy of the pristine run so each tamper test is isolated."""
        type(self)._counter += 1
        dst = Path("runs") / f"{label}-{type(self)._counter}"
        shutil.copytree(self.pristine, dst)
        return dst

    @contextlib.contextmanager
    def tampered_fixture(self):
        d = json.loads(self.fixture.read_text())
        d["hidden"]["slot_y"][0] = float(d["hidden"]["slot_y"][0]) + 42.0
        self.fixture.write_text(json.dumps(d))
        try:
            yield
        finally:
            self.fixture.write_bytes(self.fixture_bytes)


class TestRunConstruction(ReplayTestBase):

    def test_run_artifacts_exist_and_are_bound_to_the_fixture(self):
        meta = json.loads((self.pristine / "meta.json").read_text())
        self.assertEqual(meta["case_id"], "case-101")
        self.assertEqual(meta["case_path"], CASE_ARG)
        self.assertEqual(len(meta["case_sha256"]), 64)
        self.assertEqual(meta["theta"], cli.THETA_DEFAULT)
        state = json.loads((self.pristine / "state.json").read_text())
        self.assertEqual(state["observed_slots"], list(SLOTS))
        self.assertTrue(state["finalized"])
        v = json.loads((self.pristine / "verdict.json").read_text())
        self.assertEqual(v["observed_slots"], list(SLOTS))
        self.assertEqual(v["n_obs"], len(SLOTS))

    def test_run_directory_must_live_under_runs(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("start", "--case", CASE_ARG, "--run",
                         "../escape-run")
        self.assertEqual(cm.exception.code, 2)
        self.assertFalse((self.root / "escape-run").exists())

    def test_case_fixture_must_live_under_data_cases(self):
        outside = self.root / "sneaky.json"
        outside.write_bytes(self.fixture_bytes)
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("start", "--case", "../sneaky.json", "--run",
                         "runs/sneaky")
        self.assertEqual(cm.exception.code, 2)

    def test_theta_cannot_be_overridden_at_the_cli(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("start", "--case", CASE_ARG, "--run", "runs/theta",
                         "--theta", "0.0")
        self.assertEqual(cm.exception.code, 2)

    def test_why_is_mandatory_on_observe(self):
        run = self.make_run("nowhy", slots=(), finalize=False)
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("observe", "--run", str(run).replace("\\", "/"),
                         "--slot", "3", "--why", "   ")
        self.assertEqual(cm.exception.code, 2)

    def test_cli_rejects_a_changed_fixture_mid_run(self):
        run = self.make_run("hashcheck", slots=(2,), finalize=False)
        arg = str(run).replace("\\", "/")
        with self.tampered_fixture():
            with self.assertRaises(SystemExit) as cm:
                self.run_cli("state", "--run", arg)
            self.assertEqual(cm.exception.code, 2)
        self.run_cli("state", "--run", arg)  # restored: legal again


class TestReplayHappyPath(ReplayTestBase):

    def test_untouched_run_replays_clean(self):
        res = replay(self.pristine)
        self.assertTrue(res["ok"], res["mismatches"])
        self.assertEqual(res["mismatches"], [])
        for name in ("artifacts_readable", "fixture_hash", "replay_legality",
                     "measurement_match", "state_matches_log",
                     "verdict_present", "verdict_recomputes"):
            self.assertTrue(res["checks"].get(name), f"{name} not checked/ok")

    def test_replay_is_deterministic(self):
        a, b = replay(self.pristine), replay(self.pristine)
        self.assertEqual(a["checks"], b["checks"])
        self.assertTrue(a["ok"] and b["ok"])

    def test_copied_run_bundle_is_portable(self):
        """meta stores a relative case_path, so a moved bundle still replays."""
        moved = self.clone("moved")
        res = replay(moved)
        self.assertTrue(res["ok"], res["mismatches"])


class TestReplayTamperDetection(ReplayTestBase):

    def _edit_json(self, path, mutate):
        d = json.loads(path.read_text())
        mutate(d)
        path.write_text(json.dumps(d, indent=2))

    def test_edited_measurement_in_action_log(self):
        run = self.clone("tamper-rv")
        log = run / "actions.jsonl"
        rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
        edited = 0
        for row in rows:
            if row.get("cmd") == "observe" and row.get("ok"):
                row["rv"] = round(float(row["rv"]) + 0.01, 6)
                edited += 1
                break
        self.assertEqual(edited, 1)
        log.write_text("".join(json.dumps(r) + "\n" for r in rows))

        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["measurement_match"])

    def test_measurement_edit_below_tolerance_is_not_flagged(self):
        """RV_TOL exists for the pre-6dp logs; keep the boundary explicit."""
        run = self.clone("tamper-tiny")
        log = run / "actions.jsonl"
        rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
        for row in rows:
            if row.get("cmd") == "observe" and row.get("ok"):
                row["rv"] = float(row["rv"]) + 1e-5
                break
        log.write_text("".join(json.dumps(r) + "\n" for r in rows))
        self.assertTrue(replay(run)["ok"])

    def test_injected_illegal_observe_in_action_log(self):
        run = self.clone("tamper-illegal")
        log = run / "actions.jsonl"
        text = log.read_text()
        # Re-observing an already-passed slot violates chronology.
        text += json.dumps({"cmd": "observe", "slot": int(SLOTS[0]),
                            "ok": True, "rv": 0.0, "why": "x"}) + "\n"
        log.write_text(text)
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["replay_legality"])

    def test_edited_observed_slots_in_state(self):
        run = self.clone("tamper-state")
        self._edit_json(run / "state.json",
                        lambda d: d.__setitem__("observed_slots",
                                                [SLOTS[0], SLOTS[1],
                                                 SLOTS[2] + 1]))
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["state_matches_log"])
        self.assertTrue(res["checks"]["measurement_match"])

    def test_edited_verdict_resolved_flag(self):
        run = self.clone("tamper-verdict")
        self._edit_json(run / "verdict.json",
                        lambda d: d.__setitem__("resolved",
                                                not d["resolved"]))
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["verdict_recomputes"])

    def test_edited_verdict_prediction(self):
        run = self.clone("tamper-pred")
        self._edit_json(run / "verdict.json",
                        lambda d: d.__setitem__("pred", int(d["pred"]) + 1))
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["verdict_recomputes"])

    def test_edited_verdict_max_support(self):
        run = self.clone("tamper-support")
        self._edit_json(run / "verdict.json",
                        lambda d: d.__setitem__("max_support", 0.99999))
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["verdict_recomputes"])

    def test_missing_verdict_file(self):
        run = self.clone("tamper-noverdict")
        (run / "verdict.json").unlink()
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["verdict_present"])

    def test_modified_fixture_breaks_the_hash_binding(self):
        run = self.clone("tamper-fixture")
        with self.tampered_fixture():
            res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["fixture_hash"])
        self.assertTrue(replay(run)["ok"], "restore should re-validate")

    def test_corrupt_meta_json(self):
        run = self.clone("tamper-meta")
        (run / "meta.json").write_text("{ not json")
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["artifacts_readable"])

    def test_missing_action_log(self):
        run = self.clone("tamper-nolog")
        (run / "actions.jsonl").unlink()
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["artifacts_readable"])

    def test_deleted_observe_from_the_action_log(self):
        run = self.clone("tamper-droplog")
        log = run / "actions.jsonl"
        rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
        rows = [r for r in rows
                if not (r.get("cmd") == "observe"
                        and r.get("slot") == SLOTS[-1])]
        log.write_text("".join(json.dumps(r) + "\n" for r in rows))
        res = replay(run)
        self.assertFalse(res["ok"])
        self.assertFalse(res["checks"]["state_matches_log"])


if __name__ == "__main__":
    unittest.main()
