"""Red cases for the v21 shakedown's shared instruments S-9 (lock, pre-run checks) and S-1 (the mirror).

ARMS.md §2-§3; ARMS-item1.md §2.1, §2.9, §8 D-18 A'.  Each test shows the instrument refusing or
detecting on a constructed bad input, beside the green on the real one.

  python3 -m unittest tests/test_v21_shakedown_common.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import v21_shakedown_common as c  # noqa: E402

BUSY = "import time\nend = time.time() + 30\nwhile time.time() < end: pass\n"


class LockTest(unittest.TestCase):
    def test_second_holder_is_refused_and_told_who_holds_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lock"
            probe = ("import sys; sys.path.insert(0, %r); import v21_shakedown_common as c\n"
                     "from pathlib import Path\n"
                     "try:\n"
                     "    with c.browser_lock('second', path=Path(%r)): print('acquired')\n"
                     "except c.LockBusy as e: print('busy', e)\n") % (str(HERE / "tools"), str(path))
            with c.browser_lock("first", path=path):
                out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True).stdout
                self.assertTrue(out.startswith("busy"), out)
                self.assertIn('"tool": "first"', out)
            out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True).stdout
            self.assertTrue(out.startswith("acquired"), out)


class ForeignCpuTest(unittest.TestCase):
    def test_a_busy_process_outside_the_tree_is_over_the_limit_and_one_inside_is_not(self):
        own = subprocess.Popen([sys.executable, "-c", BUSY])
        # Orphaned on purpose: the shell exits, the busy child is re-parented away from this tree.
        shell = subprocess.run(["sh", "-c", f"{sys.executable} -c '{BUSY}' >/dev/null 2>&1 & echo $!"],
                               capture_output=True, text=True)
        foreign_pid = int(shell.stdout.strip())
        try:
            time.sleep(0.3)
            sample = c.foreign_cpu(seconds=1.5)
            over = {row["pid"] for row in sample["overLimit"]}
            self.assertIn(foreign_pid, over, sample)
            self.assertFalse(sample["ok"])
            self.assertNotIn(own.pid, over)
            self.assertIn(own.pid, {row["pid"] for row in sample["topOwn"]}, sample)
        finally:
            own.kill()
            os.kill(foreign_pid, 9)


class PreRunTest(unittest.TestCase):
    def fake(self, wallet):
        def runner(cmd):
            if cmd[0] == "busctl":
                return wallet
            return ""
        return runner

    # 2026-11-04: the wallet is recorded, never a refusal (Chrome runs with --password-store=basic).
    def test_wallet_state_never_refuses(self):
        for wallet in ("b true", "b false", "unreadable: no bus"):
            checks = c.pre_run_checks(self.fake(wallet))
            self.assertEqual(checks["refuse"], [], wallet)
            self.assertEqual(checks["kwalletLocked"], wallet)

    def test_every_chrome_launcher_skips_the_wallet(self):
        import run_browser_probe, v21_network
        for module in (run_browser_probe, v21_network):
            self.assertIn('"--password-store=basic"', Path(module.__file__).read_text(), module.__name__)


class MirrorTest(unittest.TestCase):
    def test_injection_keeps_order_and_refuses_bad_input(self):
        html = "<head>" + c.MODULE_ANCHOR + "</head>"
        out = c.inject(html, ["<script>1</script>", "<script>2</script>"])
        self.assertLess(out.index("1"), out.index("2"))
        self.assertLess(out.index("2"), out.index(c.MODULE_ANCHOR))
        with self.assertRaises(SystemExit):
            c.inject("<head></head>", ["<script>1</script>"])
        with self.assertRaises(SystemExit):
            c.inject(html + c.MODULE_ANCHOR, [])
        with self.assertRaises(SystemExit):
            c.inject(html, ["console.log(1)"])

    def test_the_real_mirror_reproduces_the_round_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = c.build_mirror(Path(tmp) / "m", snippets=["<script>/*x*/</script>"],
                                      extra_files={"v21-a.odt": b"a", "deep/dir/b.txt": b"b"})
            self.assertTrue(identity["identityOk"], identity["identityChecks"])
            # The default profile's round page (v22 since SPEC-M3-link-batch-v22 §11.7 step 3; was v21).
            self.assertEqual(identity["profile"], c.DEFAULT_PROFILE)
            self.assertEqual(identity["pageServedSha256"], c.EXPECTED[c.DEFAULT_PROFILE]["pageServed"])
            self.assertEqual(identity["shellDigest"], c.EXPECTED_SHELL_DIGEST)
            self.assertEqual((Path(tmp) / "m" / "deep/dir/b.txt").read_bytes(), b"b")

    def test_a_non_shipped_worker_is_declared(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = c.build_mirror(Path(tmp) / "m", worker_override=b"// not the shipped worker\n")
            self.assertTrue(identity["instrumentedWorker"])
            self.assertFalse(identity["identityOk"])

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "m"
            target.mkdir()
            with self.assertRaises(SystemExit):                       # an existing target
                c.build_mirror(target)
            with self.assertRaises(SystemExit):                       # through a symlink into dist/
                c.build_mirror(Path(tmp) / "m2", extra_files={"e1-fixtures/x.odt": b"x"})
            self.assertFalse((c.DIST / "e1-fixtures" / "x.odt").exists())
            with self.assertRaises(SystemExit):                       # overwriting a served file
                c.build_mirror(Path(tmp) / "m3", extra_files={"e2-editor.html": b"x"})


if __name__ == "__main__":
    unittest.main()
