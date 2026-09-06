import pathlib, sys
old_v, new_v = sys.argv[1], sys.argv[2]
p = pathlib.Path("tools/build_e2_c_shell_bundle.py")
s = p.read_text(encoding="utf-8")
old = 'MANIFEST = Path("e2/editor-shell-v2-bundle-%s.json")' % old_v
new = 'MANIFEST = Path("e2/editor-shell-v2-bundle-%s.json")' % new_v
# 2026-08-17's lesson, wired as an assertion: a string replace that did not
# match once left MANIFEST pointing at the previous generation while --write
# regenerated it in place.  Silence is what made that expensive.
assert s.count(old) == 1, "expected exactly 1 MANIFEST line, found %d" % s.count(old)
p.write_text(s.replace(old, new), encoding="utf-8")
print("MANIFEST repointed %s -> %s" % (old_v, new_v))
