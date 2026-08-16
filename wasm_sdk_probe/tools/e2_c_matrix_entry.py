#!/usr/bin/env python3
"""The D0 entry assertion: refuse to run a round against a matrix that is not
frozen, or whose baseline does not describe what is on disk.

Why this exists, in the words of the external review that named it: between the
relink and the freeze there is a window in which the second round's matrix still
carries placeholder hashes, and **nobody checks that the freeze happened before
D0**.  The first round was bitten by the neighbouring mistake -- 27 cells used a
gesture the product does not use, and the matrix had never said which gesture to
use.  A matrix written after the data is not a prediction.

Three refusals, all fail-closed:

  1. `status` is not `frozen-before-D0`;
  2. any baseline hash is still a placeholder, or missing, or not a hex digest;
  3. the baseline hashes do not match the artifact on disk.

(3) is what makes this an assertion rather than a spelling check: a frozen
matrix that describes a different build is worse than an unfrozen one, because
it looks finished.

Usable as a library (`assert_entry`) and as a command.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "TO-BE-FILLED-AT-RELINK"
FROZEN_STATUS = "frozen-before-D0"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# The artifact fields a round's baseline may pin, and the file each one is the
# digest of.  `shellBundleSha256` and `manifestSha256` are not read from
# dist/profiles/, so they are checked for shape and freeze only -- named here so
# the omission is deliberate rather than an oversight.
ARTIFACT_FILES = {
    "wasmSha256": "probe.wasm",
    "loaderSha256": "probe.js",
    "workerSha256": "sdk-worker.js",
}
SHAPE_ONLY = ("shellBundleSha256", "manifestSha256")


def sha256_of(path: Path) -> str | None:
    import hashlib
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def assert_entry(matrix_path: Path, *, profile: str | None = None,
                 project: Path = PROJECT) -> dict:
    """Evaluate the entry assertion.  Returns a report; never raises for a
    failed assertion -- the caller decides whether to stop, and the report says
    exactly which of the three refusals fired."""
    problems: list[str] = []
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"matrix": str(matrix_path), "ok": False,
                "problems": [f"matrix could not be read: {error}"]}

    status = matrix.get("status")
    if status != FROZEN_STATUS:
        problems.append(
            f"matrix status is {status!r}, not {FROZEN_STATUS!r}: a round may "
            f"not be judged against a matrix that is still being written")

    baseline = matrix.get("baseline") or {}
    checked: dict[str, str] = {}
    for field in list(ARTIFACT_FILES) + list(SHAPE_ONLY):
        if field not in baseline:
            continue
        value = str(baseline[field])
        checked[field] = value
        if value == PLACEHOLDER:
            problems.append(f"baseline {field} is still {PLACEHOLDER}")
        elif not HEX64.match(value):
            problems.append(f"baseline {field} is not a sha256 digest: {value!r}")

    if not checked:
        problems.append("the matrix baseline pins no artifact hash at all")

    target = profile or baseline.get("profile")
    directory = project / "dist" / "profiles" / str(target)
    on_disk: dict[str, str | None] = {}
    for field, filename in ARTIFACT_FILES.items():
        if field not in baseline or baseline[field] == PLACEHOLDER:
            continue
        actual = sha256_of(directory / filename)
        on_disk[field] = actual
        if actual is None:
            problems.append(
                f"{directory / filename} could not be read, so the baseline's "
                f"{field} cannot be confirmed against the scene")
        elif actual != baseline[field]:
            problems.append(
                f"baseline {field} does not match the artifact on disk "
                f"({baseline[field][:12]}… vs {actual[:12]}…)")

    return {
        "matrix": str(matrix_path),
        "status": status,
        "profile": target,
        "baselineHashes": checked,
        "onDisk": on_disk,
        "ok": not problems,
        "problems": problems,
    }


def require_entry(matrix_path: Path, *, profile: str | None = None,
                  project: Path = PROJECT) -> dict:
    """assert_entry, but stops the process.  This is what a runner calls."""
    report = assert_entry(matrix_path, profile=profile, project=project)
    if not report["ok"]:
        lines = "\n".join(f"  - {problem}" for problem in report["problems"])
        raise SystemExit(
            f"D0 entry assertion refused this round:\n{lines}\n"
            f"matrix: {matrix_path}\n"
            f"Fix the matrix (or the profile) before running, not afterwards -- "
            f"the whole point of a frozen matrix is that it exists first.")
    return report


def self_test() -> int:
    import copy
    import tempfile

    failures: list[str] = []
    ran: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    live = PROJECT / "e2" / "validation-matrix-v1.json"
    draft = PROJECT / "e2" / "validation-matrix-v2-draft.json"

    check("the frozen first-round matrix passes",
          assert_entry(live)["ok"], str(assert_entry(live)["problems"]))

    # The case the external review named: the draft must NOT be admitted.
    report = assert_entry(draft)
    check("the v2 DRAFT is refused", not report["ok"])
    check("and it is refused for BOTH reasons, not just the status",
          any("status" in problem for problem in report["problems"])
          and any(PLACEHOLDER in problem for problem in report["problems"]),
          str(report["problems"]))

    original = json.loads(draft.read_text(encoding="utf-8"))

    def with_matrix(mutate) -> dict:
        cloned = copy.deepcopy(original)
        mutate(cloned)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.json"
            path.write_text(json.dumps(cloned), encoding="utf-8")
            return assert_entry(path)

    def freeze_but_keep_placeholders(cloned):
        cloned["status"] = FROZEN_STATUS

    # The trap this assertion exists for: someone flips the status and forgets
    # the hashes.  A checker that only reads `status` would wave this through.
    check("flipping status alone does NOT get the draft admitted",
          not with_matrix(freeze_but_keep_placeholders)["ok"])

    frozen = json.loads(live.read_text(encoding="utf-8"))

    def wrong_hash(cloned):
        cloned.clear()
        cloned.update(copy.deepcopy(frozen))
        cloned["baseline"]["wasmSha256"] = "0" * 64

    check("a frozen matrix whose hash is not the artifact on disk is refused",
          not with_matrix(wrong_hash)["ok"])

    def no_hashes(cloned):
        cloned.clear()
        cloned.update(copy.deepcopy(frozen))
        for field in list(ARTIFACT_FILES) + list(SHAPE_ONLY):
            cloned["baseline"].pop(field, None)

    check("a matrix that pins no hash at all is refused",
          not with_matrix(no_hashes)["ok"])

    def truncated_hash(cloned):
        cloned.clear()
        cloned.update(copy.deepcopy(frozen))
        cloned["baseline"]["shellBundleSha256"] = "deadbeef"

    check("a hash-shaped field that is not a digest is refused",
          not with_matrix(truncated_hash)["ok"])

    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          "checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path,
                        default=PROJECT / "e2" / "validation-matrix-v1.json")
    parser.add_argument("--profile")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    report = assert_entry(args.matrix, profile=args.profile)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
