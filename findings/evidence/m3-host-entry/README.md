# M3 host entry — evidence

Criteria: `specs/SPEC-M3-host-entry.md` §4. Verdict: `RESULT.md`, from
`wasm_sdk_probe/tools/check_m3_host_entry.py --score runs/2026-09-28T095100Z.json`.

| path | what |
| --- | --- |
| `RESULT.md` | The result, how it got there (two wrong turns), named limits. |
| `runs/` | Counted run (`--label counted`: 3 per arm per browser, refuses a dirty app tree, a dist page that differs from `web/`, or a served shell that is not a frozen generation). |
| `shakedown/` | Never counted. `092749Z`: H2 red on the `<text:h` oracle, both browsers. `092945Z`: Chrome open-save only, with the style payload that showed `Heading_20_1`. `093031Z`: first all-arm pass, dirty app tree. `093154Z`: clean. `094839Z`: after the review's changes (page, host, runner); the base of `--red-cases` (21/21 red). |
| `product-path/` | H4: `run_e2_c_product_path.py --browser chrome` on the final page, shipping v8 and `--profile e2-editor-v14`, each 40 PASS / 2 NE, the same cells as v52's. `superseded/` holds the same net on the first page draft (also 40/2), before save serialization changed the page again. |

## 2026-09-29: the runner on a locking host

From host `49cc4ab` the host takes a WebDAV token lock, and this runner could no longer run:
it closed the browser without leaving the page (its own lock stayed until it lapsed, ~306 s,
and its next reset upload got 423), and the conflict arm's intruder — a PUT without the lock
token — was refused with 423, so no conflict could be made. Changed in
`SPEC-M3-install-elsewhere.md` §3.4, criteria H1–H3 and H5 unchanged:

- every arm goes back to Files before the browser closes, then polls `nc:lock` for 10 s
  (recorded with the PROPFIND status, not scored); a lock found at a reset is recorded and
  cleared from the database;
- the conflict intruder is **admin, the same user as the page**, writing with its own lock
  token from another client (read from `lockdiscovery`). That is a legitimate WebDAV write
  (RFC 4918 §6.4), not finding 102 (which is about a *different* user using the token);
- H3 is pinned to the branch it now measures (`intruder.mode = "lock-token"` in the report):
  intruder 2xx with a token, each save exactly one PUT `(412, with token)`, `tokenOnServer`
  true. New red cases `H3-intruder-refused`, `H3-lock-died`.

Keeping H3 rather than retiring it (as `SPEC-M3-locks-and-permissions.md:94` had recorded) is
fable's ruling on the owner's authority: H3's "second press after a conflict" has no
counterpart in locks K6/K12 or versions step 6. Ruling and conditions:
`../m3-install/ruling-2026-09-29-fable-h3.md`.
