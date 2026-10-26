#!/usr/bin/env python3
"""Correct the report-root prefix in the storage-index mapping only."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "findings/evidence/link-batch-v23/feature-pre-red"
OUT = BASE / "counted-05"
summary_path = OUT / "cohort-summary.json"
runner = json.loads((OUT / "report.json").read_text())
index = json.loads((BASE / "storage-index-03.json").read_text())
summary = json.loads(summary_path.read_text())
if summary["status"] != "FAIL" or summary["problems"] != ["storage index differs from completed raw cohort"]:
    raise SystemExit("initial summary differs from expected path-normalization-only failure")
rows = {row["path"]: row for row in runner["runs"]}
payloads = {row["path"]: row for row in index["payloads"]}
expected_paths = {"counted-05/" + path for path in rows}
path_match = set(payloads) == expected_paths
sha_match = path_match and all(payloads["counted-05/" + path]["sha256"] == row["sha256"]
                               for path, row in rows.items())
report = index["reports"]
report_sha = hashlib.sha256((OUT / "report.json").read_bytes()).hexdigest()
report_match = len(report) == 1 and report[0]["path"] == "counted-05/report.json" and report[0]["sha256"] == report_sha
corrected = {"pathPrefix":"counted-05/", "runnerRunCount":len(rows), "storagePayloadCount":len(payloads),
             "expectedPayloadPathCount":len(expected_paths), "pathsMatch":path_match,
             "rawShaMatchesRunnerRows":sha_match, "reportIdentityMatches":report_match,
             "packCommandExit":json.loads((OUT/"storage-pack.command.json").read_text())["exitCode"],
             "verifyCommandExit":json.loads((OUT/"storage-verify.command.json").read_text())["exitCode"]}
if not (path_match and sha_match and report_match and len(rows)==32 and len(payloads)==32 and corrected["packCommandExit"]==0 and corrected["verifyCommandExit"]==0):
    raise SystemExit(json.dumps(corrected, sort_keys=True))
summary["storage"].update({"pathsMatchReportSet":True,"shaMatchesRunnerReport":True,
                           "indexRelativePathPrefix":"counted-05/","prefixCorrection":"Runner report paths are cohort-local; storage index paths are rooted at its evidence base."})
summary["problems"]=[]; summary["status"]="PASS"
summary["summaryCorrection"]="The initial summary-only FAIL compared cohort-local runner paths with evidence-rooted storage-index paths without the `counted-05/` prefix. The packer and verify command both exited 0; corrected path+SHA mapping passes. Initial summary retained as cohort-summary-initial-path-check.json."
summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
correction_path=OUT/'storage-path-correction.json'
if correction_path.exists():raise SystemExit('refusing overwrite storage-path-correction.json')
correction_path.write_text(json.dumps(corrected,indent=2)+'\n')
print(json.dumps({"status":summary["status"],"correction":corrected},indent=2))
