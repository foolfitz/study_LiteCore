# A real php-fpm worker, driven over FastCGI: where its background child goes, what it holds open

2026-09-29, litecoreprobe, outside any window (no window has run since the second review).
Asked by review 2, items 4 and 14: I2-3 has no control on the php-fpm path, and "no subreaper
in the container" (spec §3.5, I4-1b) was inferred, not measured.

## Method

No HTTP request, no file in the docroot: a 25-line FastCGI client run with the container's PHP
CLI (`docker exec … php fcgi.php <script>`) connects to the pool socket
`/run/php/php-fpm.sock` (`listen.mode = 0666`, pool `www`, no `open_basedir`,
`security.limit_extensions` not set) and asks the pool to run a script under `/tmp`. The
script therefore runs inside an ordinary `php-fpm: pool www` worker, the same kind of process
that runs every app request.

The script (`/tmp/lcsub/lcsub.php`):

    <?php
    $f = fopen('/mnt/litecore-dist/e2-editor.html', 'r');
    exec('/tmp/lcsub/lcsleep 8 > /dev/null 2>&1 &');
    sleep(3);
    fclose($f);
    echo "worker ", getmypid(), "\n";

`/tmp/lcsub/lcsleep` is a copy of `/bin/sleep`. The client (`/tmp/lcsub/fcgi.php`) is the
`FPM_CLIENT` text as later embedded in `check_m3_install_elsewhere.py` if the ruling adopts it;
until then it lives only in this session's scratchpad and the listing below.

## Output (verbatim)

    --- +1s
      38457    1600 php-fpm         php-fpm: pool www
      38543    1600 php-fpm         php-fpm: pool www
      38723    1600 php-fpm         php-fpm: pool www
      39277    1600 php-fpm         php-fpm: pool www
      40496       0 php             php /tmp/lcsub/fcgi.php /tmp/lcsub/lcsub.php
      40503       1 lcsleep         /tmp/lcsub/lcsleep 8
    /proc/38723/fd/7
    /proc/40503/fd/7
    --- +5s
      40503       1 lcsleep         /tmp/lcsub/lcsleep 8
    /proc/40503/fd/7
    end
    --- client output
    Content-type: text/html; charset=UTF-8

    worker 38723

(`ps -eo pid,ppid,comm,args | grep -E "lcsleep|php-fpm: pool|lcsub"` and
`find /proc/[0-9]*/fd -lname "*litecore-dist*"`, run with `docker exec` at +1.2 s and +4.7 s.)

## What it shows

1. **A background child of a php-fpm worker is reparented to PID 1 at once.** At +1.2 s
   `lcsleep` already has ppid 1; the `sh -c` that `exec()` ran had exited. On this path there
   is no subreaper between the worker and PID 1 — measured, where spec §3.5 had inferred it.
2. **I4-1a alone would not have seen it.** The only moment `lcsleep` was a php-fpm descendant
   was the few milliseconds before `sh -c` exited. I4-1b (PID 1's descendants) is the rule that
   catches a backgrounded document server; this is the case review 1, item 1 argued from reading.
3. **The sampler sees a real worker's open file on the mount**: `/proc/38723/fd/7` is the
   worker holding `e2-editor.html` (uid 1000, same as `docker exec`).
4. **The orphan inherited the worker's open file**: `/proc/40503/fd/7` is still open in
   `lcsleep` after the worker closed its copy (PHP's `fopen` does not set `O_CLOEXEC`). A
   process the app backgrounds keeps whatever the worker had open.
5. The php-fpm master is pid 1600 (started `Mon Sep 28 13:50:33 2026`, two seconds after
   supervisord pid 16 and the container, `StartedAt 2026-09-28T05:50:31Z`); it is the same
   pid in all three shakedowns and in `install.json`'s baseline — the container has run
   continuously since before the first install. (A first draft of this line said the master
   had been restarted since the shakedowns; that was written without looking, and is wrong.)

Cleanup: `/tmp/lcsub` removed after the run (`ls: cannot access '/tmp/lcsub'`); `lcsleep`
exited by itself at +8 s.
