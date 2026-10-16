#!/usr/bin/env python3
"""Make d1_population.py go red, and show that a new arm is classified without editing anything.

Usage: python3 -I population_red_demo.py ARMS_JSON SCRATCH_DIR

Runs d1_population.py (next to this file) on four scratch copies of ARMS_JSON and
prints each exit status and the tail of its output:
  1. one arm's script gets a step outside the grammar ("X9")       -> must exit 1
  2. only the OUT arms are kept (zero IN)                           -> must exit 1
  3. a fictional arm with only product steps is appended            -> exit 0, listed IN
  4. a fictional arm with a u. step is appended                     -> exit 0, listed OUT with rule u.
Exits 1 if any of the four does not behave as stated.
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def run(path):
    p = subprocess.run([sys.executable, '-I', str(HERE / 'd1_population.py'), str(path)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    arms = json.loads(pathlib.Path(sys.argv[1]).read_text())
    scratch = pathlib.Path(sys.argv[2])
    scratch.mkdir(parents=True, exist_ok=True)
    ok = True

    def case(title, mutated, want_rc, must_contain):
        nonlocal ok
        path = scratch / f'arms-{len(list(scratch.glob("arms-*.json")))}.json'
        path.write_text(json.dumps(mutated, indent=1))
        rc, out = run(path)
        lines = out.strip().splitlines()
        hit = [ln for ln in lines if must_contain in ln]
        good = rc == want_rc and bool(hit)
        ok = ok and good
        print(f'## {title}')
        print(f'exit {rc} (want {want_rc}); line containing {must_contain!r}: {hit[:2]}')
        print('tail:')
        for ln in lines[-4:]:
            print(f'  {ln}')
        print(f'-> {"as stated" if good else "NOT as stated"}')
        print()

    a = json.loads(json.dumps(arms))
    a[0]['script'] = a[0]['script'].replace(',L', ',X9,L')
    case(f'1. unknown step X9 in {a[0]["name"]}', a, 1, "unknown step kind 'X9'")

    import importlib.util
    spec = importlib.util.spec_from_file_location('d1_population', HERE / 'd1_population.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ins, _, _ = mod.classify(arms)
    in_names = {x['name'] for x in ins}
    case('2. only the OUT arms kept', [x for x in arms if x['name'] not in in_names], 1, 'zero arms IN')

    a = arms + [{'name': 'fictional-new-arm', 'fixture': 'plain3', 'script': 'k1024,k1027x3,Mce=9221,L',
                 'group': 'demo', 'note': 'not run', 'saves': False, 'tool': 'main'}]
    case('3. fictional arm with only product steps appended', a, 0, '- fictional-new-arm [plain3]')

    a = arms + [{'name': 'fictional-uno-arm', 'fixture': 'plain3', 'script': 'u.uno:GoDown,Mch=9220,L',
                 'group': 'demo', 'note': 'not run', 'saves': False, 'tool': 'main'}]
    case('4. fictional arm with a u. step appended', a, 0, '- fictional-uno-arm: u. (u.uno:GoDown)')

    print('ALL AS STATED' if ok else 'SOMETHING WAS NOT AS STATED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
