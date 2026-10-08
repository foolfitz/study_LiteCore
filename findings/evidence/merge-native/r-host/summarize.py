import json, re, sys, zipfile, hashlib
sys.path.insert(0, 'tools')
from odt_paragraphs import paragraph_texts, first_difference
R = sys.argv[1]; R0C = sys.argv[2]
def comment(u):
    m = re.search(r'"comment": *"([^"]+)"', str(u).replace('\\n', '\n').replace('\\"', '"'))
    return m.group(1) if m else None
def count(u):
    m = re.search(r"'count': '(\d+)'", str(u)); return m.group(1) if m else None
def cx(p):
    m = re.search(r"'cursor': '([^']+)'", str(p)); return m.group(1) if m else None
def content(p): return zipfile.ZipFile(p).read('content.xml')
orig = paragraph_texts(f"{R}/docs/original.odt")
for line in open(f"{R}/arms.jsonl"):
    a = json.loads(line)
    if 'case' not in a: continue
    c, arm, rnd = a['case'], a['arm'], a['round']
    out = [rnd, c, arm, 'placeOk', a.get('placementOk'), 'placed', cx(a.get('placed'))]
    if arm == 'key':
        out += ['undo', count(a.get('undoAfter')), comment(a.get('undoAfter')), 'after', cx(a.get('after'))]
        for p in a.get('laterPresses', []):
            out += ['| p%d' % p['press'], count(p.get('undo')) if 'count' in str(p.get('undo')) else '', comment(p.get('undo')), cx(p.get('after'))]
    if arm == 'b':
        out += ['eshapeStop', a.get('eshapeStop'), 'undo', count(a.get('undoAfter')), comment(a.get('undoAfter'))]
    print(*out)
print()
for rnd in (1, 2, 3):
    d = f"{R}/docs/r{rnd}"
    e02 = content(f"{d}-E02-key.odt")
    print(rnd, 'E02 key == R0c r1 E02 key bytes:', e02 == content(f"{R0C}/docs/r1-E02-key.odt"),
          '| Q01 key text == original:', first_difference(paragraph_texts(f"{d}-Q01-key.odt"), orig),
          '| Q01 key2 text == E02 key text:', first_difference(paragraph_texts(f"{d}-Q01-key2.odt"), paragraph_texts(f"{d}-E02-key.odt")),
          '| Q01 key2 bytes == E02 key bytes:', content(f"{d}-Q01-key2.odt") == e02,
          '| Q02 key text==orig:', first_difference(paragraph_texts(f"{d}-Q02-key.odt"), orig),
          '| Q03 key text==orig:', first_difference(paragraph_texts(f"{d}-Q03-key.odt"), orig),
          '| Q03 key bytes==orig:', content(f"{d}-Q03-key.odt") == content(f"{R}/docs/original.odt"))
