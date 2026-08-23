#!/usr/bin/env python3
"""Assemble the e2-editor-v4 product profile: the successor identity for ABI 4.

Named after what it BUILDS, not after a phase.  `build_e2_b_profile.py` and
`build_e2_c_profile.py` are named for E2-B and E2-C because each of those
phases happened to mint a version; this relink happens inside E2-C, so
`build_e2_d_profile.py` would claim a phase that does not exist.

A separate entry point again, for the third time and the same reason (SPEC
E2-B 5.8): a builder that can emit either version is a builder whose output
nobody can name.  It imports the v3 builder -- importing does not build -- and
changes exactly what this relink changes.

WHAT MOVES, AND WHAT DELIBERATELY DOES NOT
------------------------------------------

Moves:

  * `abiVersion` 3 -> 4, and the binary reports 4.  The worker compares the two
    with an EXACT match at init (`sdk-worker.js:925-935`), so a v3 client that
    reaches this profile dies at init with INCOMPATIBLE_ABI rather than running
    against a contract whose action ids it does not have.  That handshake is
    the whole reason appending under a SUCCESSOR identity is safe while
    appending IN PLACE is not.

  * six new actions, ids 16-21, appended.  Ids 1-15 are inherited VERBATIM --
    that is the claim this profile makes, and `tests/editor_abi_header_test.cpp`
    pins every one of them.

  * `redo`, which is NOT an action and has no wire id.  It is a document-level
    SDK operation, the sibling of `undo`, declared here the same way undo is.
    The relink queue's acceptance criterion asked for `"redo": 16` in the
    worker; that criterion was written before the design and describes a
    different remedy.  See the queue item for the correction.

Does not move, on purpose:

  * `version` (the contract version) and the capability strings.  v3's builder
    recorded why: the worker's operation map keys on the capability, so moving
    it would make this profile unreachable through the worker -- the defect
    SPEC E2-C 2.2 exists to record.  ABI version is the field that carries a
    binary-compatibility break, and it is the one that moved.

  * the ten v1 actions stay `["collapsed"]`.  Nothing measured a wider gesture
    for them, and `queue-cut-cannot-remove-text` is closed by ADDING an action
    rather than by widening theirs -- which is why delete-selection exists.

WITHHELD RATHER THAN ABSENT
---------------------------

Two of the six ship dark, and dark is a manifest choice rather than a build
one.  The engine intersects (`gEditorActionGestures[a] &= mask`), so a manifest
can withhold what the binary implements and can never grant what it does not.
That asymmetry runs one way only, and it is what makes shipping dark free: a
later profile can grant these WITHOUT ANOTHER RELINK, on the strength of a
measurement.  Shipping them dark therefore claims nothing.

The trap, and it is not hypothetical: the engine initialises every entry to
ALL-PERMITTED on the first `set_action_gestures` call and intersects from
there.  An action the worker never calls the setter for keeps that all-permitted
default -- so "withheld" has to mean `gestures: []`, which the worker's loop
still passes through as mask 0, and must NOT mean "omit the action".  Omitting
it would ship the thing wide open while the manifest looked silent about it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_b_profile as v2  # noqa: E402
import build_e2_c_profile as v3  # noqa: E402
from e1_support import write_json  # noqa: E402

ABI_VERSION = 4
PROFILE = "e2-editor-v4"

# The four movements are caret movements, so `collapsed` is the only gesture
# that has a meaning for them; what happens when one runs with a range already
# selected is not characterised, and declaring it would be the manifest
# claiming coverage the evidence does not have.
#
# `no-extend-selection` is not a narrowing of something offered -- the ABI
# refuses `extendSelection` for anything but the two v1 moves
# (editor_api.cpp:159) -- it is the manifest saying so where a client can read
# it, so nobody builds shift+Up on the assumption that it must work.
MOVE_LINE_ACTIONS = {
    "move-line-up": 16,
    "move-line-down": 17,
    "move-line-home": 18,
    "move-line-end": 19,
}

NEW_ACTIONS: dict[str, dict] = {
    name: {"id": wire, "gestures": [v2.COLLAPSED],
           "limits": ["no-extend-selection"]}
    for name, wire in MOVE_LINE_ACTIONS.items()
}

# delete-selection: RANGE ONLY, both range classes, CHARACTERISED 2026-08-22.
#
# `collapsed` is withheld because an action named delete-selection that runs
# with no selection has no meaning, and delete-backward already owns that case
# with a characterisation behind it.  Granting collapsed here would put two
# actions on one behaviour and quietly widen the one that was measured.
#
# BOTH RANGE BITS, and the reason it is both rather than one is the engine's,
# not a preference.  probe_engine.cpp gates an unclassified selection on
# `range_single AND range_cross` -- it cannot tell the two apart without an
# html read, and that read is the wedge risk findings 037/038 describe.  So
# `[range-single]` alone is not a narrower grant, it is an OFF SWITCH: it was
# shipped that way from the link until this measurement, and the engine
# refused every cut with "this action is not offered for this kind of
# selection in this profile" -- a sentence that was true of no selection at
# all.  A manifest that declares a gesture the binary will never honour is the
# "describes but does not constrain" defect pointing the other way, and it is
# worse than either extreme because it reads as a deliberate narrowing.
#
# The measurement this rests on, pre-registered before it ran
# (findings/evidence/queue-cut-cannot-remove-text/PREDICTION.md, and RESULT
# -range-cross.md for the outcome).  A MIRRORED manifest, dist/ never written,
# probe.wasm byte-identical to f923cfa5:
#
#   P-CUT-1  the refusal disappears                            held
#   P-CUT-2  a within-paragraph range is removed, neighbours
#            survive, the document still parses                held
#   P-CUT-3  the session stays `ready` and can still save      held
#   P-CUT-4  the cross-paragraph shape, recorded not forecast  four shapes,
#            all correct: two paragraphs, three paragraphs into a bullet list,
#            a bullet list through a plain paragraph into a numbered list, and
#            within one list.  Every arm merged exactly as a word processor
#            does -- head of the first paragraph plus tail of the last, line
#            count down by exactly the number of boundaries crossed, every
#            untouched paragraph verbatim, session ready, document readable.
#
# RANGE_DELETE_CHARACTERISED.  What is still NOT characterised is named rather
# than implied: a range inside a table, and one covering a footnote or endnote
# reference.  Neither is in this fixture.
NEW_ACTIONS["delete-selection"] = {
    "id": 20,
    "gestures": [v2.RANGE_SINGLE, v2.RANGE_CROSS],
    "limits": ["not-characterised-in-tables-or-note-apparatus"],
}

# select-all: SHIPPED DARK.  Empty list, not omitted -- see the module
# docstring for why the difference is the whole mechanism.
NEW_ACTIONS["select-all"] = {
    "id": 21,
    "gestures": [],
    "limits": ["withheld-pending-characterisation"],
}


def action_map() -> dict:
    actions = v3.action_map()
    inherited = dict(actions)
    for name, spec in NEW_ACTIONS.items():
        actions[name] = {"id": spec["id"], "gestures": list(spec["gestures"]),
                         "limits": list(spec["limits"])}

    # The claim this profile makes, checked rather than asserted in prose: the
    # fifteen inherited actions came through with their ids untouched, and the
    # six new ones occupy 16-21 with nothing colliding.
    for name, spec in inherited.items():
        if actions[name]["id"] != spec["id"]:
            raise SystemExit(f"v4 renumbered inherited action {name}: "
                             f"{spec['id']} -> {actions[name]['id']}")
    ids = sorted(spec["id"] for spec in actions.values())
    if ids != list(range(1, 22)):
        raise SystemExit(f"v4 action ids are not 1..21 exactly: {ids}")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    # A DIAGNOSTIC PROFILE MUST NOT WEAR THE PRODUCT'S NAME.
    #
    # a11y gate 0 needs this packaging against a DIFFERENT core build (one whose
    # accessibility call sites are compiled in), and `profile` is one of the
    # five identities a profile is.  Two artifacts declaring `e2-editor-v4`
    # would make every report that quotes a profile name ambiguous, and this
    # tree has already paid once for an archive directory that named a
    # different artifact than the one inside it.
    #
    # Defaulted, so omitting it reproduces the shipped invocation byte for byte.
    parser.add_argument("--paragraph-text", action="store_true",
                        help="declare caretParagraphText: the engine being "
                             "packaged was built with "
                             "OXSDK_A11Y_PARAGRAPH_TEXT. Off by default, so "
                             "the shipped invocation is unchanged")
    parser.add_argument("--document-outline", action="store_true",
                        help="declare documentOutline: the engine being "
                             "packaged was built with OXSDK_A11Y_OUTLINE. Off "
                             "by default, so the shipped invocation is "
                             "unchanged")
    # GRANTING A GESTURE NOBODY HAS MEASURED, on purpose and only here.
    #
    # Finding 078: the four inline formats are offered for `collapsed` only,
    # because range dispatch was characterised for the paragraph actions and not
    # for these -- so the manifest declines to claim it. That is right, and the
    # cost of it is that the product cannot embolden text a user has selected.
    #
    # The measurement that would justify granting it cannot be taken through a
    # manifest that withholds it: the engine refuses before dispatch. So this
    # flag exists to build the profile the CHARACTERISATION runs against, and
    # for nothing else. What it produces is not a product profile and says so
    # in its own limits.
    #
    # Refused with the product's name below, because a profile that grants an
    # unmeasured gesture while wearing the shipped identity is the exact shape
    # of claim this contract is built to prevent.
    parser.add_argument("--inline-range-gestures",
                        choices=("none", "range-single", "range-cross", "all"),
                        default="none",
                        help="`range-single` grants what finding 078's "
                             "characterisation measured, on all four inline "
                             "formats, and records range-cross as withheld. "
                             "`all` also grants range-cross, which nobody has "
                             "characterised -- DIAGNOSTIC ONLY, and refused "
                             "under the product's own name")
    parser.add_argument("--profile", default=PROFILE,
                        help="profile identity to stamp; defaults to the "
                             "product's. Use another name for any profile "
                             "built against a core that is not the product's")
    args = parser.parse_args()

    if args.inline_range_gestures not in ("none", "range-single") \
            and args.profile == PROFILE:
        raise SystemExit(
            "refusing to grant unmeasured inline range gestures under the "
            f"product's own name ({PROFILE}). Pass --profile with a "
            "diagnostic name: a manifest that claims coverage the evidence "
            "does not have is the one thing this contract exists to prevent")

    problems = v2.refuse_non_product(args.exports)
    if problems:
        raise SystemExit("refusing to build a v4 product profile:\n  "
                         + "\n  ".join(problems))

    v2.build_profile(
        source_manifest=args.source_manifest, loader=args.loader,
        wasm=args.wasm, worker=args.worker, output=args.output,
        exports=args.exports, cross_paragraph=True)

    paragraph_text = args.paragraph_text
    document_outline = args.document_outline
    manifest_path = args.output / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profile"] = args.profile
    manifest["sdkVersion"] = manifest["sdkVersion"].replace(
        "+e2-editor-v2", "+" + args.profile)
    contract = manifest["editorContract"]
    contract["abiVersion"] = ABI_VERSION
    contract["actions"] = action_map()
    if args.inline_range_gestures != "none":
        diagnostic = args.inline_range_gestures != "range-single"
        # `range-cross` alone is the discriminator for a question the other
        # three cannot answer: whether the ENGINE calls a selection inside one
        # line `range-single` at all. Measured 2026-08-23 -- the same drag that
        # succeeds where both are granted is REFUSED where only range-single
        # is, so the engine is classifying it as something else, and a profile
        # that grants only cross says which.
        extra = {"range-single": [v2.RANGE_SINGLE],
                 "range-cross": [v2.RANGE_CROSS],
                 "all": [v2.RANGE_SINGLE, v2.RANGE_CROSS]}[
                     args.inline_range_gestures]
        for name in ("set-bold", "set-italic", "set-underline",
                     "set-strikethrough"):
            action = contract["actions"][name]
            action["gestures"] = list(action["gestures"]) + list(extra)
            if diagnostic:
                # Nobody has characterised `range-cross`, and a manifest that
                # offers it must say so in its own limits rather than rely on
                # whoever reads it knowing where it came from.
                action["limits"] = list(action["limits"]) + [
                    "range-gesture-granted-for-characterisation-only"]
            else:
                # THE WITHHOLDING IS WRITTEN DOWN, not left as an absence.
                #
                # This project has already paid for the difference: the engine
                # initialises every action to ALL-PERMITTED and intersects from
                # there, so "omitted" and "withheld" are opposite instructions,
                # and an absence with no recorded reason invites the next
                # builder to read it as an oversight and "fix" it. `range-cross`
                # is missing here on purpose.
                action["limits"] = list(action["limits"]) + [
                    "range-single-characterised-2026-08-23",
                    "range-cross-withheld-pending-characterisation"]
        if diagnostic:
            contract["inlineRangeGesturesAreDiagnostic"] = True
        else:
            # What the grant rests on, in the artifact that makes the claim.
            contract["inlineRangeEvidence"] = (
                "findings/evidence/f078-inline-format-on-a-selection/ -- all "
                "four inline formats measured on range-single against the "
                "shipped artifact f923cfa5, the formatted text equal to the "
                "selected text in every arm, with a baseline save and a "
                "shipped-profile control. range-cross measured equal too but "
                "expresses a fully selected paragraph as paragraph-level "
                "formatting and reports a 5-character list prefix in the "
                "selection text; neither is explained, so it is not granted")
    contract["inlineFormatEnabledIsHonoured"] = True
    # The sibling of `undo`, and declared the same way: a document-level SDK
    # operation, not an action, so it has no wire id and no gesture.
    contract["redo"] = "document-sdk-redo"
    # ROADMAP 3.4.  DECLARED, so a host can tell "this profile does not carry
    # the text" from "this paragraph is empty" BEFORE reading the field --
    # exactly the distinction `redo` above is declared for, and the one the
    # worker projects as `null` rather than `""`.
    #
    # Tied to the flag rather than asserted: the field is emitted only by an
    # engine built with OXSDK_A11Y_PARAGRAPH_TEXT, so a manifest that claimed
    # it unconditionally would be the "describes but does not constrain" defect
    # that cost this tree the 2026-08-22 cut. The builder is TOLD which kind of
    # artifact it is packaging; it does not guess.
    if paragraph_text:
        contract["caretParagraphText"] = "focused-paragraph-text"
    # ROADMAP 3.4's structure half, declared the same way and for the same
    # reason: a host has to tell "this profile carries no outline" from "this
    # document has no paragraphs" BEFORE it reads the field, because the second
    # would make it announce a blank document.
    if document_outline:
        contract["documentOutline"] = "accessible-document-outline"
    manifest["editorContract"] = contract
    write_json(manifest_path, manifest)

    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    print(json.dumps({
        "profile": args.profile,
        "abiVersion": ABI_VERSION,
        "wasmSha256": contract.get("wasmSha256"),
        "manifestSha256": digest,
        "actions": len(contract["actions"]),
        "withheld": sorted(name for name, spec in contract["actions"].items()
                           if not spec.get("gestures")),
        "noteLimitOn": sorted(name for name, spec in contract["actions"].items()
                              if v3.NOTE_LIMIT in spec.get("limits", [])),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
