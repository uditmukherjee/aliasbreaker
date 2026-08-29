"""Fail-closed leak scan (diff-gate 2 finding 4): nothing the World CLI ever
prints — normal output or errors, any command — may contain hidden-field
names or values: stratum, oracle, true params, unvisited outcomes."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aliasbreaker import cli  # noqa: E402
from aliasbreaker.world import make_case, case_to_dict  # noqa: E402

FORBIDDEN_TOKENS = ("stratum", "oracle", "true_params", "true_basin",
                    "slot_y", "hidden")


class TestNoHiddenLeak(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / "data" / "cases" / "dev").mkdir(parents=True)
        (cls.tmp / "runtime" / "runs").mkdir(parents=True)
        case = None
        seed = 0
        while case is None:
            seed += 1
            case = make_case(seed)
        d = case_to_dict(case)
        d["hidden"]["oracle"] = {"resolvable": True, "n_random": 2000,
                                 "oracle_seed": 1234, "theta": 0.997}
        cls.case = case
        cls.case_path = cls.tmp / "data" / "cases" / "dev" / "leaktest.json"
        cls.case_path.write_text(json.dumps(d, indent=1))
        cls.prev_cwd = os.getcwd()
        os.chdir(cls.tmp / "runtime")

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.prev_cwd)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run(self, argv):
        out = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out):
            try:
                cli.main(argv)
            except SystemExit as e:
                code = e.code or 0
        return code, out.getvalue()

    def _assert_clean(self, text, ctx):
        low = text.lower()
        for token in FORBIDDEN_TOKENS:
            self.assertNotIn(token, low, f"{ctx}: leaked token {token!r}")
        # No unvisited realized outcome values may appear.
        printed_numbers = low
        for idx, y in enumerate(self.case.slot_y):
            if idx in self.observed:
                continue
            self.assertNotIn(f"{y:.3f}", printed_numbers,
                             f"{ctx}: leaked unvisited outcome slot {idx}")

    def test_full_lifecycle_output_is_clean(self):
        self.observed = set()
        rel_case = "../data/cases/dev/leaktest.json"
        for argv, ctx in [
            (["start", "--case", rel_case, "--run", "runs/leak"], "start"),
            (["state", "--run", "runs/leak"], "state"),
            (["diagnostics", "--run", "runs/leak"], "diagnostics"),
        ]:
            code, text = self._run(argv)
            self.assertEqual(code, 0, ctx)
            self._assert_clean(text, ctx)
        code, text = self._run(["observe", "--run", "runs/leak", "--slot",
                                "0", "--why", "leak scan observation"])
        self.assertEqual(code, 0)
        self.observed.add(0)
        self._assert_clean(text, "observe")
        # Error paths must be clean too.
        for argv, ctx in [
            (["observe", "--run", "runs/leak", "--slot", "0",
              "--why", "repeat"], "observe-illegal"),
            (["observe", "--run", "runs/leak", "--slot", "1"],
             "observe-missing-why"),
            (["state", "--run", "runs/nonexistent"], "state-missing-run"),
            (["start", "--case", "../../outside.json", "--run",
              "runs/leak2"], "start-bad-case"),
        ]:
            code, text = self._run(argv)
            self.assertEqual(code, 2, ctx)
            self._assert_clean(text, ctx)
        code, text = self._run(["finalize", "--run", "runs/leak", "--why",
                                "leak scan stop"])
        self.assertEqual(code, 0)
        self._assert_clean(text, "finalize")


if __name__ == "__main__":
    unittest.main()
