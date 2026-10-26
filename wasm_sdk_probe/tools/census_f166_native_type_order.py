#!/usr/bin/env python3
"""Finding 166 census: in which native S5 type cells did x land before the Shift step?

For each named run (run-01 posted Shift and x back to back; run-02 settled the Shift step
first) and every native-capable type cell, compare the after-save's paragraph text with one
prediction made from the pre-Shift shape alone: x typed over the pre-Shift caret or range,
which is what x-then-Shift produces.  It also counts shapes whose four Shift keys gave one
after-text.  Logical points are paragraph/code-point offsets from the retained native setup
names; a point that is not pN.M or pN.end (the wrap line end) is judged only by cross-key
equality.  Reads only; writes nothing unless --output is given."""
import argparse
import json
from pathlib import Path
import re
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import v23_feature_s_cases as source
from odt_paragraphs import paragraph_texts_from_xml
ROOT=source.ROOT
NATIVE=ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native'

def paragraphs(path):
    with zipfile.ZipFile(path) as z:return paragraph_texts_from_xml(z.read('content.xml'))

def point(name,texts):
    m=re.fullmatch(r'p(\d+)\.(\d+|end)',name)
    if not m:return None
    p=int(m.group(1));return p,(len(texts[p]) if m.group(2)=='end' else int(m.group(2)))

def typed_over_shape(setup,texts):
    """Paragraph text after typing x over the pre-Shift caret or range, or None if not derivable."""
    names=setup['logicalPointNames']
    if setup['method']=='click+Shift+Right x3':
        a=point(names[0],texts);b=a and (a[0],a[1]+3)
    elif setup['method']=='drag':a,b=point(names[0],texts),point(names[1],texts)
    else:a=b=point(setup['expectedMovingPointName'],texts)
    if a is None or b is None:return None
    (pa,oa),(pb,ob)=sorted([a,b])
    return texts[:pa]+[texts[pa][:oa]+'x'+texts[pb][ob:]]+texts[pb+1:]

def census(run):
    table=source.derive(source.read_rounds());setups={c['id']:c for c in table['cases']}
    rows={r['id']:r for r in (json.loads(l) for l in (NATIVE/run/'native.jsonl').read_text().splitlines() if l.strip()) if 'id' in r}
    cells=[];byshape={}
    for cell_id,row in sorted(rows.items()):
        if row.get('family')!='type':continue
        setup=setups[cell_id.rsplit('/',1)[0]]['setup']
        before=paragraphs(NATIVE/run/'saves'/row['beforeFile']);after=paragraphs(NATIVE/run/'saves'/row['afterFile'])
        predicted=typed_over_shape(setup,before)
        cells.append({'id':cell_id,'shape':row['shape'],'key':row['key'],
            'afterEqualsXTypedOverPreShiftShape':None if predicted is None else after==predicted,
            'afterSelection':row['after']['getTextSelection'],
            'betweenSelection':(row.get('between') or {}).get('getTextSelection')})
        byshape.setdefault(row['shape'],set()).add(tuple(after))
    derivable=[c for c in cells if c['afterEqualsXTypedOverPreShiftShape'] is not None]
    return {'run':run,'typeCells':len(cells),
            'derivable':len(derivable),'afterEqualsXTypedOverPreShiftShape':sum(c['afterEqualsXTypedOverPreShiftShape'] for c in derivable),
            'shapes':len(byshape),'shapesWithOneAfterTextAcrossKeys':sum(len(v)==1 for v in byshape.values()),
            'cells':cells}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+');p.add_argument('--output',type=Path)
    a=p.parse_args();result={'schema':1,'censuses':[census(r) for r in a.runs]}
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')
if __name__=='__main__':main()
