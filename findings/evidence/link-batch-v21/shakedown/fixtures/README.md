# Converted fixtures (S-6), item 1

The ten `.odt` files here are `N142/fixtures/*.fodt` (`findings/evidence/link-batch-v21/native/142-ctrl-home-end/fixtures/`) converted by `wasm_sdk_probe/tools/fodt_to_odt.py --batch` (ARMS.md S-6; ARMS-item1.md §2.5 and §8 D-4). `SHA256SUMS` lists the outputs; the sources' hashes are in `ARMS-item1.md` §0.

- **Deterministic.** Fixed timestamps and member order; converting again gives the same bytes [observed: `tests/test_v21_fodt_odt.py::test_the_committed_outputs_are_the_converter_s` reconverts all ten and compares bytes].
- **Proof (i)** (paragraphs through the S-7 adapter equal the flat file's): holds for all ten fixtures and all 171 native saved documents (`d1-marker/out/*/r*.fodt.gz` and `out/*/r*.fodt.gz`) [observed: `tools/v21_item1_marker.py --self-test`, "cross-container on the real adapter: 0 problem(s)"].
- **Proof (ii)** (every top-level slice and every automatic-style slice is in the part its rule names, byte for byte; mimetype first and stored): `fodt_to_odt.py --verify` passes for all ten [observed]. The batch refuses to write an output whose proof fails [source: `wasm_sdk_probe/tools/fodt_to_odt.py`, `main`].
- **Proof (iii)** is per run: each runner records the saved document's paragraphs against the native saved document's.
- `header-footer.odt` is used by no item-1 arm. It is here because it is the only fixture with master-styles paragraphs, so it is the one that catches an adapter which loses them [observed: the three adapter mutations in the self-test are each caught by exactly 1 source, this one].
