#!/usr/bin/env python3
"""Read the saved Files evidence, named case population, XML and cleanup."""
import ast
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
TOOLS=ROOT.parents[2]/'wasm_sdk_probe/tools'
sys.path.insert(0,str(TOOLS))
from run_calc_cell_native import cells_from_xml


def template(n):
    if isinstance(n,ast.Constant) and isinstance(n.value,str):return n.value
    if isinstance(n,ast.Name) and n.id in ('browser','fmt'):return '{'+n.id+'}'
    if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Add):
        a,b=template(n.left),template(n.right)
        if a is not None and b is not None:return a+b
    return None


def required():
    manifest=json.loads((ROOT/'input-range-host-01/fixture/manifest.json').read_text())
    names=set()
    for n in ast.walk(ast.parse((TOOLS/'probe_calc_input_range_host.py').read_text())):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='check' and n.args:
            t=template(n.args[0])
            assert t is not None
            for b in ('chrome','firefox'):
                for f in manifest['formats']:names.add(t.format(browser=b,fmt=f))
    # Setup checks from the inherited executable run(), not a mirrored list.
    tree=ast.parse((TOOLS/'run_calc_editor_host.py').read_text())
    method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='run')
    for n in ast.walk(method):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='check' and isinstance(n.args[0],ast.Constant):names.add(n.args[0].value)
    return names


def score(report):
    bad=[];checks=report.get('checks',[]);ids=[c['id'] for c in checks]
    if not report.get('ok') or report.get('error') or not checks or any(c.get('ok') is not True for c in checks):bad.append('failed/empty host checks')
    if set(ids)!=required() or len(ids)!=len(set(ids)):bad.append('missing/extra/duplicate cases')
    if {r['browser'] for r in report.get('runs',[])}!={'chrome','firefox'}:bad.append('missing browser')
    release=json.loads((ROOT/'release.json').read_text())
    for r in report.get('runs',[]):
        if '/'+release['buildId']+'-' not in r['entry']['landed']:bad.append('served package mismatch')
    return bad


report=json.loads((ROOT/'input-range-host-01/report.json').read_text());assert not score(report),score(report)
tiles=0
for b in ('chrome','firefox'):
    s=json.loads((ROOT/f'input-range-host-01/{b}-input-tiles.json').read_text())
    assert s['tiles'] and s['visibleTiles']>0 and all(t['matched'] for t in s['tiles']) and s['revision']==s['context']['revision']
    tiles+=len(s['tiles'])
    _,cells=cells_from_xml(ROOT/f'input-range-host-01/{b}-saved.ods')
    text=lambda c,r:''.join(cells[(0,c,r)].itertext())
    assert text(0,0)=='Host active '+b and text(1,1)=='Host replacement '+b and text(0,1)=='鄰格必須保留'
    save=next(c['raw'] for c in report['checks'] if c['id']==b+'/manual-save')
    assert len(save)==1 and save[0]['outcome']=='saved' and save[0]['trigger']=='manual'
identity=json.loads((ROOT/'post-test-identity.json').read_text())
assert identity['installedVersion']=='0.2.36' and identity['engineEqualsArchive'] and identity['hostClean'] and identity['temporaryUserAbsent'] and identity['ownedFolderStatus']==404
assert identity['lockFileIdsBefore']==identity['lockFileIdsAfter']==(ROOT/'locks-before.txt').read_text().split()
states=lambda n:{p['name']:p['status'] for p in json.loads((ROOT/n).read_text())['raw']}
assert states('ddev-before.json')==states('ddev-after.json') and states('ddev-after.json')['litecore']=='running'
assert json.loads((ROOT/'owner-document-before.json').read_text())==json.loads((ROOT/'owner-document-after.json').read_text())
print(json.dumps({'checks':len(report['checks']),'views':2,'tiles':tiles,'problems':[]}))
for name,mutate in [('empty checks',lambda r:r.update(checks=[])),('missing case',lambda r:r['checks'].pop()),('false check',lambda r:r['checks'][0].update(ok=False)),('missing browser',lambda r:r.update(runs=r['runs'][:1]))]:
    broken=copy.deepcopy(report);mutate(broken);assert score(broken);print('RED '+name)
