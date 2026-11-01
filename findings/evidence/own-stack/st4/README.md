# ST4 of SPEC-M3-own-stack (2026-11-01 ~22:06 +0800)

The reason for the move. `run_st4.py` polled the own stack while the real `ddev` started and stopped a project. `reading.json`: **`ST4_HOLDS`**. `self-test.json`: ALL_RED, 9 mutations.

| poller | polls | outcomes |
|---|---|---|
| own stack, `status.php`, every 250 ms | 219 | 200 x 219 |
| own stack, DAV PROPFIND (touches the database), every 1 s | 45 | 207 x 45 |
| **ddev's side**, `litecoreprobe.ddev.site:8443`, every 500 ms | 114 | 404 x 66, 200 x 46, connection refused x 1, connection reset x 1 |

The third row is the control, and also the disease: ddev's router went down during `ddev start` (`200 -> refused -> reset -> 200` in about three seconds) and then answered 404 after the stop. The own stack did not notice.

Steps, all exit 0: `ddev start litecoreprobe` 14.2 s, `ddev stop litecoreprobe` 1.8 s, `ddev stop litecore` 1.0 s. The last is the command that removed a stack container in the rehearsal, when the web image still carried ddev's labels. `litecore` is stopped, so it said so and did nothing.

The three stack containers have the same ids and start times before and after. `docker ps --filter label=com.ddev.platform=ddev` lists `ddev-router` and `ddev-ssh-agent`, not the stack. `litecoreprobe` was `running` during and `stopped` after. The dead port read as an error in the same poller.

None of the owner's other projects was started or stopped. `ddev-router` restarted, as ddev does; nothing else was running on it.
