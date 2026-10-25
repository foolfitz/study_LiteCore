#!/usr/bin/env python3
"""Run existing cell-input/format/save checks against the built successor."""
import run_calc_editor_browser as browser
from probe_calc_range_format import mirror

if __name__=='__main__':
    browser.mirror=mirror
    raise SystemExit(browser.main())
