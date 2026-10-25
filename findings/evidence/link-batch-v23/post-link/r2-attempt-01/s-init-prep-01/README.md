# S-init preparation 01: mirror construction refused before browser startup

Status: instrument construction failure, **zero browser cells**. This is not a v22/r2 product comparison or a counted S-init run. The runner exited 1 before acquiring the browser lock or running the CPU guard. The sibling `s-init-prep-01-runner.txt` preserves the traceback; `pre-browser-config.json` preserves the exact initial profile, resource, fixture and instrument identities.

The executed-source graph includes `input/clipboard-adapter.js`, imported transitively by the session. The mirror builder only linked the three SDK/session directories. Its existing full-graph verifier refused the missing file rather than accepting an unbound instrument. The correction makes mirror coverage follow the executable served-source graph, including future imported directories without a second directory inventory. A focused construction test reproduced this same missing-file error before the correction and passed afterward.

No artifact/profile bytes, shared SDK, service, host or live document changed. The partial mirror is retained locally and ignored in git. A fresh `s-init-prep-02` is required for the corrected instrument; this output is never overwritten or counted.
