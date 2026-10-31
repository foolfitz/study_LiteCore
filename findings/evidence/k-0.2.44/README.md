# K for host 0.2.44: preparation (2026-10-31)

Spec `specs/SPEC-M3-K-0.2.44.md`. The owner chose B, then wrote 「請執行A／然後可以跑B／但我不在座位，請自主執行／授權讓你跑編譯和連結」.

- **Inventory** (`inventory-k-bindings.py` -> `k-binding-inventory.json`): 22 string pins unfrozen, the merge `BINDING` frozen.
- **Repin** (`repin_0244.py`, `repin-0.2.44.json`): 24 sites in 10 files (22 + the two C2 judges). Fixed by execution before any run: `HOST_COMMIT` must be the short hash, the runners compare it with `git log --oneline`.
- **Live-bound set** (`live_bound_set.py`, `live-bound-set.json`): 50 paths unmoved; `--flip` red.
- **P6** (`p6_reds.py`, `p6-named-reds.txt`, `p6-static-first.txt`): the static target's red set after the repin equals v28's pre-link set. Unit tests 134 OK.
- **Readers** (`readers/`): `read_k_0244_merge.py` red on the 0.2.26 reports as they are (32 problems), holds on a synthetic rebinding, 10/10 mutations red; `read_k_0244_product_path.py` holds on F3-82 taken three times, 16/16 mutations red, and STOP on the 0.2.26 directory (42 != 46).
- **Page-gate negative** (`legacy-v8-gate/`): `LEGACY_V8_CONTROL_REFUSED`: control PASS, legacy-v8 `EXPECTED_REFUSAL`, `insertRequests 0`, page `3b0a2ebb`, v8 wasm `4a2710bb`.
- **Enter replay** (`enter-replay/`): `V24_ENTER_HOLDS`, 3/3 on v28. The first attempt was refused by the bound tool's v24 page pin (`enter-replay-run-01-refused/`), hence the thin wrapper `tools/check_v82_shift_enter.py`.
- **Merge smoke** (`merge-smoke/`, Chrome, one round, shakedown mode, through `run_k_0244_merge.py`): runner `aaee0cda`, bound equal to the binding, 26 cases verified (20 key-undo, 5 boundary no-op, 1 selection delete).
- **Lock table** (`lock-row-before.txt`): one row, the owner's hand test of 0.2.44 (`empty.odt`, 00:39:49, ttl 8101 s), expired about 10 hours before; that one row was deleted so P5 reads 0.
