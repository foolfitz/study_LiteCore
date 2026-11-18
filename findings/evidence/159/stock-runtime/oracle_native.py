#!/usr/bin/env python3
"""Finding 159 oracle: what desktop LibreOffice computes for every case in cases.json.

Starts the native soffice (whatever `soffice` is on PATH) headless with a throw-away profile, creates a Calc
document, sets every cell formula through XCell.setFormula (API grammar, the same strings the wasm probe's API path
uses), and reads back formula, error code, value and string. Writes JSON to stdout.

The direct cases are not called here: each names the cell ("oracle_cell") that computes the same function with the
same arguments. (Creating com.sun.star.sheet.addin.Analysis through the remote service manager ended the native
soffice process on the first try, "Binary URP bridge disposed during call"; not looked into.)

usage: /opt/libreoffice26.8/program/python oracle_native.py <cases.json>   (a Python with PyUNO; the system python3 is 3.14 and has none)
"""
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import uno


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def prop(name, value):
    p = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    p.Name, p.Value = name, value
    return p


def main():
    cases = json.load(open(sys.argv[1]))
    soffice = shutil.which("soffice")
    version = subprocess.run([soffice, "--version"], capture_output=True, text=True).stdout.strip()
    port = free_port()
    out = {"soffice": soffice, "version": version, "cells": []}
    with tempfile.TemporaryDirectory(prefix="oracle-159-lo-") as profile:
        proc = subprocess.Popen([soffice, "--headless", "--nologo", "--nodefault", "--nofirststartwizard",
                                 "--norestore", f"-env:UserInstallation={uno.systemPathToFileUrl(profile)}",
                                 f"--accept=socket,host=127.0.0.1,port={port};urp;StarOffice.ServiceManager"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            ctx = None
            for _ in range(120):
                try:
                    ctx = resolver.resolve(f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext")
                    break
                except Exception:
                    time.sleep(0.25)
            if ctx is None:
                raise SystemExit("could not connect to soffice")
            smgr = ctx.ServiceManager
            desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
            doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (prop("Hidden", True),))
            sheet = doc.Sheets.getByIndex(0)
            for row, c in enumerate(cases["cells"]):
                cell = sheet.getCellByPosition(0, row)
                cell.setFormula(c["formula"])
            doc.calculateAll()
            for row, c in enumerate(cases["cells"]):
                cell = sheet.getCellByPosition(0, row)
                out["cells"].append({"id": c["id"], "formula_set": c["formula"], "formula_read": cell.getFormula(),
                                     "error": cell.getError(), "value": cell.getValue(), "string": cell.getString()})
            doc.close(True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
