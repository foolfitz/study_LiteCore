# K for host 0.2.45: preparation (2026-11-02)

Spec `specs/SPEC-M3-K-0.2.45.md`, results in its section 11. The owner chose A on the C2 gate: `boundaries` commit <= 16 ms, on-screen gates unchanged.

- **Tools** (`derive_k_tools.py`): closed list, each replacement must match its count. `tools/run_k_0245_path.py` is hand-written, a thin wrapper.
- **Census** (`census_old_identity.py`, `census.json`): walks the chain's import closure. Found the two `SHELL_MANIFEST` pins.
- **Repin** (`repin_0245.py`, `repin-0.2.45.json`): 25 sites in 11 files. Fewer pins than 0.2.44's 22 because the narrow session did not move.
- **Live-bound set** (`live-bound-set.json`): 50 paths unmoved, `--flip` red.
- **Counted paths** (`counted-paths/`): 34/34.
- **T1 under the new gate** (`t1-under-gate-16/`): holds; at 10 it gives the two FAILs T1 recorded.
- **M8** (`m8-fix/`): the widened match and its red cases.
- **Pre-chain** (`pre-chain.sh`, `pre-chain-log.txt`): gate negative, Enter replay, merge smoke, path smoke. `path-smoke-*.exit.txt` is 1 by design: the runner exits on the cells the K table reads by their own rule. Read `path-smoke/equal.json`: `F3_83_EQUAL`, 46/46 both browsers.
- **Readers** (`readers/`): merge 13/13 red, path 16/16 red.
- **Counted dry run** (`counted-dry-run/`): the real runners in counted mode. Not K. `first-attempt/` is the run that caught N9.
- **Preflight** (`preflight-only.txt`): only P5, the owner's word.

Start it from a file, not a heredoc: runners wait while another runner's name is on any command line.

    cd /home/jiajun/LibreOffice/study_LiteCore
    setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.45/chain-0.2.45.sh --owner-window "<the owner's words>" > /dev/null 2>&1 &

Read with `bash findings/evidence/m3-production-ui/runs-0.2.45/read-0.2.45.sh <logdir>`.
