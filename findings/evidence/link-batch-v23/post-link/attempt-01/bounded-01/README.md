# Bounded v23 diagnostic cohort, 24 cells

The predeclared cohort ran once with the explicit v23 WASM SHA-256, the native `plain-grapheme.odt` fixture, both browsers, three rounds, and all four arms. The runner exited 0 and recorded all 24 cells with no fatal payloads. The existing aggregate judge reports `NOT_ESTABLISHED` with a complete population.

All 18 smoke, proof, and hang cells passed. All six js-thread cells returned `NOT_ESTABLISHED`: the page lacked a fresh-worker witness and a post-recovery save; the private hang did not reach the SDK timeout, the default timeout was not used, and the session did not enter recovery or restart. This same result occurred in all three rounds in both Chrome and Firefox.

See `report.json` for the complete raw browser observations, `aggregate-judge.stdout.json` for the full aggregate reader output, `verdicts.json` for each page verdict and failure reason, and `commands.json` for exact invocations and exit codes. The aggregate reader's remaining protocol scopes are listed in `verdicts.json`; this run does not close them.
