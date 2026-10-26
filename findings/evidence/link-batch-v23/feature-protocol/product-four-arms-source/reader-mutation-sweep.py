#!/usr/bin/env python3
"""Disable one defining check of the four-arm reader at a time, in a temporary copy, and require
the matching control in wasm_sdk_probe/tests/test_v23_product_four_arms.py to go red.

The reader in the tree is never edited.  Exit 0 only when every disabled check is caught.
Run from anywhere:  python3 reader-mutation-sweep.py
"""
import importlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

PROBE = Path(__file__).resolve().parents[5] / "wasm_sdk_probe"
JUDGE = PROBE / "tools" / "judge_v23_product_four_arms.py"
sys.path.insert(0, str(PROBE / "tools"))
sys.path.insert(0, str(PROBE / "tests"))

C, H, N = "CausalControls", "HoldContradictions", "NeverStopsTheRunner"
MUTATIONS = [
    ("contradict(growth <= bound,", "contradict(True or growth <= bound,", f"{C}.test_release_bound_violated"),
    ('need(all(i.get("isTrusted") is True for i in measured)', "need(True",
     f"{C}.test_synthetic_input_instead_of_trusted"),
    ('contradict(first["seq"] < move["seq"],', "contradict(True,", f"{C}.test_swapped_immediate_request_order"),
    ('need(any(k.get("repeat") is True for k in downs),', "need(True,", f"{C}.test_all_repeats_removed"),
    ('need(len(requests) == len(admissions), "an admitted extension or edit has no wire request")',
     'need(True, "an admitted extension or edit has no wire request")', f"{C}.test_omitted_pending_request"),
    ('need(len(requests) == len(admissions), "an admitted extension or edit has no wire request")',
     'need(True, "an admitted extension or edit has no wire request")',
     f"{H}.test_an_admission_never_posted_is_not_established"),
    ('need(start >= previous, "overlapping', 'need(True, "overlapping', f"{C}.test_stolen_adjacent_same_clock_request"),
    ("if identity_key in opens.values() or", "if False and identity_key in opens.values() or", f"{C}.test_copied_round"),
    ("            if ready is None:\n", "            if False:\n", f"{C}.test_removed_readiness_mutation_or_save"),
    ('contradict(mp.get("extendSelection") is True', 'contradict(True or mp.get("extendSelection") is True',
     f"{C}.test_public_extension_flag_absent_on_the_wire"),
    ('need(arms.digest(raw) == save.get("sha256")', 'need(True or arms.digest(raw) == save.get("sha256")',
     f"{C}.test_corrupt_raw_save"),
    ('contradict(witness["paragraphs"] == expect["paragraphs"],', "contradict(True,", f"{C}.test_wrong_saved_content"),
    ('need(ua_family(page.get("userAgent")) == browser,', "need(True,", f"{C}.test_wrong_browser"),
    ('need(not i.get("diagnosticOverrides"),', "need(True,", f"{C}.test_diagnostic_override_is_not_acceptance"),
    ('need(call.get("result") == terminal["message"].get("result"),', "need(True,",
     f"{C}.test_page_snapshot_substituted_for_engine_state"),
    ('need(release_prefix <= len(answered),', "need(True,", f"{C}.test_post_release_state_moved_into_the_release_slot"),
    ("pending = [r for r in moves if r[\"seq\"] < release[\"seq\"] and not ended_before(r)",
     "pending = [r for r in moves if r[\"seq\"] < 10 ** 12 and not ended_before(r)",
     f"{C}.test_held_work_misclassified_as_wire_pending"),
    ("need(got in allowed,", "need(True,", f"{C}.test_a_lagging_or_unstamped_shell_member_is_not_established"),
    ('need(arms.digest(raw) == shell.get("bundleFileSha256"),', "need(True,",
     f"{C}.test_an_unreported_shell_manifest_is_not_established"),
    ('contradict(anchor == witness["setup"]["anchor"], "final selection anchor moved")',
     'contradict(True, "final selection anchor moved")', f"{H}.test_final_anchor_moved_is_a_failure"),
    ("contradict(text == reference.texts[admitted],", "contradict(True,",
     f"{H}.test_overshoot_beyond_the_admitted_extensions_is_a_failure"),
    ('contradict(not attribution["multiple"],', "contradict(True,", f"{H}.test_one_press_admitted_twice_is_a_failure"),
    ('contradict(len(ok) == len(witness["terminals"]),', "contradict(True,",
     f"{H}.test_a_refused_extension_terminal_is_a_failure"),
    ('need(not early, "a dirty checkpoint', 'need(True, "a dirty checkpoint', f"{H}.test_s12_gates_bind_the_two_second_arm_only"),
    ('need(request["generation"] == call.get("generation") == generation,', "need(True,",
     f"{H}.test_a_reference_call_on_another_generation_is_not_established"),
    ("        return _judge_run(run_dir, repo)\n    except Exception",
     "        return _judge_run(run_dir, repo)\n    except ZeroDivisionError",
     f"{N}.test_any_reader_exception_is_not_established"),
]


def main() -> int:
    source = JUDGE.read_text(encoding="utf-8")
    undetected = []
    with tempfile.TemporaryDirectory(prefix="four-arm-reader-sweep-") as scratch:
        for index, (find, replace, test) in enumerate(MUTATIONS):
            if source.count(find) != 1:
                undetected.append(f"{test}: anchor found {source.count(find)} times")
                continue
            target = Path(scratch) / str(index) / "judge_v23_product_four_arms.py"
            target.parent.mkdir()
            target.write_text(source.replace(find, replace), encoding="utf-8")
            for name in ("judge_v23_product_four_arms", "test_v23_product_four_arms"):
                sys.modules.pop(name, None)
            spec = importlib.util.spec_from_file_location("judge_v23_product_four_arms", target)
            module = importlib.util.module_from_spec(spec)
            sys.modules["judge_v23_product_four_arms"] = module
            spec.loader.exec_module(module)
            tests = importlib.import_module("test_v23_product_four_arms")
            suite = unittest.defaultTestLoader.loadTestsFromName(test, tests)
            with open(Path(scratch) / "log", "a", encoding="utf-8") as log:
                result = unittest.TextTestRunner(stream=log, verbosity=0).run(suite)
            red = bool(result.failures or result.errors)
            print(f"{'RED  ' if red else 'GREEN'} {test}")
            if not red:
                undetected.append(test)
    print(f"{len(MUTATIONS)} disabled checks; undetected:", undetected)
    return 1 if undetected else 0


if __name__ == "__main__":
    raise SystemExit(main())
