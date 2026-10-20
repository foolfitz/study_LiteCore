#!/usr/bin/env python3
"""Finding 159's probe file: one sheet, one formula per candidate cause, saved by desktop
LibreOffice so every cell carries a cached value.  A second copy has =1+1's cached value edited
to 3 in content.xml: a viewer that shows 3 used the cache, one that shows 2 recalculated.

Usage: make_159_probe.py OUT_DIR   (writes probe-159.ods and probe-159-cache3.ods, prints the
desktop's own text of the sheet as the expected column)
"""
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import uno  # noqa: E402  (system python3-uno)

ROWS = [
    ("1+1 (control)", "=1+1"),
    ("SUM (control)", "=SUM(1;2)"),
    ("SERIESSUM add-in, numbers", "=SERIESSUM(2;3;2;3)"),
    ("MULTINOMIAL add-in, numbers", "=MULTINOMIAL(2;3)"),
    ("CONVERT add-in, unit text", '=CONVERT(10;"km";"mi")'),
    ("EUROCONVERT core, currency text", '=EUROCONVERT(100;"ATS";"EUR")'),
    ("TIMEVALUE 24h text", '=TIMEVALUE("16:00")'),
    ("TIMEVALUE 4PM text", '=TIMEVALUE("4PM")'),
    ("TIMEVALUE 6:45 PM text", '=TIMEVALUE("6:45 PM")'),
    ("DATEVALUE ISO text", '=DATEVALUE("2001-01-01")'),
    ("DATEVALUE en-US text", '=DATEVALUE("01/01/2001")'),
    ("VALUE 1.5", '=VALUE("1.5")'),
    ("VALUE 1,5", '=VALUE("1,5")'),
    ("COUPDAYS add-in, date serials", "=COUPDAYS(DATE(2001;1;25);DATE(2001;11;15);2;1)"),
    ("ACCRINT add-in, date serials", "=ACCRINT(DATE(2001;3;1);DATE(2001;8;31);DATE(2001;5;1);0.1;1000;2;0)"),
    ("implicit text to number", '="3"+1'),
    ("TEXT format", '=TEXT(1234.5;"0.00")'),
    ("DATE serial", "=DATE(2001;1;1)"),
    ("YEARFRAC core, dates", "=YEARFRAC(DATE(2001;1;1);DATE(2001;7;1);1)"),
    ("MINUTE of TIMEVALUE 6:45 PM", '=MINUTE(TIMEVALUE("6:45 PM"))'),
]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def prop(name, value):
    p = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    p.Name, p.Value = name, value
    return p


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    soffice = shutil.which("soffice")
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="probe-159-lo-") as profile:
        proc = subprocess.Popen([soffice, "--headless", "--nologo", "--nodefault", "--nofirststartwizard",
                                 "--norestore", f"-env:UserInstallation={uno.systemPathToFileUrl(profile)}",
                                 f"--accept=socket,host=127.0.0.1,port={port};urp;StarOffice.ServiceManager"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            context = None
            for _ in range(120):
                try:
                    context = resolver.resolve(f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext")
                    break
                except Exception:
                    time.sleep(0.25)
            desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
            doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (prop("Hidden", True),))
            sheet = doc.Sheets.getByIndex(0)
            sheet.Name = "Probe"
            for row, (label, formula) in enumerate(ROWS):
                sheet.getCellByPosition(0, row).setString(label)
                sheet.getCellByPosition(1, row).setFormula(formula)
                sheet.getCellByPosition(2, row).setString(formula)
            doc.calculateAll()
            texts = []
            for row, (label, formula) in enumerate(ROWS):
                cell = sheet.getCellByPosition(1, row)
                texts.append((label, formula, cell.getString(), cell.getError()))
            target = out / "probe-159.ods"
            doc.storeToURL(uno.systemPathToFileUrl(str(target)), (prop("FilterName", "calc8"),))
            doc.close(True)
            try:
                desktop.terminate()
            except Exception:
                pass
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
    for label, formula, text, err in texts:
        print(f"{label:34} {formula:70} -> {text!r} (err {err})")
    # The cache copy: =1+1's cached value becomes 3.
    src = zipfile.ZipFile(target)
    content = src.read("content.xml").decode("utf-8")
    needle = 'table:formula="of:=1+1" office:value-type="float" office:value="2"'
    if content.count(needle) != 1:
        raise SystemExit(f"cannot find =1+1's cached value exactly once: {content.count(needle)}")
    patched = content.replace(needle, 'table:formula="of:=1+1" office:value-type="float" office:value="3"')
    cache_target = out / "probe-159-cache3.ods"
    with zipfile.ZipFile(cache_target, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "content.xml":
                data = patched.encode("utf-8")
            dst.writestr(info, data, compress_type=info.compress_type)
    print(f"wrote {target} and {cache_target}")


if __name__ == "__main__":
    main()
