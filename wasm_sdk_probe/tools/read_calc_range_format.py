#!/usr/bin/env python3
"""Verify the finite range-format report population and saved artifact hashes."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
from create_calc_range_format_fixture import FORMATS, CASES

PROBE = Path(__file__).with_name("probe_calc_range_format.py")


def required():
    def strings(node):
        if isinstance(node,ast.Constant) and isinstance(node.value,str): return {node.value}
        if isinstance(node,ast.Name) and node.id == "fmt": return set(FORMATS)
        if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=="case" and isinstance(node.slice,ast.Constant) and node.slice.value=="id":
            return {case["id"] for case in CASES}
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
            return {a+b for a in strings(node.left) for b in strings(node.right)}
        raise ValueError("unhandled executable check population: "+ast.dump(node))
    ids=[]
    for node in ast.walk(ast.parse(PROBE.read_text())):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="check":
            ids.extend(strings(node.args[0]))
    if not ids or len(ids)!=len(set(ids)):raise ValueError("empty/duplicate check population")
    return {"opened-cell",*ids}


def validate(report):
    wanted=required();runs=report["runs"]
    expected={(b,n) for b in ("chrome","firefox") for n in range(1,4)}
    assert len(runs)==len(expected) and {(r["browser"],r["repeat"]) for r in runs}==expected,"wrong run population"
    for run in runs:
        assert not run["error"] and run["toolSha256"]==hashlib.sha256(PROBE.read_bytes()).hexdigest(),"run failed or wrong tool"
        checks=run["checks"]
        assert len(checks)==len(wanted) and {c["id"] for c in checks}==wanted,"missing/duplicate case"
        assert all(c["pass"] is True for c in checks),"false case"
    return len(runs)*len(wanted)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out",type=Path);parser.add_argument("--red-cases",action="store_true")
    args=parser.parse_args();report=json.loads((args.out/"report.json").read_text());count=validate(report)
    profile=Path(report["profile"]);manifest=json.loads((profile/"sdk-manifest.json").read_text())
    assert manifest["profile"]=="ods-editor-v2" and "cell-range-formatting" in manifest["capabilities"],"wrong native profile"
    for run in report["runs"]:
        saved=run["saved"];assert hashlib.sha256(Path(saved["path"]).read_bytes()).hexdigest()==saved["sha256"],"saved bytes changed"
    sources=json.loads((args.out/"mirror-sources.json").read_text())
    root=Path(sources["root"]);assert sources["sha256"],"empty mirror"
    for relative,sha in sources["sha256"].items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==sha,"mirror changed: "+relative
    assert sources["engineSha256"],"empty engine identity"
    for name,sha in sources["engineSha256"].items():
        assert hashlib.sha256((profile/name).read_bytes()).hexdigest()==sha,"engine changed: "+name
    controls=[]
    if args.red_cases:
        for name in ("empty","missing-run","missing-case","false-case","wrong-tool"):
            bad=copy.deepcopy(report)
            if name=="empty":bad["runs"]=[]
            elif name=="missing-run":bad["runs"].pop()
            elif name=="missing-case":bad["runs"][0]["checks"].pop()
            elif name=="false-case":bad["runs"][0]["checks"][0]["pass"]=False
            else:bad["runs"][0]["toolSha256"]="0"*64
            try:validate(bad)
            except (AssertionError,ValueError,KeyError):controls.append({"id":name,"rejected":True});continue
            raise AssertionError("red control passed: "+name)
    print(json.dumps({"pass":True,"checks":count,"redControls":controls},indent=2))


if __name__=="__main__":main()
