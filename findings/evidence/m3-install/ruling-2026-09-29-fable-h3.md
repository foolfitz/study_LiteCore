# Ruling: keep host entry's H3 (fable, 2026-09-29, on the owner's authority)

The owner was away and had authorized fable to decide for them this round. The question, the
ruling and its conditions are below; the Chinese "WHY" is the ruling's own text, for the owner.
The main session re-checked F1 (the two commit times), F3 (`litecore-editor.js:381`, `:394`)
before acting.

## Question

Host entry's H3 (conflict: refused save, copy, no reload for 5 s, a second press refused
again) could no longer be produced once the host took a token lock (a tokenless intruder PUT
is 423). `SPEC-M3-locks-and-permissions.md:94` had recorded "宿主入口的 H3 被 K6 取代".
Option A: follow it, retire H3 from the host-entry runner. Option B: keep H3, the intruder
writing with the lock token. The main session leaned A, weakly.

## Ruling

**B** — keep H3 in the host-entry runner with a token-bearing intruder, with the rationale
corrected: the basis is same-principal WebDAV semantics (RFC 4918 §6.4), not finding 102; and
the scorer must pin the arm to the branch it claims.

## WHY (for the owner)

:94 那句「H3 被 K6 取代」是 2026-09-28 18:21 寫的（`6c0a3b66`），而 H3 的「再按一次」條款在 25 分鐘前（17:56，`1c0975a6`）就已經進了宿主入口規格；:94 只講了「入侵者怎麼寫進來」那件事，完全沒有提到第二次按。查下來，K6、K12 和版本那一步的第 6 步都只按一次存檔，所以「衝突之後再按一次仍然被拒、不會把別人的內容蓋掉」這件事目前只有 H3 在守——而且它守的是一個真實的洞：伺服器回 412 時會附帶一個 ETag（shakedown 裡的 `responseEtag` 就是），宿主現在只在成功時更新版本，但只要有人日後「順手」拿 412 的 ETag 來用，第二次按就會變成默默覆寫。選 A 的主要理由（「B 靠的是上游缺陷 102，上游修了就會紅」）查下來不成立：runner 的入侵者和頁面是同一個使用者 admin，持鎖的人自己帶 token 從別的用戶端寫入本來就是 WebDAV 允許的，102 修不修都不影響。至於「之後再把第二次按補進 K6 或 K12」，那是動一個已經落地的計數閘門，要重跑鎖與權限，比留在已經寫好、已經有紅案、已經在兩個實例上各過一輪的 H3 裡貴得多。

## Fact check (as returned)

- F1 TRUE. `SPEC-M3-locks-and-permissions.md:94`, written in `6c0a3b66` (2026-09-28 18:21 +0800), after the second-press clause entered H3 in `1c0975a6` (17:56).
- F2 TRUE. K6 (`:84`) and K12 (`:90`) each have one save (runner `check_m3_locks.py:501`, `:519`; scorer `:802`, `:831`); versions step 6 (`SPEC-M3-versions.md:60`) is a single 412 save. No second press anywhere but H3.
- F3 TRUE. `put()` sends `If-Match` and `If: (<token>)` (`litecore-editor.js:344-345`); `saveOnce()` resends only on `tokenOnServer === false` (`:365-371`); `etag` is set only on success (`:381`); `responseEtag` (`:394`) is recorded and never read.
- F4 TRUE. Both shakedowns' conflict arms: intruder 204 with an `opaquelocktoken:` token, each save one attempt `(412, withToken)`, `tokenOnServer` true, server file = intruder bytes, two copies matching the two saves.
- F5 TRUE, with a consequence the draft missed: the intruder is the page's own user (admin); finding 102 is about another user. Same principal + own token is what RFC 4918 §6.4 requires a server to accept; a fix of 102 would not touch this path.
- F6 FALSE. The handoff's "host entry's only check not covered elsewhere is H5" is wrong: H3's second press, and H2's "the heading is really on the server" (no `Heading`/`text:h` check in the locks or versions runners), are not covered elsewhere.

## Conditions, and what was done

1. Do not edit `SPEC-M3-locks-and-permissions.md:94`; append a dated revision row saying :94 stands for the locks gate and is superseded for the host-entry runner. — **Done** (top of that spec's revision table).
2. Correct the install-elsewhere spec §3.4: same principal, not 102; K12 and versions step 6 do reach `tokenOnServer true`, what only H3 has is the second press; record the ETag-on-412 hazard. — **Done** (struck-through originals kept).
3. Pin `h3()`: intruder 2xx with a token; each save exactly one attempt `(412, withToken)` and `tokenOnServer` true; a refused intruder is named as such. — **Done**, applied when the report's `intruder.mode` is `lock-token` so stored pre-lock reports score as before.
4. Red cases `H3-intruder-refused` and `H3-lock-died`, red before the counted run. — **Added**; shown red on the dev shakedown made with the pinned runner (see README).
5. Runner header, host-entry evidence README and the spec: the intruder is admin, the page's own user. — **Done.**
6. Counted run on the dev instance after 1–5. — Part of this step (spec I3-7).
7. Correct the handoff's option E statement in the next handoff. — To do at hand-off.
