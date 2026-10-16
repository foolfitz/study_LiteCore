# Item 2: the Chrome re-smoke of M6, M3, M11 and M5 after the fixes (rerun-1)

**A smoke, a development run: never judged as evidence.** Runner as committed in `9d3f568a` (`runnerSha256` `0958d87e…`) [observed], Chrome, N=1, arms `m6,m3,m11,m5`, under the S-9 lock (02:25:54 to 02:37:57, 2026-10-17), KWallet `b false`, load average 0.16 [observed `preRun`]. It re-runs the arms whose runner or judge faults the first smoke showed (`../README.md`, R1 to R5 and J1). `shape-check.txt` is the judge's reading printed as a format check: the other criteria read "missing" because their arms were not run.

Labels: **[observed]** read from the report or a diagnostic's output, **[inferred]** reasoning.

## Outcome per arm

| arm | seconds | outcome [observed] | fault it re-checks |
|---|---|---|---|
| M6, alone in its own fresh browser | 16 | busy → ready **671 ms** (click → ready 677 ms, reply 645 ms), the textarea intact, S1 differs from R, one Ctrl+Z restores R | R4, J1: fixed. The 32 s and the SDK's 30 s `TIMEOUT` of the first smoke came with M6 run late in a long session; alone, the same corpus takes 0.67 s, as in dev-r1 (0.63 s) and the trace pass (0.66 s) |
| M3 (R-dialog, R-sdk) | 424 | all 56 cells as predicted; `round-1/M13.md` on R-dialog is now the session's refusal (`INVALID_ARGUMENT`, `recovery: none`, no request); `askMisses` empty | R1: fixed. R2: did not recur |
| M11 | 11 | dirty and cancel as in the first smoke; the textarea read `focusBeforeTyping: "markdown-text"` and still held 6 UTF-16 units / 10 UTF-8 bytes, `typedAsArm: false` | **R3: not fixed by waiting for the focus** (see below) |
| M5 (proxied Chrome, background networking off) | 266 | the `probe.wasm` positive control and the `/m5-control` control as before; every cell refused with its M3 code; nothing reached a target or a listener. **6 of 38 windows still hold Chrome's own requests**: `mtalk.google.com:5228` (GCM), `android.clients.google.com:443` | R5: reduced (the component updater and safe browsing are gone), **not removed**: see below |

## R3, diagnosed (development diagnostics, under the lock, not evidence)

`diag-keys.py` opens the dialog and types `# 打字 ABC` one key at a time, reading `#markdown-text.value` after each. With S-4's `v21_input.key` (the first version of the script: the same file with `inp.key` in place of `run.type_char`, once typing at once and once after a 1 s pause) the value after `#` was `""` in both, and every later key arrived [observed: `" "`, `" 打"`, … `" 打字 ABC"`]. So `#` is dropped whatever the timing. Cause [source `wasm_sdk_probe/tools/v21_input.py` `_cdp_params`]: a character that is not a letter or digit is sent with the Windows key code `ord(ch.upper())`, which for `#` is 35, End; the keydown runs as End and Chrome drops the character [inferred]. `v21_input.py` is item 1's file and is not edited here (item 1 should know: a `#`, `$`, `%`, `&` or `'` typed through it in Chrome sends End, Home, ArrowLeft, ArrowUp or ArrowRight). The item-2 runner now sends such characters as a CDP `keyDown` with `text` and no key code (`type_char`); with it the same diagnostic read `#`, `# `, `# 打`, … `# 打字 ABC` [observed, the kept `diag-keys.py`]. The fix is committed after this folder.

## R5: the arm cannot be met as written in Chrome (for the main session)

ARMS-item2 M5 reads "0 requests and 0 connection attempts … to any origin other than the mirror's" in each item's window, with every request forced through the proxy (ruling DM-12). Headless Chrome's own services keep connecting through that proxy:

- the first smoke, without quieting: component updater, GCM, safe browsing, 58 requests to Google hosts in the pass [observed];
- this re-smoke, with `--disable-background-networking`, `--disable-component-update`, `--disable-sync` and the rest of `v21_network.QUIET_CHROME`: GCM `mtalk.google.com:5228` and `android.clients.google.com` remain, in 6 of 38 windows [observed];
- `diag-quiet.py` (page loaded and idle for 3 × 25 s) with `--disable-extensions --disable-component-extensions-with-background-pages --disable-notifications --no-service-autorun --disable-search-engine-choice-screen` added: still `mtalk.google.com:5228` ×3, `android.clients.google.com` ×2, `www.google.com` ×3, `www.gstatic.com` ×2, `accounts.google.com`, `clients2.google.com` [observed]. A Chrome policy that turns these off needs root (`/etc/opt/chrome/policies`), which is the owner's.

None of these was to an item's target [observed]. The CDP record of the page and its workers keeps the last 400 requests, and all 400 are to the mirror [observed]; that the Google hosts come from Chrome's services and not from the page is [inferred] from the hosts. The spec's verbatim criterion is "對目標主機 0 個請求" (0 requests to the target hosts). Which reading the M5 judge takes is the main session's ruling, not the runner's. The judge is unchanged and would read FAIL here.
