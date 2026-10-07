"""Ask fontconfig like PrintFontManager::Substitute: family string, optional generic,
FC_LANG as STRING, optional charset of code points; print every lang value with its
type and binding, and the best match (family, file, index).

usage: fcq.py LIB FAMILY [--generic serif|sans] [--chars 4e2d,5b57] [--weight 80] LANG...
"""
import ctypes, sys

lib = ctypes.CDLL(sys.argv[1])
family = sys.argv[2]
args = sys.argv[3:]
generic = None; chars = []; weight = None
while args and args[0].startswith("--"):
    k = args.pop(0); v = args.pop(0)
    if k == "--generic": generic = v
    elif k == "--chars": chars = [int(c, 16) for c in v.split(",") if c]
    elif k == "--weight": weight = int(v)

V = ctypes.c_void_p
for name, res in (("FcPatternCreate", V), ("FcFontMatch", V), ("FcConfigGetCurrent", V),
                  ("FcCharSetCreate", V), ("FcNameUnparse", V), ("FcPatternFormat", V)):
    getattr(lib, name).restype = res
lib.FcGetVersion.restype = ctypes.c_int


class FcValue(ctypes.Structure):
    class U(ctypes.Union):
        _fields_ = [("s", ctypes.c_char_p), ("i", ctypes.c_int), ("b", ctypes.c_int),
                    ("d", ctypes.c_double), ("p", ctypes.c_void_p)]
    _fields_ = [("type", ctypes.c_int), ("u", U)]


lib.FcPatternGetWithBinding.restype = ctypes.c_int
lib.FcLangSetGetLangs.restype = V
lib.FcStrListCreate.restype = V
lib.FcStrListNext.restype = ctypes.c_char_p
lib.FcStrListCreate.argtypes = [V]
lib.FcStrListNext.argtypes = [V]
lib.FcLangSetGetLangs.argtypes = [V]
TYPES = {3: "string", 9: "langset"}


def langs(p):
    out = []
    for i in range(16):
        v = FcValue(); b = ctypes.c_int()
        r = lib.FcPatternGetWithBinding(p, b"lang", i, ctypes.byref(v), ctypes.byref(b))
        if r != 0:
            break
        bind = {0: "w", 1: "s", 2: "same"}.get(b.value, "?")
        if v.type == 3:
            out.append(f'"{v.u.s.decode()}"({bind})')
        elif v.type == 8:
            ss = lib.FcLangSetGetLangs(v.u.p)
            it = lib.FcStrListCreate(ss); names = []
            while True:
                s = lib.FcStrListNext(it)
                if not s:
                    break
                names.append(s.decode())
            out.append("langset{" + ",".join(names) + f"}}({bind})")
        else:
            out.append(f"type{v.type}({bind})")
    return " ".join(out)


print("fontconfig", lib.FcGetVersion())
for lang in args:
    p = V(lib.FcPatternCreate())
    lib.FcPatternAddBool(p, b"scalable", 1)
    lib.FcPatternAddString(p, b"family", family.encode())
    if generic:
        lib.FcPatternAddString(p, b"family", generic.encode())
    if chars:
        cs = V(lib.FcCharSetCreate())
        for c in chars:
            lib.FcCharSetAddChar(cs, ctypes.c_uint32(c))
        lib.FcPatternAddCharSet(p, b"charset", cs)
    if lang != "-":
        lib.FcPatternAddString(p, b"lang", lang.encode())
    lib.FcPatternAddInteger(p, b"spacing", 0); lib.FcPatternAddInteger(p, b"width", 100)
    if weight is not None:
        lib.FcPatternAddInteger(p, b"weight", weight)
    cfg = V(lib.FcConfigGetCurrent())
    lib.FcConfigSubstitute(cfg, p, 0)
    lib.FcDefaultSubstitute(p)
    after = langs(p)
    res = ctypes.c_int(0)
    best = V(lib.FcFontMatch(cfg, p, ctypes.byref(res)))
    fmt = V(lib.FcPatternFormat(best, b"%{family[0]} | %{file} | %{index}"))
    print(f"asked {lang!r:9} -> lang after subst: {after:45} => {ctypes.cast(fmt, ctypes.c_char_p).value.decode()}")
