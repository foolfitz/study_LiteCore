# D5's machine half, re-run on shell bundle v7 (2026-08-16)

The same run as `../machine-half/`, on a different shell generation, kept beside
it rather than over it.

## Why

D5's two halves ran on different shells: the machine half on **v3
`34e95e10…`**, the four operator cells that established the phase on **v6
`9b7e7d2a…`** (findings 049 and 050 landed between them).  A phase whose halves
are bound to different generations cannot say "this is what that shell does",
and the machine half is the half that is automated — so it is the half that can
be re-run for free.

Since then finding 051 minted **v7 `e9668347…`**, so this run is on v7 and the
gap is now one generation for the operator cells rather than three.

## Result — unchanged, which is the point

| | v3 (original) | v7 (this run) |
|---|---|---|
| events recorded | 6 | 6 (chrome and firefox) |
| all `isTrusted` | false | false |
| every cell | `NOT_ESTABLISHED` | `NOT_ESTABLISHED` |
| run verdict | `PARTIAL` | `PARTIAL` |
| capture path exercised | yes | yes (1 document each) |
| shell bundle digest moved | no | no |
| analyzer self-test | 10/10 | **10/10, both browsers** |

A machine half that reached `PASS` would mean the harness had accepted a
synthetic gesture, which is the one thing D5 exists to make impossible.  It did
not, on either browser, on either shell.

## What this does NOT close

The four cells that carry D5's verdict were driven **by a person on v6**.  This
run does not move them; only another operator round can.  What it removes is the
weaker of the two mismatches — the automated half now sits on the current shell,
and what remains is a single named gap for the human half, not a spread of
three.

D3's corpus round and D4 also ran on v3.  Bringing every phase onto one shell is
round two's job, after the relink.

## Guard added while doing this

`tools/run_e2_c_d5.py` used to write `machine-half/<browser>/result.json`
unconditionally, and its default `--output` is D5's own directory — so this
re-run would have **replaced the v3 evidence a verdict cites**, with a result
bound to a different shell.  It now refuses unless `--allow-overwrite` is
passed.  Same rule, and the same day, as the session-attestation clobber
recorded in finding 051.
