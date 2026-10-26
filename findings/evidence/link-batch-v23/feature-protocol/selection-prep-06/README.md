# Selection collector preparation 06 (uncounted): first S4 cells

Uncounted Chrome preparation of one S4 cell per interaction method, after the S4 source unit `8189da20`. Receipt `runner.command.json` (exit 0, 50 s); all three cells PASS on the first execution.

| Cell | Method | First key | Step outcome | Final text (native, 3/3) |
| --- | --- | --- | --- | --- |
| `inter-Shift+Right-a` | trusted click at p2.10, bound to the product's own `placeCaret` (route `click`, range open) | Shift+Right selects `T` | collapsed at p2.10, empty | Shift+Home → `P3 plain p` |
| `inter-Shift+Down-b` | trusted drag p1.3→p1.8 (shared drag witness) | Shift+Down | `ALPHA` | `ALPHA` |
| `inter-Shift+End-c` | public `selectRange` p1.20→p1.25 | Shift+End | `DELTA` | `DELTA` |

Because they were green on first contact, red cases were built from these real pages before anything else (`tests/test_v23_feature_selection.py` `InteractionControls`). Each edits the page record, call result and wire reply consistently, and each must hit its own clause.

- FAIL: final text after Shift+Home altered; the click leaving the range open; drag step text altered; settled select-range text altered.
- NOT_ESTABLISHED: untrusted click; untrusted drag; click request one twip off the pointer; select-range payload altered; no Shift extension before the step; readback 400 ms earlier; an unowned extra move request.

33/33 tests pass. This is one uncounted cell per method in one browser and establishes no S4 result. Raw cells are stored as deterministic `.json.gz`.
