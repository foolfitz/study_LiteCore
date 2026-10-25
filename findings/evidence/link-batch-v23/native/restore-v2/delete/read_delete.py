#!/usr/bin/env python3
"""Read synchronous Q restoration arms. Exit 0 only for DELETE-Q-HOLDS at exactly N=5."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from arms import D_ARMS
from run_delete import OLD,identity
sys.path.insert(0,str(OLD))
from read_results import read_cell,run_log,landing


def top(payload):
    obj=json.loads(payload);actions=obj.get("actions")
    if actions=="" or actions==[]:return None
    if not isinstance(actions,list) or not actions or "comment" not in actions[0]:
        raise ValueError("unparseable undo actions")
    return actions[0]["comment"]


def judge(cells, rounds):
    expected={(arm["name"],r) for arm in D_ARMS for r in range(1,rounds+1)}
    assert expected and set(cells)==expected,"missing/extra cells"
    problems=[];failures=[]
    for (name,r),cell in cells.items():
        problems.extend(f"{name}/r{r}: {p}" for p in cell["problems"])
    if problems:return {"verdict":"NOT_ESTABLISHED","problems":problems}
    groups={arm["name"].rsplit("-",1)[0] for arm in D_ARMS if arm["name"].endswith("-direct")}
    for group in sorted(groups):
        reference=None
        for r in range(1,rounds+1):
            direct=cells[(group+"-direct",r)];restored=cells[(group+"-restore",r)]
            wrong=cells[(group+"-wrong-line",r)]
            ref=landing(direct)
            if reference is None:reference=ref
            if ref!=reference:problems.append(f"{group}/r{r}: unstable direct reference")
            for variant,cell in (("restore",restored),("wrong-line",wrong)):
                ops=cell["measured"]["ops"]
                want=["K5122","Qbefore" if variant=="restore" else "Qwrong","K1283"]
                if [op["op"] for op in ops]!=want:
                    problems.append(f"{group}/{variant}/r{r}: wrong op sequence");continue
                if ops[1].get("restoreSequence") != ["RESET","START","RESET"]:
                    problems.append(f"{group}/{variant}/r{r}: Q primitive sequence absent")
                if not all(isinstance(op.get("pollIndex"),int) and op["pollIndex"]>0 for op in ops) or len({op.get("pollIndex") for op in ops})!=1:
                    problems.append(f"{group}/{variant}/r{r}: compound command spans polls")
                first,reset=ops[0]["atReturn"],ops[1]["atReturn"]
                if first["selType"]!=1 or not any(c in first["selText"] for c in "\r\n\u2028\u2029"):
                    failures.append(f"{group}/{variant}/r{r}: K1 did not select a separator")
                if reset["selType"]!=0 or reset["selText"]:
                    failures.append(f"{group}/{variant}/r{r}: RESET did not return NONE")
            if [op["op"] for op in direct["measured"]["ops"]]!=["K1283"]:
                problems.append(f"{group}/r{r}: wrong direct key")
            if landing(restored)!=ref:failures.append(f"{group}/r{r}: restored saved shape/caret differs")
            if landing(wrong)==ref:problems.append(f"{group}/r{r}: wrong-line control is not discriminating")
            try:
                direct_top=top(direct["measured"]["ops"][-1]["atReturn"]["undo"])
                restore_top=top(restored["measured"]["ops"][-1]["atReturn"]["undo"])
                if not direct_top:problems.append(f"{group}/r{r}: direct key has no undo top")
                if direct_top!=restore_top:failures.append(f"{group}/r{r}: undo tops differ")
            except (ValueError,KeyError,TypeError):problems.append(f"{group}/r{r}: unreadable undo top")
    verdict="NOT_ESTABLISHED" if problems or rounds!=5 else "DELETE-Q-FAILS" if failures else "DELETE-Q-HOLDS"
    return {"verdict":verdict,"cells":len(cells),"rounds":rounds,"problems":problems,"failures":failures}


def read(out,rounds):
    recorded=json.loads((out/"identity.json").read_text())
    assert recorded==identity(recorded["binary"]),"binary/source/fixture identity changed"
    log=run_log(out);wanted={(a["name"],"unipoll",r) for a in D_ARMS for r in range(1,rounds+1)}
    assert set(log)==wanted,"run-log population differs from executable arms"
    assert json.loads((out/"arms.json").read_text())==D_ARMS,"recorded arms differ from executable arms"
    cells={}
    for name,mode,r in sorted(wanted):
        cell=read_cell(out/name,mode,r,log);cells[(name,r)]=cell
        path=out/name/f"{mode}-r{r}.jsonl"
        if not path.exists():continue
        records=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        env=next((x for x in records if x["rec"]=="env"),{})
        if env.get("OC_A11Y") is not None:cell["problems"].append("a11y must remain disabled")
        points={x["name"]:x["rect"] for x in records if x["rec"]=="point"}
        try:
            before=[int(v.strip()) for v in points["before"].split(",")]
            wrong=[int(v.strip()) for v in points["wrong"].split(",")]
            if len(before)!=4 or len(wrong)!=4 or before[1]<=wrong[1]:raise ValueError()
        except (ValueError,KeyError):cell["problems"].append("missing/distorted adjacent recorded points")
    return judge(cells,rounds)


def self_test():
    undo=json.dumps({"actions":[{"comment":"Delete paragraph separator"}]})
    def op(name,text="",kind=0):
        return {"op":name,"pollIndex":42,"restoreSequence":["RESET","START","RESET"],"atReturn":{"selType":kind,"selText":text,"undo":undo}}
    cells={}
    for arm in D_ARMS:
        variant=arm["name"].split("-",2)[2]
        ops=[op("K1283")] if variant=="direct" else [op("K5122","\n",1),op("Qbefore" if variant=="restore" else "Qwrong"),op("K1283")]
        for r in range(1,6):cells[(arm["name"],r)]={"problems":[],"shape":["wrong" if variant=="wrong-line" else "joined"],"caret":["a","b"],"measured":{"ops":copy.deepcopy(ops)}}
    assert judge(cells,5)["verdict"]=="DELETE-Q-HOLDS"
    controls=[]
    for name in ("wrong-save","wrong-undo","reset-not-none","no-separator","no-red-discriminator","unclean","bad-undo","split-polls","wrong-Q-sequence","missing-cell"):
        bad=copy.deepcopy(cells);cell=bad[("delete-plain-restore",1)]
        if name=="wrong-save":cell["shape"]=["bad"]
        elif name=="wrong-undo":cell["measured"]["ops"][-1]["atReturn"]["undo"]=json.dumps({"actions":[{"comment":"different"}]})
        elif name=="reset-not-none":cell["measured"]["ops"][1]["atReturn"]["selType"]=1
        elif name=="no-separator":cell["measured"]["ops"][0]["atReturn"]["selText"]="x"
        elif name=="no-red-discriminator":bad[("delete-plain-wrong-line",1)]["shape"]=["joined"]
        elif name=="unclean":cell["problems"]=["duplicate run-log entry"]
        elif name=="bad-undo":cell["measured"]["ops"][-1]["atReturn"]["undo"]="not JSON"
        elif name=="split-polls":cell["measured"]["ops"][1]["pollIndex"]=43
        elif name=="wrong-Q-sequence":cell["measured"]["ops"][1]["restoreSequence"]=["RESET"]
        else:bad.pop(("delete-plain-restore",1))
        try:rejected=judge(bad,5)["verdict"]!="DELETE-Q-HOLDS"
        except AssertionError:rejected=True
        assert rejected,name
        controls.append({"id":name,"rejected":True})
    print(json.dumps({"syntheticGreen":True,"redControls":controls,"nativeAcceptance":"NOT_ESTABLISHED"},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("out",type=Path,nargs="?")
    parser.add_argument("--rounds",type=int,default=5);parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:self_test()
    else:
        if args.out is None:parser.error("out is required")
        result=read(args.out,args.rounds);print(json.dumps(result,indent=2))
        raise SystemExit(0 if result["verdict"]=="DELETE-Q-HOLDS" else 1)
