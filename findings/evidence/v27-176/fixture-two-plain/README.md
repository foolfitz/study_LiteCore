# S3's and PL-1's document: two-plain.odt (2026-10-30)

SPEC-M3-v27-finding-176 7.3 S3: "a two-paragraph document (`Plain first` / `E1-EMPTY-AFTER`), saved once as ODT by the native core from `native/fixtures/two-plain.fodt`, receipt and sha pinned in the tool". PL-1 (7.2) runs S3's recipe, so the document is made now and S3 will pin the same bytes.

- Tool: `make_two_plain_odt.py` (checks the input against `findings/evidence/176/native/fixtures/SHA256SUMS`; `soffice --headless --convert-to odt` from `native-lok-26-8/build/instdir`, the core finding 176's native arm ran on, fresh user profile).
- `build-01/`: exit 0, 1.37 s, buildid `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb` (the native arm's `identity.json` versionrc), output `two-plain.odt` sha256 `56bc01b03b094b8da784fa98419873009fb887c8bf62953d0574f71c18a497a9`. Its `content.xml` body is the two `Standard` paragraphs, nothing else.
