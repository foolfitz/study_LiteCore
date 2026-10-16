# v21 pre-link gates run by the main session (2026-10-16)

- what-the-link-ships-v21.json: python3 tools/what_the_link_ships.py --since 543a5566 --variant link-batch-v21 --shipped-profile dist/profiles/e2-editor-v20 --json
  - ok true; configurationDrift [], so E2_V21_OBJECTS is exactly the four product units and no md4c object is among ours (spec §11 I1).
  - probe_engine, sdk_api and editor_api changed; unoembind_stub identical.
  - The worker changed: 478d0da1… shipped, 0d55bcfa… in the tree.
- test-e2-c-static.txt: nice make -k test-e2-c-static, exit 2. It stopped at the expected red, tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree, because shell generation v74 is not frozen yet.
  - The main session then ran every later command of the target itself:
    - check_gesture_offers.py is red (no v21 manifest until the link);
    - every other command passed.
  - The M1-1 line, carriers E2_V15, E2_V19, E2_V20 and E2_V21, runs before the stop and passed.
