# Ruling request 4 (v22): the engine thread's stack size, and STACK_OVERFLOW_CHECK

**You decide both questions.** The owner sent them to fable (2026-10-19, 「兩個問題都發給fable」). Work read-only: read files, run read-only Python over the reports; start no browser, run no make or link, edit and commit nothing. The main session commits your reply verbatim as `review/ruling-fable-4.md`, checks your numbers, and carries out what you order.

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. Read `CLAUDE.md` 「驗收判準的形式」 §1–§11 first.

## Context

- 0.2.26 (engine v21) is the nominal shipped version; its count held on 2026-10-19 (`findings/evidence/m3-production-ui/RESULT-0.2.26.md`).
- The owner chose next-link order **C** on 2026-10-17 (handoff 10-17b, "Next" 7). **v22 changes one variable: the engine thread's stack size** (finding 153). Item 2's re-enable (Markdown paste), fix 3 (finding 152) and finding 154's page-side rule ride along in the shell, after the link.
- The link is the owner's step. The v22 spec is not written yet. It waits on your ruling, because finding 153's criteria 2 and 3 must be settled before the link.

## F-claims (check each)

- **F1. Finding 153's criteria for this batch** (`findings/153-one-long-paragraph-overflows-the-engine-thread-stack.md`, section 「下一批的判準」):
  1. the four failing inputs complete normally, N=3, both browsers;
  2. the stack size comes with a reason (from a measured nesting depth or the native setting), and its memory cost is measured (about 7 threads × each thread's stack);
  3. whether to turn on the overflow check (`STACK_OVERFLOW_CHECK`) is decided, with its cost written;
  4. if not done, item 2 stays withheld and the release text carries a sentence. That sentence is now in `handoff/RELEASE-TEXT-0.2.25-0.2.26.md` §4.1.
- **F2. Where the value lives.** The link macro `link_r5_product` (`wasm_sdk_probe/Makefile:841-857`) passes:
  - `-sTOTAL_MEMORY=1GB` (no growth);
  - `-sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0`;
  - `-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536`;
  - `-sASSERTIONS=0`.

  Every product link uses this macro (v21 at `:1682`). Finding 153's README (`findings/evidence/link-batch-v21/shakedown/diag-long-paragraph/README.md` §"Why 64 KiB") traces the engine thread back to the default attribute: `std::thread` → `pthread_create(nullptr)` → `__default_stacksize`, set once by the loader from the link's value. It also notes that `STACK_OVERFLOW_CHECK` is 0 under `ASSERTIONS=0`.
- **F3. The measurement made today without a relink** (`findings/evidence/link-batch-v22/stack-size/README.md`, `c56be2ed`).
  - Method: the shipped v21 page and engine, with only the mirror loader's default pthread stack changed (page family `v21stack<N>`). Chrome only, N=1 per cell.
  - **Bisect** (`report-bisect1.json`) on 153's four inputs: 65,536 fails all four (crash, hang, crash, ok-then-crash); 131,072, 262,144, 524,288 and 1,048,576 pass all four.
  - **Headroom** (`report-headroom1.json`, `report-opentype1.json`): every size from 131,072 up passes both of these:
    - an `insertText` of 128/256/512 KB of CJK in one paragraph (about 28/56/112 pages);
    - opening a 28/56/112-page paragraph and typing one character at its start.

    65,536 hangs on the 28-page open-and-type.
  - So the measured need is above 64 KiB and at most 128 KiB, and it did not grow with length up to 112 pages.
  - **Not measured:** other recursion paths in the core (nested tables/lists/sections, deep XML import, other threads), Firefox, N>1, and the number of pthreads alive at once.
- **F4. Memory arithmetic** (not measured): 7 × stack is 448 KiB at 64 KiB; 0.9 / 1.75 / 3.5 / 7 MiB at 128 / 256 / 512 KiB / 1 MiB. That is 0.1–0.7 % of the fixed 1 GB heap.
- **F5. The order-C framing.** v22 "changes one variable" (handoff 10-17b, "Next" 7). Turning on `STACK_OVERFLOW_CHECK` in the same link would be a second engine variable.

## Options the owner was shown (the main session's lean marked)

**Q1, the stack size**
- **A, 1 MiB** (main session's lean). It is 8× the largest measured need and 1/8 of the native default. It leaves headroom for unmeasured recursion, and it is the counterfactual's value. About 7 MiB.
- **B, 256 KiB.** 2× the measured need, about 1.75 MiB. Unmeasured deep recursion is more likely to hit it.
- **C, 512 KiB.** 4× headroom, about 3.5 MiB.

**Q2, STACK_OVERFLOW_CHECK**
- **A, not in v22** (main session's lean). It keeps order C's one variable. It is registered as a named decision whose cost is unmeasured, to be decided after its own measurement. Until then an overflow still shows as a hang or a crash.
- **B, on in v22.** An overflow becomes a clean abort, but v22 changes two variables, and the code-size and speed cost is unmeasured.

## Questions

1. Which stack size, and what is the reason as finding 153's criterion 2 requires it? Is the memory cost satisfied by arithmetic, or must the number of live pthreads (or the heap actually used) be measured first? If measured, how, and is that measurement a precondition of the link or of the shakedown after it?
2. STACK_OVERFLOW_CHECK: on or off in v22, with the cost criterion 3 asks for written? If off, what is the named decision and its default if never revisited?
3. Do the measurements in F3 need anything more before the spec pins the value (Firefox, N=3, a size between 64 and 128 KiB, other inputs)? Say whether each is a precondition or belongs in the v22 shakedown after the link.
4. Anything in this brief that is wrong. Name it.
