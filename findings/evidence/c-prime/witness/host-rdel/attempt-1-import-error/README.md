# Attempt 1 (2026-10-11T10:35:56Z) — did not measure anything

`run-host-rdel.sh` as it stood restored only `run_e2_c_page_smoke.py` to `08d73cff`. `check_m3_production_ui.py`
imports `check_m3_page_honesty.py`, whose HEAD (ported) version imports `DOC_WINDOW_JS` from the page smoke — a name
the pre-port file does not have — so the runner died at import (`pre-port-rdel.stderr.txt`), no browser started, no
report. The page smoke was restored by the script (`cc38ee97…`, `log.txt`). `witness/PREDICTION.md` names all three
pre-port runners at `08d73cff`; the script should have restored `check_m3_page_honesty.py` too. Attempt 2 does.
