# host_batch6.py's `landed` half, found vacuous on the red run

`probe_landed.py` ran once on the installed 0.2.53 (2026-11-03 ~14:00, Chrome, `python3 -I probe_landed.py <scratch out dir>` with `host-stack/bin` first on PATH; run from the session scratchpad, moved here after; its stdout is `probe-landed.stdout.txt`, copied from the terminal). It imports `host_batch6.py` as it stood before the route fix and uploads the cell-editing fixture, opens it, then reads `location`.

The editor is at `/index.php/apps/litecore/r/89860962782b3a21-90d7bc2c/ods-editor.html`: the route redirects to a versioned path. The old predicate (`pathname.endsWith('/apps/litecore/r/ods-editor.html')`) reads false on it, and the wait returns `{"timedOut": true}`, which `bool()` took as landed. The fix is in `host_batch6.py`'s docstring.
