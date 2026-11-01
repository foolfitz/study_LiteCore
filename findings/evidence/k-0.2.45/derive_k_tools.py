#!/usr/bin/env python3
"""Derive K 0.2.45's tools from K 0.2.44's (SPEC-M3-K-0.2.45 section 2).  Each replacement must match its stated count; the 0.2.44
files are not edited.  What is here is the closed list of differences, one table per file.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / 'wasm_sdk_probe/tools'
EV = ROOT / 'findings/evidence'
K44, K45 = EV / 'k-0.2.44', EV / 'k-0.2.45'
RUNS44, RUNS45 = EV / 'm3-production-ui/runs-0.2.44', EV / 'm3-production-ui/runs-0.2.45'
OLD_PAGE, NEW_PAGE = '3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a', '022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b'
OLD_MAN, NEW_MAN = 'da4e595d859c8659145b80721007be124ad17d4b6517145630a1f7edfed3a7f3', '98371d7f7479021dc2b859bf78db796571d7070b8509548edf7db977bc214174'
B82, B83 = 'e2/editor-shell-v2-bundle-v82.json', 'e2/editor-shell-v2-bundle-v83.json'
KJSON = 'findings/evidence/k-0.2.44/k-binding-inventory.json'

C2_GATE = '''  desk "before c2 r$K"
  # SPEC-M3-K-0.2.45 section 5: C2 is the one timed step and a red there cannot be re-run, so a dirty desk means this round does not
  # run.  Fewer than three complete rounds is NOT_ESTABLISHED by J-b.2, not red.  Nothing else in this chain reads the gate.
  if ! python3 -I findings/evidence/link-batch-v22/shakedown/desk_gate.py --wait 300 > "$D/desk-gate.txt" 2>&1; then
    say "c2 r$K REFUSED dirty desk: not run :: $(tail -1 "$D/desk-gate.txt" | cut -c1-160)"; echo "$(date -u +%FT%TZ) REFUSED dirty desk" >> "$D/chain.txt"; return
  fi
'''

PLAN = {
 (TOOLS / 'run_k_0244_merge.py', TOOLS / 'run_k_0245_merge.py'): [
  ('K ruling item 4 for host 0.2.44 (SPEC-M3-K-0.2.44 section 2)', 'K ruling item 4 for host 0.2.45 (SPEC-M3-K-0.2.45 section 2, derived from tools/run_k_0244_merge.py, not edited)', 1),
  ('rebinds build_e2_c_shell_bundle.MANIFEST to generation 82', 'rebinds build_e2_c_shell_bundle.MANIFEST to generation 83', 1),
  ('binding of findings/evidence/k-0.2.44/k-binding-inventory.json.', 'binding of findings/evidence/k-0.2.45/k-binding-inventory.json.', 1),
  (f'INVENTORY = PROJECT.parent / "{KJSON}"', f'INVENTORY = PROJECT.parent / "{KJSON.replace("0.2.44", "0.2.45")}"', 1),
  (f'MANIFEST = "{B82}"', f'MANIFEST = "{B83}"', 1),
  (f'MANIFEST_SHA256 = "{OLD_MAN}"', f'MANIFEST_SHA256 = "{NEW_MAN}"', 1),
  ('PROFILE = "e2-editor-v28"', 'PROFILE = "e2-editor-v29"', 1),
  ('"generation 82 manifest differs"', '"generation 83 manifest differs"', 1),
  ('is not on v28 (the historical', 'is not on v29 (the historical', 1)],
 (TOOLS / 'judge_k_0244_merge.py', TOOLS / 'judge_k_0245_merge.py'): [
  ('K5 on the ordered engine (SPEC-M3-K-0.2.44 append 2)', 'K5 on the ordered engine (SPEC-M3-K-0.2.44 append 2, on K 0.2.45; derived from tools/judge_k_0244_merge.py)', 1),
  (KJSON, KJSON.replace('0.2.44', '0.2.45'), 1)],
 (TOOLS / 'read_k_0244_merge.py', TOOLS / 'read_k_0245_merge.py'): [
  ('K ruling item 3 for host 0.2.44 (SPEC-M3-K-0.2.44 section 2)', 'K ruling item 3 for host 0.2.45 (SPEC-M3-K-0.2.45 section 2, derived from tools/read_k_0244_merge.py, not edited)', 1),
  ('e2-editor-v28', 'e2-editor-v29', None),
  (KJSON, KJSON.replace('0.2.44', '0.2.45'), 1),
  ('read_k_0244_merge.py', 'read_k_0245_merge.py', None),
  ('judge_k_0244_merge.py', 'judge_k_0245_merge.py', None)],
 (TOOLS / 'read_k_0244_product_path.py', TOOLS / 'read_k_0245_product_path.py'): [
  ('K ruling item 5 (revision 1) for host 0.2.44 (SPEC-M3-K-0.2.44 sections 2 and 3): the plain v28 arm', 'K ruling item 5 (revision 1) for host 0.2.45 (SPEC-M3-K-0.2.45 section 2, SPEC-M3-K-0.2.44 section 3; derived from tools/read_k_0244_product_path.py, not edited): the plain v29 arm', 1),
  ("(run_v82_f3_clipboard.py's --out)", "(run_k_0245_path.py's --out)", 1),
  ('P2  entrypoint 3b0a2ebb..., no candidateCutover, override used = v82', 'P2  entrypoint 022d0cd0..., no candidateCutover, override used = v83', 1),
  ('replay report on v28', 'replay report on v29', 1),
  ('read_k_0244_product_path.py', 'read_k_0245_product_path.py', None),
  (f'PAGE = "{OLD_PAGE}"', f'PAGE = "{NEW_PAGE}"', 1),
  (f'MANIFEST, MANIFEST_SHA256 = "{B82}", "{OLD_MAN}"', f'MANIFEST, MANIFEST_SHA256 = "{B83}", "{NEW_MAN}"', 1),
  ('the span-aware replay on v28 is', 'the span-aware replay on v29 is', 1),
  ('v21 {old} -> v28 {new}', 'v21 {old} -> v29 {new}', 1)],
 (TOOLS / 'check_v82_shift_enter.py', TOOLS / 'check_v83_shift_enter.py'): [
  ("I-enter-raw-substring's replay on v28 (specs/SPEC-M3-K-0.2.44.md section 3, row 8).", "I-enter-raw-substring's replay on v29 (specs/SPEC-M3-K-0.2.44.md section 3, row 8, on K 0.2.45; derived from tools/check_v82_shift_enter.py).", 1),
  ("tools/v82_four_arms_identity.py's identity() (profile v28,\nfrozen generation 82)", "tools/v83_four_arms_identity.py's identity() (profile v29,\nfrozen generation 83)", 1),
  ('python3 -I tools/check_v82_shift_enter.py', 'python3 -I tools/check_v83_shift_enter.py', 1),
  ('from v82_four_arms_identity import identity', 'from v83_four_arms_identity import identity', 1)],
 (K44 / 'probe-legacy-v8-gate.py', K45 / 'probe-legacy-v8-gate.py'): [
  ('K ruling item 6 for host 0.2.44 (specs/SPEC-M3-K-0.2.44.md section 2): the v8 repoint on the generation-82 page', 'K ruling item 6 for host 0.2.45 (specs/SPEC-M3-K-0.2.45.md, derived from k-0.2.44/probe-legacy-v8-gate.py): the v8 repoint on the generation-83 page', 1)],
 (K44 / 'live_bound_set.py', K45 / 'live_bound_set.py'): [
  ('"""Spec K-0.2.44 4.2:', '"""Spec K-0.2.44 4.2, on K 0.2.45 (a copy, so the receipt lands next to it):', 1)],
 (K44 / 'counted-paths/check_counted_paths.py', K45 / 'counted-paths/check_counted_paths.py'): [
  ('"""SPEC-M3-K-0.2.44 append 1: witness and red cases for H1-H4, offline, before any counted run.', '"""SPEC-M3-K-0.2.44 append 1 on K 0.2.45 (derived from k-0.2.44/counted-paths/, not edited): witness and red cases for H1-H4, offline, before any counted run.', 1),
  ('H3  production UI and host_entry asked the bound bundle tool\'s default manifest (v76), not generation 82.', 'H3  production UI and host_entry asked the bound bundle tool\'s default manifest (v76), not generation 83.', 1),
  ('"H3 production UI asks generation 82: exit 0, the pinned digest"', '"H3 production UI asks generation 83: exit 0, the pinned digest"', 1),
  ('ui.SHELL_MANIFEST = "e2/editor-shell-v2-bundle-v81.json"', f'ui.SHELL_MANIFEST = "{B82}"', 1),
  ('"H3 red: asked generation 81, the same check is not exit 0"', '"H3 red: asked generation 82, the same check is not exit 0"', 1),
  ('"H3 host_entry: dist/ is generation 82"', '"H3 host_entry: dist/ is generation 83"', 1),
  ('key.get("wasm") == "profiles/e2-editor-v28/probe.wasm" and key.get("wasmSha256", "").startswith("13f674e4")', 'key.get("wasm") == "profiles/e2-editor-v29/probe.wasm" and key.get("wasmSha256", "").startswith("e61e5890")', 1),
  ('"H4 v28 carries C by its ABI', '"H4 v29 carries C by its ABI', 1),
  ('WITNESS = REPO / "findings/evidence/m3-assets/shakedown/2026-10-31T065458+0000.json"\n',
   'WITNESS = REPO / "findings/evidence/m3-assets/shakedown/2026-10-31T065458+0000.json"\n# The witness is v28-era.  Its closure rows would compare two identities on this tree, so from there on they read 0.2.45\'s own shakedown.\nLIVE = REPO / "findings/evidence/m3-assets/shakedown/2026-11-01T161343+0000.json"\n', 1),
  ('''    # The witness with the record the runner now writes (closure(DIST), as K0-1 holds it equal to the manifest).
    derived = closure(assets.DIST)
    report["package"]["pageFiles"] = {html: page["files"] for html, page in derived["pages"].items()}
''', '''    # 0.2.45's own shakedown, which carries the record the runner now writes, and closure(DIST) must be that record.
    report = json.loads(LIVE.read_text())
    ctx, manifest = assets.run_context(report), assets.run_context(report)["manifest"]
    derived = closure(assets.DIST)
    check("H1 closure(DIST) is the record 0.2.45's shakedown carries",
          report["package"]["pageFiles"] == {html: page["files"] for html, page in derived["pages"].items()})
''', 1)],
 (RUNS44 / 'chain-0.2.44.sh', RUNS45 / 'chain-0.2.45.sh'): [
  ('# The count chain for host 0.2.44 / engine v28 / shell generation 82: the batched count of 0.2.27-0.2.44 (v22-v28).\n# Spec specs/SPEC-M3-K-0.2.44.md (K ruling, findings/evidence/host-0.2.39/k-protocol-ruling/RULING.md, on 0.2.44\'s values).\n',
   '# The count chain for host 0.2.45 / engine v29 / shell generation 83: the batched count of 0.2.27-0.2.45 (v22-v29).\n# Spec specs/SPEC-M3-K-0.2.45.md.  Derived from ../runs-0.2.44/chain-0.2.44.sh, which never ran past its shakedowns.  Closed list of\n# differences (spec section 2): the identity; runs-0.2.45, release-0.2.45; host-stack/bin first on PATH and the own stack\'s URL;\n# tools/run_k_0245_path.py and tools/run_k_0245_merge.py; e2-editor-v29; desk_gate before each C2 round (spec section 5); these lines.\n# (0.2.44\'s header follows.)  Spec specs/SPEC-M3-K-0.2.44.md (K ruling, findings/evidence/host-0.2.39/k-protocol-ruling/RULING.md, on 0.2.44\'s values).\n', 1),
  ('#   setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh \\', '#   setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.45/chain-0.2.45.sh \\', 1),
  ('#   bash findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh --preflight-only', '#   bash findings/evidence/m3-production-ui/runs-0.2.45/chain-0.2.45.sh --preflight-only', 1),
  ('REPO=/home/jiajun/LibreOffice/study_LiteCore\nHOST=$HOME/Projects/Nextcloud_Apps/litecore\ncd "$REPO" || exit 9\n',
   'REPO=/home/jiajun/LibreOffice/study_LiteCore\nHOST=$HOME/Projects/Nextcloud_Apps/litecore\ncd "$REPO" || exit 9\n# The own stack (SPEC-M3-own-stack): every `ddev` below and in the runners is the adapter.\nexport PATH="$REPO/wasm_sdk_probe/host-stack/bin:$PATH"\n', 1),
  ('# Identity this count is about (specs/SPEC-M3-K-0.2.44.md section 1).', '# Identity this count is about (specs/SPEC-M3-K-0.2.45.md section 1).', 1),
  (f'PAGE={OLD_PAGE}', f'PAGE={NEW_PAGE}', 1),
  ('ARCHIVE=wasm_sdk_probe/build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea', 'ARCHIVE=wasm_sdk_probe/build/archive/host-0.2.45-engine-623f51d295ff6030', 1),
  ('HOST_URL=https://litecore.ddev.site:8443/login', 'HOST_URL=https://litecore.localhost:18443/login', 1),
  ('E=findings/evidence/m3-production-ui/runs-0.2.44 ', 'E=findings/evidence/m3-production-ui/runs-0.2.45 ', 1),
  ('R=findings/evidence/release-0.2.44', 'R=findings/evidence/release-0.2.45', 1),
  ('(read_k_0244_product_path.py)', '(read_k_0245_product_path.py)', 1),
  ('--profile e2-editor-v28 --uncounted; read_k_0244_merge.py)', '--profile e2-editor-v29 --uncounted; read_k_0245_merge.py)', 1),
  ('(the owner does not open litecore.ddev.site during it)', '(the owner does not open the litecore site during it: the runners clear the whole lock table)', 1),
  ('engine v28 also carries C', 'engine v29 also carries C', 1),
  ('the plain v28 arm, 3 rounds x 2 browsers, one at a time.', 'the plain v29 arm, 3 rounds x 2 browsers, one at a time.', 1),
  ('# ---- the product-path net (specs/SPEC-M3-K-0.2.44.md section 3)', '# ---- the product-path net (specs/SPEC-M3-K-0.2.45.md section 4, SPEC-M3-K-0.2.44 section 3)', 1),
  ('clipboard wrapper $(h $T/run_v82_f3_clipboard.py)', 'path wrapper $(h $T/run_k_0245_path.py)', 1),
  ('CMD="python3 $T/run_v82_f3_clipboard.py --browser $B --out $OUT"', 'CMD="python3 $T/run_k_0245_path.py --browser $B --out $OUT"', 1),
  ('desk "before product-path v28 $B r$N"', 'desk "before product-path v29 $B r$N"', 1),
  ('START v28 $B r$N ::', 'START v29 $B r$N ::', 1),
  ('END   v28 $B r$N exit', 'END   v29 $B r$N exit', 1),
  ('say "product-path v28 $B r$N exit $RC"', 'say "product-path v29 $B r$N exit $RC"', 1),
  ('python3 $T/run_k_0244_merge.py', 'python3 $T/run_k_0245_merge.py', 5),
  ('--candidate-profile e2-editor-v28', '--candidate-profile e2-editor-v29', 4),
  ('read-0.2.44.sh', 'read-0.2.45.sh', 2),
  ('judge_counted_m2.py --uncounted and read_k_0244_merge.py)', 'judge_k_0245_merge.py --uncounted and read_k_0245_merge.py)', 1),
  ('(both pinned to 3b0a2ebb, k-0.2.44/repin_0244.py)', '(both pinned to 022d0cd0, k-0.2.45/repin_0245.py; judge_p2 reads boundaries commit <= 16, SPEC-M3-v29-tick-pacing append 8)', 1),
  ('  desk "before c2 r$K"\n', C2_GATE, 1)],
 (RUNS44 / 'read-0.2.44.sh', RUNS45 / 'read-0.2.45.sh'): [
  ('# Derived from ../runs-0.2.26/read-0.2.26.sh 2026-10-31 (specs/SPEC-M3-K-0.2.44.md).', '# Derived from ../runs-0.2.44/read-0.2.44.sh 2026-11-02 (specs/SPEC-M3-K-0.2.45.md).  Closed list of differences: paths, the K 0.2.45 tool\n# names, e2-editor-v29, the pre-chain evidence under k-0.2.45.  (0.2.44\'s header follows.)  Derived from ../runs-0.2.26/read-0.2.26.sh 2026-10-31 (specs/SPEC-M3-K-0.2.44.md).', 1),
  ('E=findings/evidence/m3-production-ui/runs-0.2.44', 'E=findings/evidence/m3-production-ui/runs-0.2.45', 1),
  ('R=findings/evidence/release-0.2.44', 'R=findings/evidence/release-0.2.45', 1),
  ('pooled-0.2.44.json', 'pooled-0.2.45.json', 3),
  ('judge_k_0244_merge.py', 'judge_k_0245_merge.py', 2),
  ('read_k_0244_merge', 'read_k_0245_merge', 4),
  ('--profile e2-editor-v28', '--profile e2-editor-v29', 3),
  ('dist/profiles/e2-editor-v28/probe.wasm', 'dist/profiles/e2-editor-v29/probe.wasm', 1),
  ('read_k_0244_product_path', 'read_k_0245_product_path', 6),
  ('EN=findings/evidence/k-0.2.44/enter-replay/report.json', 'EN=findings/evidence/k-0.2.45/enter-replay/report.json', 1),
  ('findings/evidence/k-0.2.44/legacy-v8-gate/report.json', 'findings/evidence/k-0.2.45/legacy-v8-gate/report.json', 1),
  ('findings/evidence/k-0.2.44/enter-replay/report.json', 'findings/evidence/k-0.2.45/enter-replay/report.json', 1),
  ('findings/evidence/k-0.2.44/readers/', 'findings/evidence/k-0.2.45/readers/', 1)],
 (K44 / 'inventory-k-bindings.py', K45 / 'inventory-k-bindings.py'): [
  ('"""Read-only K preparation inventory for host 0.2.44 (engine v28, shell generation 82), derived from\nfindings/evidence/host-0.2.39/inventory-k-bindings.py (not edited).  Closed list of differences: this sentence; the\nrelease read is host-0.2.44\'s; the bundle manifest v82 and tools/v82_four_arms_identity.py; profile e2-editor-v28;\nthe host worktree build/host-0.2.44/litecore.',
   '"""Read-only K preparation inventory for host 0.2.45 (engine v29, shell generation 83), derived from\nfindings/evidence/k-0.2.44/inventory-k-bindings.py (not edited).  Closed list of differences: this sentence; the\nrelease read is host-0.2.45\'s; the bundle manifest v83 and tools/v83_four_arms_identity.py; profile e2-editor-v29;\nthe host worktree build/host-0.2.45/litecore; the chain walked is 0.2.44\'s, which carries H1-H4.', 1),
  ("CHAIN = ROOT / 'findings/evidence/m3-production-ui/runs-0.2.26/chain-0.2.26.sh'", "CHAIN = ROOT / 'findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh'", 1),
  ("READER = CHAIN.with_name('read-0.2.26.sh')", "READER = CHAIN.with_name('read-0.2.44.sh')", 1),
  ("'findings/evidence/host-0.2.44/release.json'", "'findings/evidence/host-0.2.45/release.json'", 1),
  ("bundle.MANIFEST = Path('e2/editor-shell-v2-bundle-v82.json')", "bundle.MANIFEST = Path('e2/editor-shell-v2-bundle-v83.json')", 1),
  ('from v82_four_arms_identity import identity', 'from v83_four_arms_identity import identity', 1),
  ("merge.bound_values(SDK / 'dist', 'e2-editor-v28', page, page, html)", "merge.bound_values(SDK / 'dist', 'e2-editor-v29', page, page, html)", 1),
  ("SDK / 'build/host-0.2.44/litecore'", "SDK / 'build/host-0.2.45/litecore'", 1)],
}

for (src, dst), reps in PLAN.items():
    text = src.read_text(encoding='utf-8')
    for old, new, count in reps:
        got = text.count(old)
        if (count is None and got == 0) or (count is not None and got != count):
            raise SystemExit(f'{src.name}: {old[:80]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    if dst.suffix == '.py':
        compile(text, str(dst), 'exec')
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding='utf-8')
    if dst.suffix == '.sh':
        dst.chmod(0o755)
    print(dst.relative_to(ROOT), 'written')
