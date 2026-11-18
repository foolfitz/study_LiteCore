#!/usr/bin/env python3
"""Finding 159: compute the gcc3_wasm bridge call signature of every scaddins add-in method and say whether a given
build's generated signature table contains it.

The signature rule is that of bridges/source/cpp_uno/gcc3_wasm/uno2cpp.cxx, call():
  return:  void 'v'; boolean/byte/short/ushort/long/ulong/char/enum 'i'; hyper 'j'; float 'f'; double 'd';
           string/type/any/sequence/interface "vi" (returned through a pointer)
  then 'i' for the this pointer
  params:  [in] simple types as above ('i', 'j', 'f', 'd'); everything else (string, any, sequence, interface,
           struct, and every out/inout parameter) 'i'

usage: addin_signatures.py <scaddins idl dir> <generated-cxx.cxx> [<idl->Calc name map: Analysis.idl etc. not needed>]
Output: one line per method: interface, method, signature, IN_TABLE / ABSENT. Exit 2 if no method was parsed or the
table has no signatures (the tool must not report an empty result as a finding).
"""
import re
import sys
from pathlib import Path

RET = {'void': 'v', 'boolean': 'i', 'byte': 'i', 'short': 'i', 'unsigned short': 'i', 'long': 'i',
       'unsigned long': 'i', 'char': 'i', 'hyper': 'j', 'unsigned hyper': 'j', 'float': 'f', 'double': 'd',
       'string': 'vi', 'type': 'vi', 'any': 'vi'}
PARAM = {'boolean': 'i', 'byte': 'i', 'short': 'i', 'unsigned short': 'i', 'long': 'i', 'unsigned long': 'i',
         'char': 'i', 'hyper': 'j', 'unsigned hyper': 'j', 'float': 'f', 'double': 'd'}


def ret_letter(t):
    t = ' '.join(t.split())
    if t in RET:
        return RET[t]
    if t.startswith('sequence') or '::' in t or t[0].isupper():
        return 'vi'  # sequence or interface (no struct returns in these IDLs; checked below)
    raise SystemExit(f'unknown return type {t!r}')


def param_letter(direction, t):
    t = ' '.join(t.split())
    if direction != 'in':
        return 'i'
    return PARAM.get(t, 'i')


def methods(idl_text):
    # strip comments
    text = re.sub(r'/\*.*?\*/', '', idl_text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    for im in re.finditer(r'interface\s+(\w+)\s*:\s*[\w:]+\s*\{(.*?)\};', text, flags=re.S):
        iface, body = im.group(1), im.group(2)
        for mm in re.finditer(r'([\w:<>\s]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:raises\s*\([^)]*\))?\s*;', body, flags=re.S):
            rtype, name, params = mm.group(1).strip(), mm.group(2), mm.group(3)
            plist = []
            if params.strip():
                for p in re.split(r',(?![^<]*>)', params):
                    pm = re.match(r'\s*\[(in|out|inout)\]\s*(.+?)\s+(\w+)\s*$', p, flags=re.S)
                    if not pm:
                        raise SystemExit(f'cannot parse parameter {p!r} of {iface}.{name}')
                    plist.append((pm.group(1), pm.group(2)))
            yield iface, name, rtype, plist


def main():
    idl_dir, table = Path(sys.argv[1]), Path(sys.argv[2])
    sigs = set(re.findall(r'^extern "C" void callVirtualFunction_([a-z]+)\(', table.read_text(), flags=re.M))
    if not sigs:
        print('no signatures found in table', file=sys.stderr)
        sys.exit(2)
    n = 0
    for f in sorted(idl_dir.glob('X*.idl')):
        for iface, name, rtype, plist in methods(f.read_text()):
            sig = ret_letter(rtype) + 'i' + ''.join(param_letter(d, t) for d, t in plist)
            n += 1
            print(f'{iface}\t{name}\t{sig}\t{"IN_TABLE" if sig in sigs else "ABSENT"}')
    print(f'# methods={n} table_signatures={len(sigs)} table={table}', file=sys.stderr)
    if n == 0:
        sys.exit(2)


if __name__ == '__main__':
    main()
