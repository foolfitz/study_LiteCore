"""Finding 112 / m3-locks rule 5.1: make the Files-row capture red once.
Non-counted: K5 with a row name that does not exist, so the wait times out."""
import sys
from pathlib import Path
REPO = Path("/home/jiajun/LibreOffice/study_LiteCore")
sys.path.insert(0, str(REPO / "wasm_sdk_probe" / "tools"))
import check_m3_locks as m  # noqa: E402

m.EVIDENCE = REPO / "findings" / "evidence" / "112" / "capture-red"
real = m.open_from_files


def absent_row(session, base, folder, name, record):
    record["deliberatelyWrongRowName"] = name[:-4] + "-absent.odt"
    return real(session, base, folder, record["deliberatelyWrongRowName"], record)


m.open_from_files = absent_row
sys.argv = ["check_m3_locks.py", "--label", "shakedown", "--repeats", "1",
            "--arms", "foreign-lock", "--browsers", "chrome,firefox"]
sys.exit(m.main())
