#!/usr/bin/env python3
"""Read actual Files range/autosave artifacts and external preservation proofs."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
from probe_calc_range_autosave_host import FORMATS, ods_snapshot, snapshot_matches

TOOLS=Path(__file__).resolve().parent
PROBE=TOOLS/"probe_calc_range_autosave_host.py"
HARNESS=TOOLS/"run_calc_editor_host.py"


def required():
    def strings(node):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):return {node.value}
        if isinstance(node,ast.Name) and node.id=="browser":return {"chrome","firefox"}
        if isinstance(node,ast.Name) and node.id=="fmt":return set(FORMATS)
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
            return {a+b for a in strings(node.left) for b in strings(node.right)}
        raise ValueError("unknown executable check expression: "+ast.dump(node))
    ids=[]
    trees=[ast.parse(PROBE.read_text())]
    inherited=ast.parse(HARNESS.read_text())
    for name in ("run","readonly_round"):
        found=[n for n in ast.walk(inherited) if isinstance(n,ast.FunctionDef) and n.name==name]
        if len(found)!=1:raise ValueError("inherited population drifted: "+name)
        trees.extend(found)
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="check":
                ids.extend(strings(node.args[0]))
    if not ids or len(ids)!=len(set(ids)):raise ValueError("empty/duplicate executable case population")
    return set(ids)


def validate(report,build_id):
    assert report.get("ok") is True and not report.get("error"),"failed host run"
    assert report["expectedBuildId"]==build_id,"wrong candidate build"
    assert report["toolSha256"]==hashlib.sha256(PROBE.read_bytes()).hexdigest(),"wrong tool identity"
    assert report["dependencySha256"],"empty dependency identity"
    for name,sha in report["dependencySha256"].items():
        assert hashlib.sha256((TOOLS/name).read_bytes()).hexdigest()==sha,"dependency drift: "+name
    wanted=required();checks=report["checks"]
    assert len(checks)==len(wanted) and {c["id"] for c in checks}==wanted,"missing/extra/duplicate cases"
    assert all(c["ok"] is True for c in checks),"false case"
    runs=report["runs"]
    assert len(runs)==4 and {(r["browser"],r["kind"]) for r in runs}=={(b,k) for b in ("chrome","firefox") for k in ("admin","readonly")},"wrong browser/route population"
    for run in runs:
        assert "/"+build_id+"-" in run["entry"]["landed"],"wrong served package"
    clean=report["cleanup"]
    assert not clean.get("errors") and clean["ownedUnlocks"]==[],"fallback cleanup or cleanup failure"
    assert clean["shareRemoved"] is True and clean["userRemoved"] is True and clean["folderDeleteStatus"] in (200,204),"owned fixture cleanup incomplete"
    return len(checks)


def artifacts(out,report):
    tiles=0
    for run in report["runs"]:
        if run["kind"]!="admin":continue
        browser=run["browser"]
        snapshots=run["serverSnapshots"]
        assert len(snapshots)==2 and {s["phase"] for s in snapshots}=={"idle","export"},"missing server snapshots"
        for item in snapshots:
            path=out/item["file"]
            assert path.parent==out and item["status"]==200,"bad snapshot path/status"
            assert hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"],"server artifact changed"
            assert snapshot_matches(ods_snapshot(path),browser,item["phase"]),"server ODS XML mismatch"
        view=json.loads((out/(browser+"-range-tiles.json")).read_text())
        assert view["visibleTiles"]>0 and view["tiles"] and view["revision"]==view["context"]["revision"],"empty/stale viewport"
        assert all(t["matched"] is True for t in view["tiles"]),"tile mismatch"
        tiles+=len(view["tiles"])
        saves=run["host"]["saves"]
        assert len(saves)>=2 and all(s["trigger"]=="auto" and s["outcome"]=="saved" and s["target"]=="original" and s["settled"] for s in saves),"host outcome differs from automatic original saves"
    return tiles


def preservation(directory):
    def read(name):return json.loads((directory/name).read_text())
    before=read("owner-document-before.json");after=read("owner-document-after.json")
    assert before==after and before["fileId"]==24920 and before["status"]==200,"owner document changed or missing"
    locks=(directory/"locks-before.txt").read_text().split()
    assert locks==(directory/"locks-after.txt").read_text().split() and "24674" in locks,"unrelated locks changed"
    states=lambda filename:{p["name"]:p["status"] for p in read(filename)["raw"]}
    assert states("ddev-before.json")==states("ddev-after.json"),"service state changed"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out",type=Path)
    parser.add_argument("--release",type=Path,required=True)
    parser.add_argument("--safety-dir",type=Path,required=True)
    parser.add_argument("--red-cases",action="store_true")
    args=parser.parse_args();out=args.out.resolve()
    report=json.loads((out/"report.json").read_text())
    build_id=json.loads(args.release.read_text())["buildId"]
    count=validate(report,build_id);tiles=artifacts(out,report);preservation(args.safety_dir)
    controls=[]
    if args.red_cases:
        for name in ("empty","missing-case","false-case","missing-browser","wrong-tool","wrong-build","cleanup-fallback"):
            bad=copy.deepcopy(report)
            if name=="empty":bad["checks"]=[]
            elif name=="missing-case":bad["checks"].pop()
            elif name=="false-case":bad["checks"][0]["ok"]=False
            elif name=="missing-browser":bad["runs"].pop()
            elif name=="wrong-tool":bad["toolSha256"]="0"*64
            elif name=="wrong-build":bad["expectedBuildId"]="wrong"
            else:bad["cleanup"]["ownedUnlocks"]=[{"name":"synthetic","status":204}]
            try:validate(bad,build_id)
            except (AssertionError,KeyError,ValueError):controls.append({"id":name,"rejected":True});continue
            raise AssertionError("red control passed: "+name)
    print(json.dumps({"pass":True,"checks":count,"views":2,"tiles":tiles,"redControls":controls},indent=2))


if __name__=="__main__":main()
