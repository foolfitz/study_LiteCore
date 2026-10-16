#!/usr/bin/env python3
"""Map wasm function indices of a stripped link to C++ names via a reference link that has a name section.

Method
  1. Parse both modules (types, imports, function/global/tag sections, code section, the reference's
     "name" custom section). The function index space counts imported functions first.
  2. Decode each body into a normalised instruction sequence. Immediates that depend on the link are
     replaced: `call f` -> the callee's signature, `call_indirect t` / block types -> the signature
     text, `ref.func`, data-segment and element indices dropped, `i32.const` values dropped (data
     addresses and table slots move between links), memarg offsets >= 65536 collapsed to "BIG"
     (folded data addresses). Everything else (local indices, branch depths, small memarg offsets,
     i64/f32/f64 constants, tag and table indices, global types) is kept. This is the LOOSE form.
     The STRICT form additionally keeps i32.const values in [-4096, 4096) (others as "BIG"),
     every memarg offset and global indices; small constants can still be table slots, so a strict
     disagreement alone does not mean different source. The DEEP form is the loose form with each
     direct callee replaced by the callee's own loose hash (imports by their import name, indirect
     calls by signature). Tiny bodies (thunks) usually need the deep form to be told apart.
  3. Shortlist reference candidates by (own signature, local declarations, body size within
     +-20% / 64 bytes), hash, compare. One loose match = "exact-unique". Several = narrowed by the
     strict hash, then by the deep hash; still several = "exact-ambiguous" (every name listed).
     An exact-unique match is then checked in reverse (the reference function against a target
     shortlist at the same level); if it hits more than the one target function it is demoted to
     "exact-ambiguous". strict_agrees / deep_agrees report whether the stricter forms agree too.
     None = "none"; the best opcode-sequence similarity over a wider shortlist is then reported
     as "near" evidence only, never as a mapping.
  4. Stack checks (tokens N@OFFSET given in stack order, innermost first): every OFFSET must lie in
     the body of function N (exit 2 otherwise); in the target, the instruction at a caller frame's
     OFFSET must be a call to the next-inner frame (direct) or a call_indirect (exit 2 if it is a
     direct call to something else). For a mapped caller, the instruction at the same ordinal in
     the reference body is checked to call the mapped callee: "confirmed-direct" / "indirect-both"
     / "mismatch".

Limits
  - A match means "identical normalised code", not "same source function": wasm-opt merges
    identical functions (the surviving name may be another instantiation or an ICF alias), and
    functions that differ only in dropped immediates (constants, callees) are separated only when
    the strict or deep form tells them apart.
  - A function whose code changed between the two links (different core sources, different
    inlining) does not match exactly; "near" scores are reported for orientation, not as names.
  - Only the instruction set met in these Emscripten links is decoded (MVP, legacy and new EH,
    threads 0xFE, 0xFC, SIMD 0xFD); an unknown opcode stops with an error naming its offset.

Read-only on the binaries. Exit status: 0 = at least one index mapped (exact-unique) and every
check passed; 1 = nothing mapped at all; 2 = a stack/offset check failed in the target;
3 = a mapped call edge disagrees in a reference (the matched caller does not call the matched
callee at the same instruction ordinal, or an indirect callee is not in the table).

Red cases run before use (2026-10-17, v21 against preguard-profiling): reference without a name
section -> exit 1; frame offset in another function's body -> exit 2; a skipped frame (143@552527
given as the caller of 21444) -> exit 2 and an edge mismatch; offset one byte past an instruction
start -> exit 2; --out on an existing file -> refused.

Usage
  map_functions.py TARGET.wasm --ref REF.wasm [--ref REF2.wasm] [--out FILE.json] [--sample K]
                   TOKEN [TOKEN ...]
  TOKEN is N or N@OFFSET (module byte offset of the frame, V8 columnNumber), in stack order.
  --out refuses to overwrite an existing file. --sample K adds a base rate: K target functions
  picked deterministically (every n-th defined function), and how many map exact-unique.
"""
from __future__ import annotations

import argparse
import bisect
import difflib
import hashlib
import json
import mmap
import os
import subprocess
import sys
from collections import defaultdict

sys.dont_write_bytecode = True

VALTYPE = {0x7F: 'i', 0x7E: 'I', 0x7D: 'f', 0x7C: 'F', 0x7B: 'v', 0x70: 'r', 0x6F: 'e'}


def uleb(b, p):
    r = 0
    s = 0
    while True:
        x = b[p]
        p += 1
        r |= (x & 0x7F) << s
        if x < 0x80:
            return r, p
        s += 7


def sleb(b, p):
    r = 0
    s = 0
    while True:
        x = b[p]
        p += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            if x & 0x40:
                r -= 1 << s
            return r, p


# immediate kinds for single-byte opcodes
K_NONE, K_BT, K_KEEP, K_CALL, K_CALLIND, K_GLOBAL, K_BRTABLE, K_MEM, K_I32, K_I64, K_F32, K_F64, \
    K_BYTE, K_SELT, K_REFFUNC, K_FC, K_FD, K_FE, K_TRYTABLE, K_KEEP2 = range(20)

KIND = {}
for _op in (0x00, 0x01, 0x05, 0x0A, 0x0B, 0x0F, 0x19, 0x1A, 0x1B, 0xD1):
    KIND[_op] = K_NONE
for _op in range(0x45, 0xC5):
    KIND[_op] = K_NONE
for _op in (0x02, 0x03, 0x04, 0x06):
    KIND[_op] = K_BT
for _op in (0x07, 0x08, 0x09, 0x0C, 0x0D, 0x18, 0x20, 0x21, 0x22, 0x25, 0x26):
    KIND[_op] = K_KEEP
KIND[0x0E] = K_BRTABLE
KIND[0x10] = K_CALL
KIND[0x12] = K_CALL
KIND[0x11] = K_CALLIND
KIND[0x13] = K_CALLIND
KIND[0x23] = K_GLOBAL
KIND[0x24] = K_GLOBAL
for _op in range(0x28, 0x3F):
    KIND[_op] = K_MEM
KIND[0x3F] = K_BYTE
KIND[0x40] = K_BYTE
KIND[0x41] = K_I32
KIND[0x42] = K_I64
KIND[0x43] = K_F32
KIND[0x44] = K_F64
KIND[0x1C] = K_SELT
KIND[0xD0] = K_BYTE
KIND[0xD2] = K_REFFUNC
KIND[0xFC] = K_FC
KIND[0xFD] = K_FD
KIND[0xFE] = K_FE
KIND[0x1F] = K_TRYTABLE


class DecodeError(Exception):
    pass


class Module:
    def __init__(self, path):
        self.path = path
        self.fh = open(path, 'rb')
        self.b = mmap.mmap(self.fh.fileno(), 0, access=mmap.ACCESS_READ)
        b = self.b
        if b[:4] != b'\0asm':
            raise SystemExit(f'{path}: not a wasm module')
        self.size = len(b)
        self.types = []          # signature text per type index
        self.func_types = []     # type index per function index (imports first)
        self.import_names = {}   # function index -> "module.field"
        self.nimp = 0
        self.global_types = []   # "i/I/f/F" + "m"/"c"
        self.code = []           # (entry_start, body_start, end, locals_text)
        self.names = {}
        self.exports = {}
        self.custom = []
        self.table_funcs = set()  # functions placed in a table (callable through call_indirect)
        p = 8
        n = len(b)
        while p < n:
            sid = b[p]
            p += 1
            sz, p = uleb(b, p)
            end = p + sz
            if sid == 1:
                self._types(p)
            elif sid == 2:
                self._imports(p)
            elif sid == 3:
                cnt, q = uleb(b, p)
                for _ in range(cnt):
                    t, q = uleb(b, q)
                    self.func_types.append(t)
            elif sid == 6:
                self._globals(p)
            elif sid == 7:
                cnt, q = uleb(b, p)
                for _ in range(cnt):
                    ln, q = uleb(b, q)
                    nm = bytes(b[q:q + ln]).decode('utf-8', 'replace')
                    q += ln
                    kind = b[q]
                    idx, q = uleb(b, q + 1)
                    if kind == 0:
                        self.exports.setdefault(idx, nm)
            elif sid == 9:
                self._elements(p)
            elif sid == 10:
                self._code(p)
            elif sid == 0:
                ln, q = uleb(b, p)
                nm = bytes(b[q:q + ln]).decode('utf-8', 'replace')
                self.custom.append(nm)
                if nm == 'name':
                    self._names(q + ln, end)
            p = end
        self.nfunc = len(self.func_types)
        if self.nfunc != self.nimp + len(self.code):
            raise SystemExit(f'{path}: function count mismatch')
        self.code_starts = [c[0] for c in self.code]

    def _const_expr(self, p):
        """Skip a constant expression; return (ref.func indices seen, position after `end`)."""
        b = self.b
        funcs = []
        while True:
            op = b[p]
            p += 1
            if op == 0x0B:
                return funcs, p
            if op in (0x41, 0x42):
                _, p = sleb(b, p)
            elif op == 0x43:
                p += 4
            elif op == 0x44:
                p += 8
            elif op == 0xD2:
                f, p = uleb(b, p)
                funcs.append(f)
            elif op in (0x23, 0xD0):
                _, p = uleb(b, p)
            elif op in (0x6A, 0x6B, 0x6C, 0x7C, 0x7D, 0x7E):
                pass
            else:
                raise SystemExit(f'{self.path}: unsupported constant-expression opcode 0x{op:02x}')

    def _elements(self, p):
        b = self.b
        cnt, p = uleb(b, p)
        for _ in range(cnt):
            flags, p = uleb(b, p)
            if flags & 2 and not flags & 1:
                _, p = uleb(b, p)                  # table index
            if not flags & 1:
                _, p = self._const_expr(p)         # offset
            if flags & 3:
                p += 1                             # elemkind / reftype
            n, p = uleb(b, p)
            for _ in range(n):
                if flags & 4:
                    fs, p = self._const_expr(p)
                    self.table_funcs.update(fs)
                else:
                    f, p = uleb(b, p)
                    self.table_funcs.add(f)

    def _valtypes(self, p):
        cnt, p = uleb(self.b, p)
        s = ''.join(VALTYPE.get(self.b[p + i], '?') for i in range(cnt))
        return s, p + cnt

    def _types(self, p):
        b = self.b
        cnt, p = uleb(b, p)
        for _ in range(cnt):
            if b[p] != 0x60:
                raise SystemExit(f'{self.path}: unsupported type form 0x{b[p]:02x}')
            pa, p = self._valtypes(p + 1)
            re_, p = self._valtypes(p)
            self.types.append(pa + '>' + re_)

    def _limits(self, p):
        flags = self.b[p]
        _, p = uleb(self.b, p + 1)
        if flags & 1:
            _, p = uleb(self.b, p)
        return p

    def _imports(self, p):
        b = self.b
        cnt, p = uleb(b, p)
        for _ in range(cnt):
            ln, p = uleb(b, p)
            mod = bytes(b[p:p + ln]).decode('utf-8', 'replace')
            p += ln
            ln, p = uleb(b, p)
            fld = bytes(b[p:p + ln]).decode('utf-8', 'replace')
            p += ln
            kind = b[p]
            p += 1
            if kind == 0:
                t, p = uleb(b, p)
                self.import_names[len(self.func_types)] = f'{mod}.{fld}'
                self.func_types.append(t)
                self.nimp += 1
            elif kind == 1:
                p = self._limits(p + 1)
            elif kind == 2:
                p = self._limits(p)
            elif kind == 3:
                self.global_types.append(VALTYPE.get(b[p], '?') + ('m' if b[p + 1] else 'c'))
                p += 2
            elif kind == 4:
                _, p = uleb(b, p + 1)
            else:
                raise SystemExit(f'{self.path}: unknown import kind {kind}')

    def _globals(self, p):
        b = self.b
        cnt, p = uleb(b, p)
        for _ in range(cnt):
            self.global_types.append(VALTYPE.get(b[p], '?') + ('m' if b[p + 1] else 'c'))
            p += 2
            # init expression: scan to the terminating end at depth 0
            while True:
                op = b[p]
                p += 1
                if op == 0x0B:
                    break
                if op in (0x41, 0x42):
                    _, p = sleb(b, p)
                elif op == 0x43:
                    p += 4
                elif op == 0x44:
                    p += 8
                elif op in (0x23, 0xD2, 0xD0):
                    _, p = uleb(b, p)
                elif op in (0x6A, 0x6B, 0x6C, 0x7C, 0x7D, 0x7E):
                    pass
                else:
                    raise SystemExit(f'{self.path}: unsupported global init opcode 0x{op:02x}')

    def _code(self, p):
        b = self.b
        cnt, p = uleb(b, p)
        for _ in range(cnt):
            sz, q = uleb(b, p)
            end = q + sz
            entry = q
            nl, q = uleb(b, q)
            loc = []
            for _ in range(nl):
                c, q = uleb(b, q)
                loc.append(f'{c}{VALTYPE.get(b[q], "?")}')
                q += 1
            self.code.append((entry, q, end, ','.join(loc)))
            p = end

    def _names(self, p, end):
        b = self.b
        while p < end:
            sub = b[p]
            sz, p = uleb(b, p + 1)
            if sub == 1:
                cnt, q = uleb(b, p)
                for _ in range(cnt):
                    idx, q = uleb(b, q)
                    ln, q = uleb(b, q)
                    self.names[idx] = bytes(b[q:q + ln]).decode('utf-8', 'replace')
                    q += ln
            p += sz

    # ---- helpers ----
    def defined(self, idx):
        return self.nimp <= idx < self.nfunc

    def entry(self, idx):
        return self.code[idx - self.nimp]

    def sig(self, idx):
        return self.types[self.func_types[idx]]

    def name(self, idx):
        if idx in self.import_names:
            return 'import:' + self.import_names[idx]
        return self.names.get(idx)

    def func_at(self, off):
        i = bisect.bisect_right(self.code_starts, off) - 1
        if i < 0:
            return None
        e = self.code[i]
        return self.nimp + i if e[0] <= off < e[2] else None

    # ---- decoder ----
    def decode(self, idx):
        """Return (loose_tokens, strict_extra, calls, insn_offsets).

        loose_tokens: list of tuples, one per instruction.
        strict_extra: list of values kept only by the strict form (parallel to loose_tokens, None
                      when the strict form adds nothing).
        calls: list of (insn_ordinal, opcode, callee_index_or_None, signature).
        insn_offsets: module offset of every instruction (parallel to loose_tokens).
        """
        b = self.b
        _, p, end, _ = self.entry(idx)
        types = self.types
        ftypes = self.func_types
        gtypes = self.global_types
        toks = []
        strict = []
        calls = []
        offs = []
        kind_of = KIND.get
        while p < end:
            o = p
            op = b[p]
            p += 1
            k = kind_of(op)
            si = None
            if k == K_NONE:
                t = (op,)
            elif k == K_KEEP:
                v, p = uleb(b, p)
                t = (op, v)
            elif k == K_MEM:
                al, p = uleb(b, p)
                mi = 0
                if al & 0x40:
                    mi, p = uleb(b, p)
                off, p = uleb(b, p)
                t = (op, al, mi, off if off < 0x10000 else 'BIG')
                si = off
            elif k == K_I32:
                v, p = sleb(b, p)
                t = (op,)
                si = v if -4096 <= v < 4096 else 'BIG'
            elif k == K_CALL:
                f, p = uleb(b, p)
                t = (op, types[ftypes[f]])
                calls.append((len(toks), op, f, types[ftypes[f]]))
            elif k == K_BT:
                if 0x40 <= b[p] < 0x80:
                    t = (op, b[p])
                    p += 1
                else:
                    v, p = sleb(b, p)
                    t = (op, types[v])
            elif k == K_CALLIND:
                ty, p = uleb(b, p)
                tb, p = uleb(b, p)
                t = (op, types[ty], tb)
                calls.append((len(toks), op, None, types[ty]))
            elif k == K_GLOBAL:
                g, p = uleb(b, p)
                t = (op, gtypes[g] if g < len(gtypes) else '?')
                si = g
            elif k == K_BRTABLE:
                cnt, p = uleb(b, p)
                lab = []
                for _ in range(cnt + 1):
                    v, p = uleb(b, p)
                    lab.append(v)
                t = (op, tuple(lab))
            elif k == K_I64:
                v, p = sleb(b, p)
                t = (op, v)
            elif k == K_F32:
                t = (op, bytes(b[p:p + 4]))
                p += 4
            elif k == K_F64:
                t = (op, bytes(b[p:p + 8]))
                p += 8
            elif k == K_BYTE:
                v, p = uleb(b, p)
                t = (op, v)
            elif k == K_SELT:
                cnt, p = uleb(b, p)
                t = (op, bytes(b[p:p + cnt]))
                p += cnt
            elif k == K_REFFUNC:
                _, p = uleb(b, p)
                t = (op,)
            elif k == K_FC:
                sub, p = uleb(b, p)
                if sub <= 7:
                    t = (op, sub)
                elif sub == 8:
                    _, p = uleb(b, p)
                    m, p = uleb(b, p)
                    t = (op, sub, m)
                elif sub in (9, 13):
                    _, p = uleb(b, p)
                    t = (op, sub)
                elif sub in (10, 12, 14):
                    a, p = uleb(b, p)
                    c, p = uleb(b, p)
                    t = (op, sub, c if sub == 12 else (a, c))
                elif sub in (11, 15, 16, 17):
                    a, p = uleb(b, p)
                    t = (op, sub, a)
                else:
                    raise DecodeError(f'0xFC {sub} at {o}')
            elif k == K_FE:
                sub, p = uleb(b, p)
                if sub == 3:
                    p += 1
                    t = (op, sub)
                else:
                    al, p = uleb(b, p)
                    off, p = uleb(b, p)
                    t = (op, sub, al, off if off < 0x10000 else 'BIG')
                    si = off
            elif k == K_FD:
                sub, p = uleb(b, p)
                if sub <= 11 or sub in (92, 93):
                    al, p = uleb(b, p)
                    off, p = uleb(b, p)
                    t = (op, sub, al, off if off < 0x10000 else 'BIG')
                    si = off
                elif sub in (12, 13):
                    t = (op, sub, bytes(b[p:p + 16]))
                    p += 16
                elif 21 <= sub <= 34:
                    t = (op, sub, b[p])
                    p += 1
                elif 84 <= sub <= 91:
                    al, p = uleb(b, p)
                    off, p = uleb(b, p)
                    t = (op, sub, al, off if off < 0x10000 else 'BIG', b[p])
                    p += 1
                    si = off
                else:
                    t = (op, sub)
            elif k == K_TRYTABLE:
                if 0x40 <= b[p] < 0x80:
                    bt = b[p]
                    p += 1
                else:
                    v, p = sleb(b, p)
                    bt = types[v]
                cnt, p = uleb(b, p)
                cl = []
                for _ in range(cnt):
                    ck = b[p]
                    p += 1
                    if ck in (0, 1):
                        tg, p = uleb(b, p)
                        lb, p = uleb(b, p)
                        cl.append((ck, tg, lb))
                    else:
                        lb, p = uleb(b, p)
                        cl.append((ck, lb))
                t = (op, bt, tuple(cl))
            else:
                raise DecodeError(f'unknown opcode 0x{op:02x} at module offset {o} in function {idx}')
            toks.append(t)
            strict.append(si)
            offs.append(o)
        if p != end:
            raise DecodeError(f'function {idx}: decode ran past the body end')
        return toks, strict, calls, offs


def h(obj):
    return hashlib.blake2b(repr(obj).encode(), digest_size=16).hexdigest()


class Hasher:
    """Caches decodes and hashes per module."""

    def __init__(self, mod):
        self.m = mod
        self.dec = {}
        self.loose = {}
        self.strict = {}
        self.deep = {}

    def decode(self, idx):
        d = self.dec.get(idx)
        if d is None:
            d = self.m.decode(idx)
            self.dec[idx] = d
        return d

    def key(self, idx):
        e = self.m.entry(idx)
        return (self.m.sig(idx), e[3])

    def loose_hash(self, idx):
        if idx in self.loose:
            return self.loose[idx]
        if not self.m.defined(idx):
            v = 'import:' + self.m.import_names.get(idx, '?')
        else:
            toks = self.decode(idx)[0]
            v = h((self.key(idx), toks))
        self.loose[idx] = v
        return v

    def strict_hash(self, idx):
        if idx not in self.strict:
            toks, st, _, _ = self.decode(idx)
            self.strict[idx] = h((self.key(idx), toks, st))
        return self.strict[idx]

    def deep_hash(self, idx):
        if idx not in self.deep:
            toks, st, calls, _ = self.decode(idx)
            callees = [(c[0], self.loose_hash(c[2]) if c[2] is not None else c[3]) for c in calls]
            self.deep[idx] = h((self.key(idx), toks, callees))
        return self.deep[idx]


def demangle(names):
    names = [n for n in names if n]
    if not names:
        return {}
    tool = os.environ.get('LLVM_CXXFILT') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'llvm-cxxfilt')
    cands = [tool, '/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/tools/emsdk/upstream/bin/llvm-cxxfilt',
             'llvm-cxxfilt', 'c++filt']
    for c in cands:
        try:
            r = subprocess.run([c], input='\n'.join(names) + '\n', capture_output=True, text=True,
                               timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        out = r.stdout.splitlines()
        if r.returncode == 0 and len(out) == len(names):
            return dict(zip(names, out))
    return {n: n for n in names}


class RefIndex:
    def __init__(self, mod):
        self.m = mod
        self.by_key = defaultdict(list)    # key -> sorted list of (size, idx)
        self.by_sig = defaultdict(list)
        for i, (entry, body, end, loc) in enumerate(mod.code):
            idx = mod.nimp + i
            sig = mod.sig(idx)
            sz = end - body
            self.by_key[(sig, loc)].append((sz, idx))
            self.by_sig[sig].append((sz, idx))
        for v in self.by_key.values():
            v.sort()
        for v in self.by_sig.values():
            v.sort()

    @staticmethod
    def window(lst, size, frac, slack):
        lo = size - max(slack, int(size * frac))
        hi = size + max(slack, int(size * frac))
        a = bisect.bisect_left(lst, (lo, -1))
        z = bisect.bisect_right(lst, (hi, 1 << 62))
        return [i for _, i in lst[a:z]]


def body_size(mod, idx):
    e = mod.entry(idx)
    return e[2] - e[1]


def _narrow(tidx, A, B, cands):
    """Members of `cands` (indices in B) whose hash equals A's function `tidx`, narrowed level by
    level. Returns (level, hits_at_that_level, loose_hits)."""
    lh = A.loose_hash(tidx)
    hits = [c for c in cands if B.loose_hash(c) == lh]
    if len(hits) <= 1:
        return 'loose', hits, hits
    sh = A.strict_hash(tidx)
    s_hits = [c for c in hits if B.strict_hash(c) == sh]
    if len(s_hits) == 1:
        return 'strict', s_hits, hits
    pool = s_hits or hits
    dh = A.deep_hash(tidx)
    d_hits = [c for c in pool if B.deep_hash(c) == dh]
    if len(d_hits) == 1:
        return 'deep', d_hits, hits
    return ('deep' if d_hits else ('strict' if s_hits else 'loose')), (d_hits or pool), hits


def match_one(tidx, T, R, RI, TI=None, near=True):
    tm = T.m
    if not tm.defined(tidx):
        nm = tm.import_names.get(tidx)
        hits = [i for i, n in R.m.import_names.items() if n == nm]
        return {'confidence': 'import', 'ref': hits, 'import': nm}
    key = T.key(tidx)
    size = body_size(tm, tidx)
    cands = RI.window(RI.by_key.get(key, []), size, 0.20, 64)
    level, hits, loose_hits = _narrow(tidx, T, R, cands)
    res = {'shortlist': len(cands)}
    if len(loose_hits) > 1:
        res['loose_hits'] = loose_hits
    if not hits:
        res.update(confidence='none', ref=[])
        if near:
            res['near'] = near_scores(tidx, T, R, RI)
        return res
    if len(hits) > 1:
        res.update(confidence='exact-ambiguous', ref=hits, by=level)
        return res
    r = hits[0]
    res.update(confidence='exact-unique', ref=hits, by=level)
    # agreement of the stricter forms (not required for the match, reported as strength)
    res['strict_agrees'] = T.strict_hash(tidx) == R.strict_hash(r)
    res['deep_agrees'] = T.deep_hash(tidx) == R.deep_hash(r)
    if TI is not None:
        # reverse direction: is the target function the only one in the target that the
        # reference function matches at the same level?
        tc = TI.window(TI.by_key.get(key, []), body_size(R.m, r), 0.20, 64)
        rlevel, rhits, _ = _narrow(r, R, T, tc)
        res['reverse'] = {'level': rlevel, 'target_hits': rhits, 'unique': rhits == [tidx]}
        if rhits != [tidx]:
            res['confidence'] = 'exact-ambiguous'
            res['note'] = 'unique from target to reference but not back'
    return res


def opseq(H, idx):
    return [t[0] if t[0] not in (0xFC, 0xFD, 0xFE) else (t[0] << 16) | t[1] for t in H.decode(idx)[0]]


def near_scores(tidx, T, R, RI, top=3):
    tm = T.m
    size = body_size(tm, tidx)
    cands = RI.window(RI.by_sig.get(tm.sig(tidx), []), size, 0.35, 128)
    if len(cands) > 4000:
        cands = RI.window(RI.by_sig.get(tm.sig(tidx), []), size, 0.10, 32)
    a = opseq(T, tidx)
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(a)
    scored = []
    for c in cands:
        bseq = opseq(R, c)
        sm.set_seq1(bseq)
        if sm.real_quick_ratio() < 0.6 or sm.quick_ratio() < 0.6:
            continue
        scored.append((sm.ratio(), c))
    scored.sort(reverse=True)
    return {'shortlist': len(cands),
            'best': [{'ref': c, 'ratio': round(r, 4)} for r, c in scored[:top]]}


def instr_ordinal(H, idx, off):
    offs = H.decode(idx)[3]
    i = bisect.bisect_left(offs, off)
    return i if i < len(offs) and offs[i] == off else None


def describe_call(H, idx, ordinal):
    toks = H.decode(idx)[0]
    t = toks[ordinal]
    for c in H.decode(idx)[2]:
        if c[0] == ordinal:
            return {'op': 'call' if c[1] in (0x10, 0x12) else 'call_indirect', 'callee': c[2],
                    'sig': c[3]}
    return {'op': f'0x{t[0]:02x}', 'callee': None}


def sha256_file(path):
    d = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            d.update(chunk)
    return d.hexdigest()


def run(args):
    T = Hasher(Module(args.target))
    frames = []
    for tok in args.tokens:
        if '@' in tok:
            a, b = tok.split('@', 1)
            frames.append((int(a), int(b)))
        else:
            frames.append((int(tok), None))
    tm = T.m
    out = {'argv': sys.argv[1:], 'tool_sha256': sha256_file(os.path.abspath(__file__)),
           'target': {'path': args.target, 'sha256': sha256_file(args.target), 'size': tm.size,
                      'functions': tm.nfunc, 'imported': tm.nimp,
                      'custom_sections': tm.custom, 'has_name_section': bool(tm.names)},
           'frames': [], 'references': []}
    fail = []
    # frame offset checks
    for k, (idx, off) in enumerate(frames):
        fr = {'index': idx, 'offset': off}
        if not (0 <= idx < tm.nfunc):
            fr['check'] = 'index-out-of-range'
            fail.append(f'frame {k}: index {idx} out of range')
        elif not tm.defined(idx):
            fr['check'] = 'imported'
        else:
            e = tm.entry(idx)
            fr['body'] = [e[1], e[2]]
            if off is not None:
                inside = e[1] <= off < e[2]
                fr['offset_in_body'] = inside
                if not inside:
                    fail.append(f'frame {k}: offset {off} not in body of {idx} '
                                f'[{e[1]},{e[2]}); it lies in {tm.func_at(off)}')
                else:
                    o = instr_ordinal(T, idx, off)
                    fr['instruction_boundary'] = o is not None
                    if o is None:
                        fail.append(f'frame {k}: offset {off} is not an instruction boundary in {idx}')
                    else:
                        fr['ordinal'] = o
                        if k == 0:
                            t = T.decode(idx)[0][o]
                            fr['instruction'] = {'opcode': f'0x{t[0]:02x}',
                                                 'loose_immediates': repr(t[1:]),
                                                 'strict_extra': repr(T.decode(idx)[1][o])}
                            fr['instruction'].update(
                                {k2: v for k2, v in describe_call(T, idx, o).items() if v is not None
                                 and k2 != 'op'})
                        if k > 0:
                            d = describe_call(T, idx, o)
                            fr['instruction'] = d
                            callee = frames[k - 1][0]
                            if d['op'] == 'call':
                                fr['calls_inner_frame'] = d['callee'] == callee
                                if d['callee'] != callee:
                                    fail.append(f'frame {k}: {idx}@{off} calls {d["callee"]}, '
                                                f'not the inner frame {callee}')
                            elif d['op'] == 'call_indirect':
                                fr['calls_inner_frame'] = 'indirect'
                                fr['inner_frame_sig_matches'] = d['sig'] == tm.sig(callee)
                                if d['sig'] != tm.sig(callee):
                                    fail.append(f'frame {k}: call_indirect sig {d["sig"]} != '
                                                f'{tm.sig(callee)} of inner frame {callee}')
                            else:
                                fail.append(f'frame {k}: {idx}@{off} is {d["op"]}, not a call')
        out['frames'].append(fr)
    uniq = list(dict.fromkeys(f[0] for f in frames))
    TI = RefIndex(tm)
    any_mapped = False
    for rpath in args.ref:
        R = Hasher(Module(rpath))
        rm = R.m
        RI = RefIndex(rm)
        rres = {'path': rpath, 'sha256': sha256_file(rpath), 'size': rm.size, 'functions': rm.nfunc,
                'imported': rm.nimp,
                'named_functions': len(rm.names), 'map': {}, 'edges': []}
        if not rm.names:
            rres['error'] = 'reference has no name section'
            out['references'].append(rres)
            continue
        maps = {}
        for idx in uniq:
            if not (0 <= idx < tm.nfunc):
                continue
            r = match_one(idx, T, R, RI, TI)
            maps[idx] = r
        allnames = set()
        for r in maps.values():
            for c in r.get('ref', []):
                allnames.add(rm.name(c))
            for nb in (r.get('near') or {}).get('best', []):
                allnames.add(rm.name(nb['ref']))
        dm = demangle(sorted(n for n in allnames if n and not n.startswith('import:')))
        for idx, r in maps.items():
            r['ref'] = [{'index': c, 'name': rm.name(c), 'demangled': dm.get(rm.name(c), rm.name(c))}
                        for c in r.get('ref', [])] if r['confidence'] != 'import' else r['ref']
            if 'loose_hits' in r:
                r['loose_hits'] = [{'index': c, 'name': rm.name(c)} for c in r['loose_hits']]
            if 'near' in r:
                for nb in r['near']['best']:
                    nb['name'] = rm.name(nb['ref'])
                    nb['demangled'] = dm.get(nb['name'], nb['name'])
            if r['confidence'] == 'exact-unique':
                any_mapped = True
            rres['map'][str(idx)] = r
        # call edges in stack order
        for k in range(1, len(frames)):
            callee, _ = frames[k - 1]
            caller, off = frames[k]
            e = {'caller': caller, 'callee': callee, 'offset': off}
            mc, me = maps.get(caller), maps.get(callee)
            rc = mc['ref'][0]['index'] if mc and mc['confidence'] == 'exact-unique' else None
            re_ = me['ref'][0]['index'] if me and me['confidence'] == 'exact-unique' else None
            e['ref_caller'] = rc
            e['ref_callee'] = re_
            if rc is not None and off is not None and tm.defined(caller):
                o = instr_ordinal(T, caller, off)
                if o is not None:
                    tgt = describe_call(T, caller, o)
                    ref = describe_call(R, rc, o)
                    e['target_instruction'] = tgt
                    e['ref_instruction'] = ref
                    if tgt['op'] == 'call' and ref['op'] == 'call':
                        if re_ is not None:
                            e['result'] = 'confirmed-direct' if ref['callee'] == re_ else 'mismatch'
                        else:
                            e['result'] = 'ref-calls-unmapped-callee'
                            e['ref_callee_from_call'] = {'index': ref['callee'],
                                                         'name': rm.name(ref['callee'])}
                    elif tgt['op'] == 'call_indirect' and ref['op'] == 'call_indirect':
                        # an indirect callee must sit in the table, in both links
                        e['callee_in_table'] = {'target': callee in tm.table_funcs,
                                                'ref': (re_ in rm.table_funcs) if re_ is not None
                                                else None}
                        ok = e['callee_in_table']['target'] and e['callee_in_table']['ref'] is not False \
                            and tgt['sig'] == ref['sig']
                        e['result'] = 'indirect-both' if ok else 'mismatch'
                    else:
                        e['result'] = 'mismatch'
            elif rc is not None and re_ is not None:
                calls = {c[2] for c in R.decode(rc)[2]}
                e['result'] = 'ref-caller-calls-callee' if re_ in calls else 'not-direct-in-ref'
            else:
                e['result'] = 'unmapped'
            rres['edges'].append(e)
        # names of unmapped callees seen from mapped callers (direct calls only)
        for e in rres['edges']:
            if e.get('ref_callee_from_call'):
                n = e['ref_callee_from_call']['name']
                e['ref_callee_from_call']['demangled'] = demangle([n]).get(n, n) if n else None
        if args.sample:
            step = max(1, len(tm.code) // args.sample)
            cnt = defaultdict(int)
            for i in range(0, len(tm.code), step)[:args.sample]:
                r = match_one(tm.nimp + i, T, R, RI, TI, near=False)
                cnt[r['confidence']] += 1
            rres['base_rate'] = {'sampled': sum(cnt.values()), 'step': step, **cnt}
        out['references'].append(rres)
        del R, RI
    summary = {}
    for idx in uniq:
        row = []
        for rres in out['references']:
            r = rres['map'].get(str(idx))
            if not r:
                continue
            row.append({'ref': os.path.basename(os.path.dirname(rres['path'])),
                        'confidence': r['confidence'],
                        'by': r.get('by'),
                        'ref_index': [x['index'] for x in r['ref']] if r['confidence'] != 'import'
                        else r['ref'],
                        'strict_agrees': r.get('strict_agrees'),
                        'deep_agrees': r.get('deep_agrees'),
                        'reverse_unique': (r.get('reverse') or {}).get('unique'),
                        'names': [x['demangled'] for x in r['ref']] if r['confidence'] != 'import'
                        else r.get('import')})
        summary[str(idx)] = row
    out['summary'] = summary
    mism = [f"{os.path.basename(os.path.dirname(rr['path']))}: {e['caller']} -> {e['callee']}"
            for rr in out['references'] for e in rr['edges'] if e['result'] == 'mismatch']
    out['checks'] = {'failures': fail, 'edge_mismatches': mism, 'any_exact_unique': any_mapped}
    status = 2 if fail else (3 if mism else (0 if any_mapped else 1))
    out['exit_status'] = status
    text = json.dumps(out, indent=1, ensure_ascii=False)
    if args.out:
        if os.path.exists(args.out):
            raise SystemExit(f'refusing to overwrite {args.out}')
        with open(args.out, 'x', encoding='utf-8') as f:
            f.write(text + '\n')
    print(text)
    for f in fail:
        print('CHECK FAILED: ' + f, file=sys.stderr)
    for m in mism:
        print('EDGE MISMATCH: ' + m, file=sys.stderr)
    if not any_mapped:
        print('SELF-CHECK FAILED: no index mapped exact-unique in any reference', file=sys.stderr)
    return status


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('target')
    ap.add_argument('--ref', action='append', required=True)
    ap.add_argument('--out')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('tokens', nargs='+')
    args = ap.parse_args()
    if args.out and os.path.exists(args.out):
        raise SystemExit(f'refusing to overwrite {args.out}')
    sys.exit(run(args))


if __name__ == '__main__':
    main()
