"""Shape check only: the item-2 judge's per-criterion reading of a smoke report (never a verdict)."""
import json, sys
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
import judge_v21_shakedown_item2 as j
rep = json.load(open(sys.argv[1]))
pop = json.load(open(j.POPULATION))
print("refusals (expected: smoke):", j.refuse(rep, __import__("hashlib").sha256(j.POPULATION.read_bytes()).hexdigest(), j.EXPECT_PAGE))
out = j.judge_report(rep, pop, rounds=int(rep.get("rounds") or 1))
for name in j.CRITERIA:
    v = out[name]
    print(f"{name}: {v['verdict']} passed={v['passed']}")
    for r in v["reasons"][:int(sys.argv[2]) if len(sys.argv) > 2 else 6]:
        print("    -", r[:230])
print("records:", json.dumps(out["records"], ensure_ascii=False)[:600])
