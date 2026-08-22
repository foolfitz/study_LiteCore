# Handoff: a11y gate 0 passed, and the screen reader can now read the paragraph

Written 2026-08-23, overnight, with the operator away and autonomy delegated.
Supersedes
[`HANDOFF-2026-08-22b-cut-arrows-and-the-ime.md`](HANDOFF-2026-08-22b-cut-arrows-and-the-ime.md)
as the entry point; that document remains the record of the ABI 4 round.

## State

| | |
|---|---|
| a11y gate 0 | **PASS**, three runs identical (`findings/evidence/a11y-gate-0/RESULT.md`) |
| §3.5 | **verified by measurement**, and it turned up a second lie one level down |
| §3.4 first increment | **G3.4-1 and G3.4-2 both PASS** (`findings/evidence/aria-projection/RESULT.md`) |
| screen-reader tree | 171 nodes / **0** carrying document text → 175 / **the focused paragraph** |
| product path | **38 checks, 35 PASS, `ok: True`** — nothing regressed |
| relink queue | 51 items, 14 open, **0 drifted**, blocking none |
| shell bundle | **v37**, `f9fcfb6b6409363d…`, frozen after the runs |
| product profile | `e2-editor-v4` untouched, byte-identical to its archive |

All static gates pass: `test-e2-c-static`, `test-e2-b-static`,
`test-e2-c-reachability`, the queue self-test, the E1-C bundle guard, 73 node
tests, 26 python tests. G3.4-1 was run **three times, identical**.

The new check's mutation was **run, not asserted**: `projection-not-wired`
takes `the-document-region-says-why-it-is-empty` PASS → FAIL with **exactly one
check moving**, observing `{present: true, text: ""}` — the region standing
empty, which is what a screen reader reads as "document, blank".

## What the operator decided, and what it bought

Two forks were put to them and both came back **B**:

* **core = `writer calc`**, accepting probe.wasm +19.9 MB rather than first
  measuring a writer-without-calc variant. This meant **no second core
  rebuild** — the gate build already on disk *is* the future product core.
* **text via the contract** (route B), not a shell-side ODT shadow.

Route B's marginal cost is near zero because the link was mandatory anyway: the
product core has to change, and `queue-fresh-is-true-where-no-read-can-succeed`
is waiting for the same ride.

## The three things worth carrying forward

**1. The control arm found the defect the gate would have shipped over.**
Gate 0's PASS needed a negative control — the same harness on the product
profile — and running it produced `enabled: false`,
`unavailable: "core-built-without-accessibility"`, which verified §3.5 by
measurement instead of by its own note. It also produced `paragraphFresh: true`
on a build where **no read can succeed**: every LOK entry point still exists on
a stripped core, `getA11yFocusedParagraph()` returns a well-formed empty answer,
and the parse's postcondition (`position >= 0 && contentLength >= 0`) accepts
it. `fresh` is the bit a consumer gates on. **The gate would have passed
without ever running that arm.**

**2. A check's first red is worth more than its pass, and this one was red in a
third place.** §3.4's first run reported one distinct reading and
`reason: engine` twice — where `engine` covered four causes at once. The defect
was in *the instrument*, not in a conclusion. Splitting the reason codes named
it in one run: `caretParagraph` absent. Then the real defect appeared —
**two writers set the page's `editorState` and only one had been fixed**. The
announcement MERGES, `editor-session.js` REPLACES with the `getState` reply, so
whichever landed last decided whether the projected name existed. Fixing both
took it 1/3 → 3/3.

**3. "Only a human can measure this" was wrong again, and narrowing it is the
reusable part.** The screen-reader question was answered with
`Accessibility.getFullAXTree` — the tree every AT consumes, built by the
browser, exposed by CDP. Same instrument for the before and the after, so the
171 → 175 comparison is one ruler and not two impressions. What genuinely stays
human is much smaller: **how one particular AT renders that tree** —
announcement order, verbosity, browse mode. That is the second time in three
days (finding 073's IME composition was the first).

## The artifacts, and which identity binds to what

| profile | wasm | what binds to it |
|---|---|---|
| `e2-editor-v4` | `f923cfa5…` | the product; untouched, byte-identical to its archive |
| `a11y-gate0` | `7dddbc6e…` | gate 0's PASS and the 171-node baseline. **Archived** before the engine changed |
| `a11y-projection` | `23233fa7…` | §3.4's G3.4-1/G3.4-2 result. A development artifact, **not** the product |

`a11y-projection` is deliberately not called `e2-editor-v5`: minting the
product's successor identity before the thing it exists for is validated is how
a generation gets frozen with work still to come.

## Open work, in the order I would take it

1. **`queue-product-page-holds-the-raw-editor-state`.** The additive mitigation
   is in and it is *not* the fix: `editorGetStateV2` still bypasses the
   product projection, and the page still holds `a11y` counters and
   `schedulerProbe`, which E1-B bans. Wants a round that can measure what
   removing them breaks.
2. **The product relink** (`e2-editor-v5`): the a11y core, the paragraph-text
   field, and `queue-fresh-is-true-where-no-read-can-succeed` all ride it.
   Note it costs the shipped artifact +19.9 MB, which lands squarely in M2a's
   lap.
3. **`queue-a11y-prefix-swallows-the-paragraph`** — one hypothesis was
   eliminated for free (our parse is faithful; the text LOK carried is the
   heading's own). The native build is still the discriminator.

## Two questions only the operator can answer

* **The accessibility standard and level** actually required of Taiwanese
  public-sector procurement. Roadmap §3.6's completion criterion is still blank
  **on purpose** — inventing one without a basis is worse than leaving it
  empty. It decides whether §3.4 stops at the focused paragraph or has to reach
  browse-mode navigation, which are two different orders of magnitude.
* **Whether the +19.9 MB is acceptable**, now that it is the price of a11y
  rather than a hypothetical. The writer-without-calc variant was declined for
  this round; it remains the cheaper option if M2a needs it back.

## Commands

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe

make test-e2-c-static && make test-e2-b-static && make test-e2-c-reachability
python3 tools/check_relink_queue.py && python3 tools/check_relink_queue.py --self-test
node --test editor-shell-v2/tests/*.test.mjs
python3 -m unittest tests/test_product_path_mutations.py tests/test_e2_editor_v4_profile.py

# the projection, both halves -- Chrome only, the AX tree is a CDP domain
python3 tools/probe_aria_projection.py --browser chrome --profile a11y-projection
python3 tools/probe_aria_projection.py --browser chrome --profile e2-editor-v4

# a11y gate 0, if it ever needs re-running
python3 tools/probe_a11y_gate0.py --browser chrome

# the product path -- detach it, and nothing else may run alongside:
# it has timing-sensitive terms and a loaded machine measures the machine
TMPDIR=/home/jiajun/.cache/litecore-probe-tmp setsid nohup \
  python3 tools/run_e2_c_product_path.py --browser chrome --out <path> \
  > <log> 2>&1 < /dev/null &
```

## One operational note

`pgrep -f` and `pkill -f` match **the checking command's own command line**.
This cost three false "still running" reports and one shell killed mid-script
in a single session. Match on the binary (`pgrep -f "em\+\+"`) or check for the
output file instead.
