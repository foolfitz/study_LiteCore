# D2 host arm: first contact with the host (2026-10-17)

One round per browser of `run_v21_d2.py --mode host --page 0224 --smoke --rounds 1`, on host 0.2.24, before the counted N=3 runs (`../../evidence/d2/d2-host-0224-*.json`). The handoff 10-17b said the arm had never run against the host and might expose route or timing issues.

- Chrome `d2-host-0224-chrome-20261017T153151.json`, Firefox `d2-host-0224-firefox-20261017T153239.json`, with their logs.
- Both: login 200, Files → open, `ready`; save 1 and save 2 `saved`; the red verdict; folder 201 / 204.
- No issue found, no tool changed. Not evidence; kept as the record that the route worked before the counted runs.
