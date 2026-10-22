# The shared Chrome launcher gets `--password-store=basic` (2026-10-22)

SPEC-M3-production-ui §17.27 (prediction, written before the change and before W1/W2).

| file | what |
| --- | --- |
| `refusal-2026-10-22.txt` | The forcing run: after the 08:04 reboot nobody is logged into the desktop, `org.freedesktop.secrets` does not exist, and `run_ods_viewer_phase_e.py` refuses (the wallet reading is an error string, not `b false`). |
| `w0-dump-dom.sh`, `w0/`, `w0-run2/`, `w0-run3/` | W0, paired, 3 runs each: the launcher's flags plus `--dump-dom` of a page on 127.0.0.1, fresh profile per arm. Default flags: page reached after 25.38 / 25.28 / 25.28 s (the D-Bus default timeout is 25 s). Only `--password-store=basic` added: 0.31 s every time. No wallet service running before or after any arm. |
| `test-e2-c-static-after.txt` | After the change (`b9a76b8a`): exit 0. |
| `compare_w2.py`, `compare-w2-selftest.txt` | W2's comparator, the mask pinned in §17.27, and its red cases (one sha changed: 1 difference; one masked field changed: 0). |
| `w1-wallet-state.txt` | W1: the wallet's D-Bus state before and after the targeted Phase E on `e96e01ec` (report in `findings/evidence/m4-ods/viewer-v2/fallback-phase-e/`): unchanged, nothing woken, 0 Chrome processes before and after. |
| `w2/` | W2: the 10-21 v1 shakedown set re-run under the flag; `compare-w2.txt`: 0 differences against `findings/evidence/m4-ods/viewer-v2/pre-link/v1-shakedown-new-shell/report-2026-10-21T023626Z.json` (flagless, wallet `b false`). 31.8 s (then 33.8 s). |

Result: SPEC-M3-production-ui §17.28 -- W1 and W2 hold.
