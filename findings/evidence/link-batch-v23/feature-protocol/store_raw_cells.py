#!/usr/bin/env python3
"""Reuse the tested lossless raw-cell store with paths rooted in this evidence directory."""
import importlib.util
from pathlib import Path

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parent/'feature-pre-red/store_payloads.py'
spec=importlib.util.spec_from_file_location('v23_existing_payload_store',SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.BASE=BASE

if __name__=='__main__':module.main()
