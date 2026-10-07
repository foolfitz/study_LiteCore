"""For every tag in FcGetLangs() (the only tags mapToFontConfigLangTag can return),
add it as a STRING FC_LANG, run FcConfigSubstitute, report the first lang value."""
import ctypes, sys
lib = ctypes.CDLL(sys.argv[1]); V = ctypes.c_void_p
for n, r in (("FcPatternCreate", V), ("FcConfigGetCurrent", V), ("FcGetLangs", V), ("FcStrListCreate", V)):
    getattr(lib, n).restype = r
lib.FcStrListNext.restype = ctypes.c_char_p; lib.FcStrListNext.argtypes = [V]; lib.FcStrListCreate.argtypes = [V]
class FcValue(ctypes.Structure):
    class U(ctypes.Union):
        _fields_ = [("s", ctypes.c_char_p), ("d", ctypes.c_double), ("p", V)]
    _fields_ = [("type", ctypes.c_int), ("u", U)]
it = lib.FcStrListCreate(lib.FcGetLangs()); langs = []
while True:
    s = lib.FcStrListNext(it)
    if not s: break
    langs.append(s.decode())
cfg = V(lib.FcConfigGetCurrent())
changed = []
for lang in sorted(langs):
    p = V(lib.FcPatternCreate())
    lib.FcPatternAddString(p, b"family", b"x")
    lib.FcPatternAddString(p, b"lang", lang.encode())
    lib.FcConfigSubstitute(cfg, p, 0)
    v = FcValue(); b = ctypes.c_int()
    lib.FcPatternGetWithBinding(p, b"lang", 0, ctypes.byref(v), ctypes.byref(b))
    got = v.u.s.decode() if v.type == 3 else f"<type {v.type}>"
    if got.lower() != lang.lower():
        changed.append((lang, got))
print(f"FcGetLangs: {len(langs)} tags; with '-': {sum('-' in l for l in langs)}; rewritten: {len(changed)}")
for a, g in changed: print(f"  {a} -> {g}")
