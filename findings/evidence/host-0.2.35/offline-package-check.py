#!/usr/bin/env python3
"""K0/Z0/H5-1 of check_m3_assets.py on a host app directory, offline, plus its package red cases.

The same package half that `check_m3_assets.py --red-cases` runs (score_package, then every
PACKAGE_CASES mutation must turn its own clause red), on an app directory instead of a full report:
no wire, no browser, nothing on the live instance.  Prints only; writes nothing.

  offline-package-check.py APP_DIR
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "wasm_sdk_probe" / "tools"))
import check_m3_assets as assets  # noqa: E402

# Package-only candidate binding; full K pins remain untouched.
assets.BUILD_ID = "b007f950b2e18cd2"


def main() -> int:
    app = Path(sys.argv[1])
    pkg = assets.package_record(app)
    print(f"app {app}")
    print(f"buildId {pkg['manifest'].get('buildId')}  schema {pkg['manifest'].get('schema')}  "
          f"files {len(pkg['manifest'].get('files', {}))}  derived {len(pkg['derived'])}  bound BUILD_ID {assets.BUILD_ID}")
    problems = assets.score_package(pkg, True)
    print(f"K0/Z0/H5-1 problems: {len(problems)}")
    for problem in problems:
        print(f"  {problem}")
    if problems:
        print("red cases not run: the package record is not clean")
        return 1
    failures = 0
    for clause, label, mutate in assets.PACKAGE_CASES:
        broken = copy.deepcopy(pkg)
        mutate(broken)
        red = any(p.startswith(clause) for p in assets.score_package(broken, True))
        failures += not red
        print(f"  {'red ' if red else 'GREEN'}  {clause} {label}")
    print(f"package red cases: {len(assets.PACKAGE_CASES) - failures}/{len(assets.PACKAGE_CASES)} red")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
