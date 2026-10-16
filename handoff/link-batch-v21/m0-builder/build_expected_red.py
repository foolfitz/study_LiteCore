"""Scratch builder for wasm_sdk_probe/tests/markdown_paste_expected.json (step 1 of the v21 task, part E).

The verdicts below are written by hand from the rules. This script only
  * computes sha256 and size of every corpus file,
  * runs round 2's md4c_scan harness (the core's own md4c 0.5.3, the swmd.cxx flags) on each file,
  * derives the verdict mechanically from those facts and refuses to write if it differs from the hand verdict,
  * writes the deciding fact as the item's "rule" text.
Not committed; the JSON is the fixture.
"""
import hashlib
import json
import os
import subprocess
import sys

REPO = "/home/jiajun/LibreOffice/study_LiteCore"
CORPUS = f"{REPO}/wasm_sdk_probe/tests/markdown_paste_corpus"
OUT = '/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/152c4a0f-6d39-4f18-8cc2-47c86da828be/scratchpad/m0/red-out.json'
SCAN = sys.argv[1]
R1 = "findings/evidence/link-batch-v21/native/markdown-paste/tool/corpus"
R2 = "findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool/corpus"
LIMIT = 65536

HAND = {
    # round 1 (findings/.../markdown-paste/tool/corpus)
    "round-1/C1.md": ("PASS", "Role elsewhere: the text/plain control of M7 (spec 9.6); natively it was only sent as text/plain. As Markdown bytes it is M1 + M2."),
    "round-1/M1.md": ("PASS", None),
    "round-1/M2.md": ("PASS", None),
    "round-1/M3.md": ("PASS", None),
    "round-1/M4.md": ("PASS", None),
    "round-1/M5.md": ("PASS", None),
    "round-1/M6.md": ("PASS", None),
    "round-1/M7.md": ("PASS", None),
    "round-1/M8.md": ("PASS", None),
    "round-1/M8-utf16le.bin": ("NUL", "M8 as UTF-16LE (round 1's MIME-utf16 arm): every ASCII character carries a 0x00 byte. Spec 9.6 excludes it from M1 as a non-string input."),
    "round-1/M9.md": ("PASS", None),
    "round-1/M10.md": ("PASS", "data: image; natively embedded, no request."),
    "round-1/M11.md": ("REMOTE", "Natively a linked image; connect attempted (round 1 strace)."),
    "round-1/M11b.md": ("REMOTE", "Natively a linked image; GET to the listener."),
    "round-1/M11c.md": ("REMOTE", "Natively a linked image; paste() blocked 5,003 ms on a silent server."),
    "round-1/M12.md": ("PASS", "L-md-wikilink."),
    "round-1/M13.md": ("NO_BLOCK", "Empty. Natively paste() true, one undo action, document unchanged."),
    "round-1/M14a.md": ("PASS", "16,594 bytes, under the limit."),
    "round-1/M14b.md": ("TOO_LARGE", "TOO_LARGE is not in spec 11 M0's verdict list (PASS/REMOTE/HTML/NO_BLOCK/NUL/PARSE_FAIL); the task brief's INVALID_ARGUMENT list does name the size. Raised in the step-1 report."),
    # round 2 (findings/.../markdown-paste/round-2/tool/corpus)
    "round-2/H1-comment-only.md": ("HTML", "Natively undo +1, document unchanged, no request."),
    "round-2/H2-html-block-img.md": ("HTML", "Natively a linked image; OPTIONS+GET+GET."),
    "round-2/H3-inline-html-img.md": ("HTML", "Natively the inline HTML is dropped and nothing is fetched; rule 2 refuses all raw HTML (L-md-no-html)."),
    "round-2/H4-inline-img-then-block.md": ("HTML", "Passed the old 9.3 rules; natively fetched (OPTIONS+GET+GET)."),
    "round-2/H5-html-block-img-sized.md": ("HTML", "Natively fetched (OPTIONS+GET) although the size is given."),
    "round-2/H6-html-link-stylesheet.md": ("HTML", "Natively OPTIONS+HEAD+GET, document unchanged."),
    "round-2/H7-text-then-html-block-img.md": ("HTML", "Passed the old 9.3 rules; natively fetched (OPTIONS+GET+GET)."),
    "round-2/N1-rule-only.md": ("PASS", "A lone rule; natively a horizontal-line paragraph. The old no-text rule refused it."),
    "round-2/S01-inline-http.md": ("REMOTE", "Natively a linked image; OPTIONS+GET."),
    "round-2/S02-https-hostname.md": ("REMOTE", "Natively a linked image; a TLS ClientHello to the closer."),
    "round-2/S03-reference.md": ("REMOTE", "Reference-style; natively a linked image; OPTIONS+GET."),
    "round-2/S04-two-images.md": ("REMOTE", "Natively two linked images; 2x(OPTIONS+GET)."),
    "round-2/S05-data-and-remote.md": ("REMOTE", "One data: and one remote image."),
    "round-2/S06-fenced-lookalike.md": ("PASS", "Look-alike in a fenced code block; natively literal, no request."),
    "round-2/S07-inline-code-lookalike.md": ("PASS", "Look-alike in inline code; natively literal, no request."),
    "round-2/S08-data-only.md": ("PASS", "data: image; natively embedded, no request."),
    "round-2/S09-indented-code-lookalike.md": ("PASS", "Look-alike in an indented code block; natively literal, no request."),
    "round-2/S10-escaped-lookalike.md": ("PASS", "Escaped; natively '!' and a hyperlink, no request."),
    "round-2/S11-autolink-png.md": ("PASS", "Autolink; natively a hyperlink, no request."),
    "round-2/S12-image-in-link.md": ("REMOTE", "Image inside a link, no text outside the image; natively a linked image, OPTIONS+GET."),
    "round-2/S13-bang-wikilink.md": ("PASS", "Natively literal, no request."),
    "round-2/S14-empty-alt-data.md": ("PASS", "Empty-alt data: image; natively embedded. The old no-text rule refused it."),
    "round-2/S15-uppercase-DATA.md": ("PASS", "Upper-case DATA:; natively embedded, no request. A case-sensitive rule 1 calls it REMOTE."),
    "round-2/W1-spaces.md": ("NO_BLOCK", "ASCII whitespace only; natively undo +1, document unchanged."),
    "round-2/W2-tabs.md": ("NO_BLOCK", "ASCII whitespace only; natively undo +1, document unchanged."),
    "round-2/W3-ideographic-space.md": ("PASS", "U+3000 is text to md4c; natively a paragraph holding it."),
    "round-2/W4-nbsp.md": ("PASS", "U+00A0 is text to md4c; natively a paragraph holding it."),
    "round-2/W5-newlines.md": ("NO_BLOCK", "ASCII whitespace only; natively undo +1, document unchanged."),
    "round-2/W6-mixed-ascii-ws.md": ("NO_BLOCK", "ASCII whitespace only; natively undo +1, document unchanged."),
    # new for spec 11 M0
    "m0/X01-nul-middle.md": ("NUL", "Spec 10.4: a 0x00 anywhere is refused."),
    "m0/X02-nul-trailing.md": ("NUL", "Writer strips trailing 0x00 (vcl transfer.cxx:1510-1515) and would paste the heading; the rule refuses any 0x00."),
    "m0/X03-nul-suffixed-reference.md": ("NUL", "Review 2 opus A1; M5's NUL-suffixed reference. On these bytes md4c ends the destination at the control character, so there is no definition and no image: without the NUL rule the scan would PASS it. On the NUL-stripped bytes Writer parses, md4c reports one non-data MD_SPAN_IMG [OBS, md4c harness]; that Writer then fetches is [INF] (S03's path), not run."),
    "m0/X04-nul-only.md": ("NUL", "Review 2 codex's minimal case: the scan sees a paragraph (MD_TEXT_NULLCHAR); Writer sees empty input."),
    "m0/X05-invalid-utf8-latin1-byte.md": ("INVALID_UTF8", "0xE9 (a Latin-1 e-acute) followed by a space: a 3-byte lead cut short. Spec 12.1. Without the rule md4c reports a paragraph (PASS); Writer would parse U+FFFD in its place [SRC]."),
    "m0/X06-invalid-utf8-truncated.md": ("INVALID_UTF8", "UTF-8 for two CJK characters, then a 3-byte sequence truncated at the end of the input. Spec 12.1."),
    "m0/X07-invalid-utf8-label-mismatch.md": ("PASS", "The item that forced spec 12.1. Without the UTF-8 rule the raw-byte scan PASSes it: md4c reads the labels [0xFF] and [0xFE] as U+00FF and U+00FE, which differ, so there is no image. Writer decodes invalid UTF-8 to U+FFFD (rtl_string2UString with OSTRING_TO_OUSTRING_CVTFLAGS, sal/textenc/converter.cxx:66-74), so both labels become [U+FFFD] and match; on those bytes md4c reports one MD_SPAN_IMG with src http://127.0.0.1:18765/x07.png [OBS, md4c harness]. The native fetch is [INF], not run."),
    "m0/X08-angle-generic.md": ("HTML", "List<T> outside code is raw inline HTML to md4c (spec 10.4, L-md-no-html extended)."),
    "m0/X09-angle-generic-inline-code.md": ("PASS", "Control for X08: the same inside inline code is not HTML."),
    "m0/X10-angle-generic-fenced.md": ("PASS", "Control for X08: the same inside a fenced code block is not HTML."),
    "m0/X11-task-list.md": ("PASS", "GFM task list (MD_FLAG_TASKLISTS is in MD_DIALECT_GITHUB); pasted, L-md-task-checkbox."),
    "m0/X12-entities.md": ("PASS", "Entities are MD_TEXT_ENTITY, not raw HTML (&lt;tag&gt; included); pasted, L-md-entities (finding 149)."),
    "m0/X13-remote-image-and-inline-html.md": ("REMOTE", "Added beyond spec 11 M0's list: pins the task brief's order, MARKDOWN_REMOTE_IMAGE (4) before MARKDOWN_HTML_UNSUPPORTED (5). md4c reports both an MD_SPAN_IMG and MD_TEXT_HTML."),
    "m0/X15-invalid-utf8-overlong.md": ("INVALID_UTF8", "Overlong 0xC0 0xAF ('/' in two bytes). Spec 12.1. md4c's own decoder would read it as U+002F; RFC 3629 forbids it."),
    "m0/X16-invalid-utf8-surrogate.md": ("INVALID_UTF8", "0xED 0xA0 0x80 encodes the surrogate U+D800. Spec 12.1."),
    "m0/X17-invalid-utf8-above-10ffff.md": ("INVALID_UTF8", "0xF4 0x90 0x80 0x80 would be U+110000, above U+10FFFF. Spec 12.1."),
    "m0/X14-parse-fail-injected.md": ("PARSE_FAIL", "md4c 0.5.3's md_parse returns non-zero only when malloc/realloc fails or a callback returns non-zero (md4c.c:418-495, :1039-1043, :5009-5011); the reference-definition output cap (:2333-2340) only stops resolving. No input bytes make it fail, so the model test fails every allocation inside md_parse for this item. Feasibility checked natively: md4c.c linked with -Wl,--wrap=malloc,--wrap=realloc returns -1 for these bytes and 0 without the injection."),
}
INJECT = {"m0/X14-parse-fail-injected.md": "allocation-failure"}


def scan(path):
    out = subprocess.run([SCAN, path], check=True, capture_output=True).stdout
    return json.loads(out.decode("utf-8", "replace"))


def derive(data, facts, inject, mutation=None):
    if b"\x00" in data:
        return "NUL", "0x00 at byte offset %d (%d in all)" % (data.index(b"\x00"), data.count(b"\x00"))
    if mutation != "no-utf8-rule":
        try:
            data.decode("utf-8")  # Python's strict codec is RFC 3629: no overlongs, surrogates, > U+10FFFF, truncation
        except UnicodeDecodeError as e:
            return "INVALID_UTF8", "not valid UTF-8 (RFC 3629): %s at byte offset %d" % (e.reason, e.start)
    if len(data) > LIMIT:
        return "TOO_LARGE", "%d bytes > %d" % (len(data), LIMIT)
    if inject:
        return "PARSE_FAIL", "md_parse returns non-zero (injected: %s)" % inject
    if facts["parseResult"] != 0:
        return "PARSE_FAIL", "md_parse returns %d" % facts["parseResult"]
    if mutation == "old-no-text":
        if facts["textNonBlank"] == 0:
            return "NO_BLOCK", "mutated rule 3 (old 9.3 no-text): no non-blank text outside images"
    elif not facts["blocks"]:
        return "NO_BLOCK", "md4c enters no block other than MD_BLOCK_DOC"
    nondata = facts["imagesNonData"] if mutation == "case-sensitive-data" else facts["imagesNonDataCI"]
    if nondata:
        return "REMOTE", "MD_SPAN_IMG x%d, %d with a src not starting with data: (case-insensitive): %s" % (
            facts["images"], nondata, ", ".join(s for s in facts["srcs"] if not s.lower().startswith("data:")))
    if mutation != "no-rule-2" and (facts["htmlBlocks"] or facts["htmlText"]):
        return "HTML", "MD_BLOCK_HTML x%d, MD_TEXT_HTML x%d" % (facts["htmlBlocks"], facts["htmlText"])
    blocks = ", ".join("%s x%d" % kv for kv in facts["blocks"].items())
    img = "no MD_SPAN_IMG" if not facts["images"] else "MD_SPAN_IMG x%d, all data:" % facts["images"]
    return "PASS", "no rule fires: blocks %s; %s; no raw HTML" % (blocks, img)


def main():
    files = sorted(os.path.relpath(os.path.join(d, f), CORPUS)
                   for d, _, fs in os.walk(CORPUS) for f in fs)
    assert sorted(HAND) == files, (set(HAND) ^ set(files))
    items, flips = [], {"case-sensitive-data": [], "no-rule-2": [], "old-no-text": [], "no-utf8-rule": []}
    bad = 0
    for rel in files:
        path = os.path.join(CORPUS, rel)
        data = open(path, "rb").read()
        facts = scan(path)
        assert facts["bytes"] == len(data)
        inject = INJECT.get(rel)
        verdict, rule = derive(data, facts, inject)
        hand, note = HAND[rel]
        if verdict != hand:
            print("DISAGREE", rel, "hand", hand, "derived", verdict, rule)
            bad += 1
        for m in flips:
            mv, _ = derive(data, facts, inject, m)
            if mv != verdict:
                flips[m].append("%s: %s -> %s" % (rel, verdict, mv))
        src = None
        if rel.startswith("round-1/"):
            src = f"{R1}/{rel.split('/', 1)[1]}"
        elif rel.startswith("round-2/"):
            src = f"{R2}/{rel.split('/', 1)[1]}"
        if src:
            assert open(os.path.join(REPO, src), "rb").read() == data, src
        item = {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        if src:
            item["copiedFrom"] = src
        else:
            item["content"] = repr(data)
        item["verdict"] = hand
        if inject:
            item["inject"] = inject
            item["verdictWithoutInjection"] = derive(data, facts, None)[0]
        item["rule"] = rule
        if note:
            item["note"] = note
        items.append(item)
    if bad:
        sys.exit("refusing to write: %d disagreements" % bad)
    doc = {
        "fixture": "M0 of specs/SPEC-M3-link-batch-v21.md section 11.2 (pinned at 523871fa), as amended by section 12.1 (3d9ca3a4): the expected pre-dispatch verdict of every corpus item, written before any scanner code exists.",
        "corpus": "tests/markdown_paste_corpus/ -- round-1/ and round-2/ are byte copies of the two native rounds' corpora (copiedFrom; both rounds' SHA256SUMS verify); m0/ holds the items spec 11 M0 adds (NUL, invalid UTF-8, List<T>, task list, entities, parse failure), X13 (rule order), and X15-X17 (the RFC 3629 classes spec 12.1 names). Every file has exactly one item below, and every item one file. 'content' (m0 items only) is the file's bytes as a Python bytes literal.",
        "rules": {
            "source": "spec 9.14 (three scan rules), 10.4 (NUL, encoding, md_parse failure), 12.1 (valid UTF-8; labels TOO_LARGE and INVALID_UTF8; PARSE_FAIL by injection), and the task brief's 'Engine reply' (handoff/tasks/TASK-2026-10-16-v21-implementation.md), which fixes the order.",
            "order": ["NUL", "INVALID_UTF8", "TOO_LARGE", "PARSE_FAIL", "NO_BLOCK", "REMOTE", "HTML", "PASS"],
            "orderNote": "First rule that fires gives the verdict. NUL, INVALID_UTF8, TOO_LARGE, PARSE_FAIL and NO_BLOCK are all INVALID_ARGUMENT (code 1). Codes 2 (MARKDOWN_ENCODING_UNSUPPORTED) and 3 (MARKDOWN_NEEDS_CARET) come between code 1 and REMOTE in the engine but are not properties of the bytes: every verdict here assumes a UTF-8 thread encoding and a collapsed caret. NO_BLOCK and REMOTE/HTML can never both hold (an image span or HTML needs a block), so only REMOTE-before-HTML is an observable order; X13 pins it.",
            "verdicts": {
                "NUL": {"code": "INVALID_ARGUMENT", "when": "a byte 0x00 anywhere in the input"},
                "INVALID_UTF8": {"code": "INVALID_ARGUMENT", "when": "the input is not valid UTF-8 by RFC 3629: an overlong form, a surrogate (U+D800-U+DFFF), a value above U+10FFFF, a byte that cannot start a sequence, or a truncated sequence"},
                "TOO_LARGE": {"code": "INVALID_ARGUMENT", "when": "more than 65,536 bytes (the engine's hard limit)"},
                "PARSE_FAIL": {"code": "INVALID_ARGUMENT", "when": "md_parse returns non-zero; no input bytes cause it in md4c 0.5.3, so it is produced by allocation-failure injection in the native model test only (item field 'inject')"},
                "NO_BLOCK": {"code": "INVALID_ARGUMENT", "when": "md4c enters no block other than MD_BLOCK_DOC"},
                "REMOTE": {"code": "MARKDOWN_REMOTE_IMAGE", "when": "any MD_SPAN_IMG whose src does not start with \"data:\", compared case-insensitively"},
                "HTML": {"code": "MARKDOWN_HTML_UNSUPPORTED", "when": "any MD_BLOCK_HTML or MD_TEXT_HTML"},
                "PASS": {"code": None, "when": "no rule fires; the engine dispatches"},
            },
            "dispatched": "false for every verdict except PASS",
        },
        "parser": {
            "md4c": "0.5.3, wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src (md4c.c sha256 f12907817a17ae7d0f6c8d18770df839f187cad5649dd36a475dba0675c5c1f8, md4c.h 4efd19bf7ec270691d5b4189f496886e421768a814b5e817eb945aa85e859f18), byte-identical in all three core trees (round 2 T3)",
            "flags": "MD_DIALECT_GITHUB | MD_FLAG_WIKILINKS = 0x2f0c (libreoffice-26-8 sw/source/filter/md/swmd.cxx:950-958)",
            "facts": "Each item's 'rule' text states the deciding fact as round 2's harness reports it (findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool/md4c_scan.c, rebuilt in scratch with the README's command; binary sha256 49495bc0e2d12dad944283caa42deb2c0316d2a0a4c84a2dcc010630d9e65cff, the same as round 2 recorded). The verdicts were written by hand from the rules and cross-checked against a mechanical reading of those facts: 0 disagreements.",
        },
        "mutations": {
            "note": "Informative, computed from the same facts: the items whose verdict each of M0's four red mutations (spec 11.2's three plus 12.1's 'UTF-8 rule removed') changes, the mutated rule keeping its own verdict label (rule 3 replaced by the old 9.3 no-text rule still answers NO_BLOCK). The model test must show each mutation red.",
            "rule-1-case-sensitive": flips["case-sensitive-data"],
            "rule-2-removed": flips["no-rule-2"],
            "rule-3-replaced-by-old-no-text": flips["old-no-text"],
            "utf8-rule-removed": flips["no-utf8-rule"],
        },
        "items": items,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    counts = {}
    for it in items:
        counts[it["verdict"]] = counts.get(it["verdict"], 0) + 1
    print(len(items), "items", counts)
    for m, l in flips.items():
        print(m, len(l))
        for x in l:
            print("  ", x)


main()
