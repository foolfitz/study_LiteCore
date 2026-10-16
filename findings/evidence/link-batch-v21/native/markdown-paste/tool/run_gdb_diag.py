#!/usr/bin/env python3
"""One gdb-traced process per corpus item (diagnostic, not an arm).

Usage: run_gdb_diag.py PROBE_BINARY SCRATCH_DIR OUT_DIR CORPUS_ID [CORPUS_ID ...]

Same environment as run_arms.py (env -i, LANG=zh_TW.UTF-8, svp, nice, fresh
profile, empty template at the document start), under
`gdb -batch -x gdb_dialog_trace.py`. Writes OUT_DIR/DIAG-gdb-<id>/.
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_arms  # noqa: E402


def main(argv):
    probe, scratch, out_dir = argv[1:4]
    for corpus in argv[4:]:
        work = os.path.join(scratch, "gdb-" + corpus)
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(os.path.join(work, "profile"))
        os.makedirs(os.path.join(work, "out"))
        doc = os.path.join(work, "doc.odt")
        shutil.copyfile(os.path.join(HERE, "inputs/empty-template.odt"), doc)
        dest = os.path.join(out_dir, "DIAG-gdb-" + corpus)
        os.makedirs(dest, exist_ok=True)
        env = {"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin", "LANG": run_arms.ZH,
               "SAL_USE_VCLPLUGIN": "svp"}
        cmd = ["nice", "-n", "10", "timeout", "300", "gdb", "-q", "-batch", "-x",
               os.path.join(HERE, "gdb_dialog_trace.py"), "--args", probe, run_arms.INSTALL,
               "file://" + os.path.join(work, "profile"), "file://" + doc,
               os.path.join(work, "out"), run_arms.MD,
               os.path.join(HERE, "corpus", corpus + ".md"), "doc-start", "60"]
        with open(os.path.join(dest, "cmd.txt"), "w") as handle:
            handle.write("env -i " + " ".join("%s=%s" % kv for kv in env.items()) + " " +
                         " ".join(cmd).replace(run_arms.REPO, "<repo>").replace(scratch, "<scratch>") + "\n")
        with open(os.path.join(dest, "runner.log"), "w") as log:
            run_arms.wait_for_quiet(log)
            proc = subprocess.run(cmd, env=env, capture_output=True, cwd=work)
            log.write("rc=%d\n" % proc.returncode)
        with open(os.path.join(dest, "gdb-stdout.txt"), "wb") as handle:
            handle.write(proc.stdout)
        with open(os.path.join(dest, "gdb-stderr.txt"), "wb") as handle:
            handle.write(proc.stderr[-20000:])
        print("==", corpus, "rc", proc.returncode)
        for line in proc.stdout.decode("utf-8", "replace").splitlines():
            if line.startswith("TRACE") or '"probe":"paste"' in line or '"probe":"done"' in line \
                    or '"probe":"blocked"' in line:
                print(line[:200])
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
