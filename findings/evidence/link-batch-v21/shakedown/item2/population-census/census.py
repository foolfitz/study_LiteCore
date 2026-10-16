"""Mutation census of tools/v21_item2_population.py: blank each `raise PopulationError` in turn and run
tests/test_v21_item2_population.py against the mutant; a raise whose removal turns no test red is unguarded.

  python3 -I -B census.py <wasm_sdk_probe/tools> <wasm_sdk_probe/tests>   (output: census.txt)
"""
import importlib.util, io, re, sys, unittest
from pathlib import Path
TOOLS = Path(sys.argv[1]); TESTS = Path(sys.argv[2]); SRC = (TOOLS / "v21_item2_population.py").read_text()
sys.path.insert(0, str(TOOLS))
lines = SRC.splitlines(keepends=True)
sites = [i for i, l in enumerate(lines) if "raise PopulationError" in l]
def run(src):
    spec = importlib.util.spec_from_loader("v21_item2_population", loader=None, origin=str(TOOLS / "v21_item2_population.py"))
    mod = importlib.util.module_from_spec(spec); mod.__file__ = str(TOOLS / "v21_item2_population.py")
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    sys.modules["v21_item2_population"] = mod
    for name in [n for n in sys.modules if n.startswith("test_v21_item2_population")]: del sys.modules[name]
    suite = unittest.defaultTestLoader.loadTestsFromName("test_v21_item2_population")
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return sorted({t.id().split(".")[-1] for t, _ in res.failures + res.errors}), res.testsRun
sys.path.insert(0, str(TESTS))
base, n = run(SRC)
print("unmutated:", base or "all green", n)
for i in sites:
    m = list(lines); indent = re.match(r"\s*", m[i]).group(0)
    # blank the raise statement (it may continue on the next lines)
    depth = 0; k = i
    while True:
        depth += m[k].count("(") - m[k].count(")"); m[k] = "" if k > i else indent + "pass  # mutated\n"
        if depth <= 0: break
        k += 1
    red, _ = run("".join(m))
    print(f"line {i+1}: {lines[i].strip()[:70]} -> red: {red or 'NOTHING'}")
