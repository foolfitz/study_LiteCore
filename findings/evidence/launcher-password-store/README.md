# The shared Chrome launcher gets `--password-store=basic` (2026-10-22)

SPEC-M3-production-ui §17.27 (prediction, written before the change and before W1/W2).

| file | what |
| --- | --- |
| `refusal-2026-10-22.txt` | The forcing run: after the 08:04 reboot nobody is logged into the desktop, `org.freedesktop.secrets` does not exist, and `run_ods_viewer_phase_e.py` refuses (the wallet reading is an error string, not `b false`). |
| `w0-dump-dom.sh`, `w0/`, `w0-run2/`, `w0-run3/` | W0, paired, 3 runs each: the launcher's flags plus `--dump-dom` of a page on 127.0.0.1, fresh profile per arm. Default flags: page reached after 25.38 / 25.28 / 25.28 s (the D-Bus default timeout is 25 s). Only `--password-store=basic` added: 0.31 s every time. No wallet service running before or after any arm. |
