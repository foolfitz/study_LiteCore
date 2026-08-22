# The product-path mutation net was already red at HEAD (2026-08-21)

Six runs of `run_e2_c_product_path.py --browser chrome --mutate {save,ime,copy}`,
three with the **HEAD** runner (`git show HEAD:…`, i.e. the state before
2026-08-21 touched it) and three with the runner as it stands after this
session's changes. Same machine, same artifact `29ec627b`, same shell v25, run
back to back from one script, alternating so neither ordering could favour one.

**Why this exists:** this session rewrote how
`every-inline-format-reaches-the-document` reads its oracle and added a check.
When the mutation rounds came back failing, "I broke the mutation net" and "it
was already broken" were indistinguishable — and an earlier attempt to tell them
apart was itself void, because `/tmp` (a 16 GB tmpfs) hit 100% mid-run. These
six ran with `TMPDIR` on a real filesystem.

## The result

| mutation | HEAD | after this session | verdict |
|---|---|---|---|
| `save` | `ok: false` — NOT DETECTED | `ok: false` — NOT DETECTED | **already red** |
| `ime` | `ok: false` — NOT DETECTED | `ok: false` — NOT DETECTED | **already red** |
| `copy` | `ok: true` — detected | `ok: true` — detected | passes on both |

**No round's verdict changed.** The only checks this session's runner adds to a
failing list are `the-edit-buttons-do-what-they-say` (added earlier the same day
by the previous session, absent at HEAD) and
`formatting-survives-the-next-paragraph-break` (this session's, and declared
`KNOWN_RED`, which the verdict logic excludes from `others_ok` — so it cannot
flip a round, and `copy` passing on both proves that).

## Why `save` and `ime` fail at HEAD

Not because the mutation escapes detection — the owning check goes red in every
case. The rounds fail on the **declared-collateral** bookkeeping, which no
longer matches what the mutation actually knocks over:

* **`save`** reintroduces finding 049, so every save the page performs writes 15
  bytes of `[object Object]`. Every check whose oracle is a saved ODT must
  therefore fail, and three that do — `ctrl-v-reaches-the-document`,
  `product-opens-a-document-the-user-chose`,
  `the-keyboard-reaches-the-document` — are **not** in the spec's `alsoRed`.
  Separately, `notice-action-recovers-the-session` **is** in `alsoRed` but comes
  back `NOT_ESTABLISHED`, and the verdict logic correctly refuses to count a
  check that never ran as a detection.
* **`ime`** breaks the composition path in the input adapter;
  `the-keyboard-reaches-the-document` drives `beforeinput` through the same
  sink and goes red with it. Also not in `alsoRed`.

Both look like **product-topology coupling** — the kind this tree's own rule
says to *declare and machine-verify* rather than to untangle. But that judgement
has to be made per entry, by someone who looks at each collateral red and asks
whether it is structural or is a real defect surfacing. **Widening `alsoRed`
because a round is failing is exactly "fix the assertion when the setup is
wrong"**, and it is not done here for that reason.

## What this does not say

It does **not** say the mutation net is worthless: `copy` detects its mutation
cleanly on both runners, and in every failing round the owning check still went
red. What is broken is the round's ability to *report* a clean detection, not
its ability to detect.

It also does not date the breakage beyond "at or before HEAD". HEAD predates all
of 2026-08-21; when these rounds were last green is not established here.
