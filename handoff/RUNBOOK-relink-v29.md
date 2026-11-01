# Owner-only v29 link (finding 177: no main-loop pacing while there is work)

Spec: `specs/SPEC-M3-v29-tick-pacing.md`. Evidence: `findings/evidence/v29-177/`.

This is one fresh product link of a new identity, `e2-editor-v29`. It does not touch ddev, a host, LibreOffice core, any frozen profile or the count chain.

## 0. Before handing over (agent)

- [x] Spec pinned after one review round (`findings/evidence/v29-177/review-opus-1.md`).
- [x] U: `main_loop_pacing_test` green, four mutations red.
- [x] S: `-fsyntax-only` clean; three controls fail where they should, including the hook itself broken in a temporary copy.
- [x] EM_ASM body read after `-E`, parses as JS.
- [x] M: `make -i test-e2-c-static` red set equals `p6-named-reds.txt`; M1-1 green with the `E2_V29` carrier.
- [x] D: `make -n` of the owner's line: four compile lines under `build/e2/editor-v29`, one guarded link.
- [x] The pacing itself measured on the mirror, without a link (`first-contact/typing-control/`).

## 1. The link (owner)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
bash tools/link_v29_tick_pacing_owner.sh
```

Report: the last lines of the output. **`withheld` must read `[]`** and `profile` `e2-editor-v29`.

If it says `Existing v29 attempt found`, stop and report; do not clean.

## 2. After the link (agent)

Spec section 6: P (contract, archive), cut the page, generation 83, then T1-T4 on the mirror. The host steps wait for the move off ddev (owner, 2026-11-01).
