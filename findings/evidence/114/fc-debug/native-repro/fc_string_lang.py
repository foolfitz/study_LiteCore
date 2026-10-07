"""Ask fontconfig the way LibreOffice's PrintFontManager::Substitute does: FC_LANG added as a STRING."""
import ctypes, sys
lib = ctypes.CDLL(sys.argv[1])
lib.FcPatternCreate.restype = ctypes.c_void_p
lib.FcFontMatch.restype = ctypes.c_void_p
lib.FcConfigGetCurrent.restype = ctypes.c_void_p
lib.FcNameUnparse.restype = ctypes.c_void_p
lib.FcGetVersion.restype = ctypes.c_int
for a in ("FcPatternAddString", "FcPatternAddBool", "FcConfigSubstitute", "FcDefaultSubstitute", "FcFontMatch", "FcPatternGetString", "FcPatternPrint", "FcNameUnparse"):
    getattr(lib, a).argtypes = None
print("fontconfig", lib.FcGetVersion())
for lang in sys.argv[2:]:
    p = ctypes.c_void_p(lib.FcPatternCreate())
    lib.FcPatternAddBool(p, b"scalable", 1)
    lib.FcPatternAddString(p, b"family", "思源黑體".encode())
    if lang != "-":
        lib.FcPatternAddString(p, b"lang", lang.encode())
    cfg = ctypes.c_void_p(lib.FcConfigGetCurrent())
    lib.FcConfigSubstitute(cfg, p, 0)
    lib.FcDefaultSubstitute(p)
    langv = ctypes.c_char_p(); fam = ctypes.c_char_p()
    r = lib.FcPatternGetString(p, b"lang", 0, ctypes.byref(langv))
    res = ctypes.c_int(0)
    best = ctypes.c_void_p(lib.FcFontMatch(cfg, p, ctypes.byref(res)))
    lib.FcPatternGetString(best, b"family", 0, ctypes.byref(fam))
    print(f"asked lang={lang!r:10} after-substitute lang[0]={(langv.value.decode() if r == 0 and langv.value else '(not a string / none)')!r:28} -> {fam.value.decode()}")
