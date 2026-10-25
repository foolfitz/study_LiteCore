#!/usr/bin/env python3
"""Read the finite autosave artifacts without starting services or browsers."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PROBE=ROOT/'tools/probe_calc_autosave.py'

def required():
    tree=ast.parse(PROBE.read_text());values={}
    for n in ast.walk(tree):
        if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and isinstance(n.iter,(ast.List,ast.Tuple)):
            v=[x.value for x in n.iter.elts if isinstance(x,ast.Constant) and isinstance(x.value,str)]
            if len(v)==len(n.iter.elts):values[n.target.id]=v
    ids=[]
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Name) or n.func.id!='check':continue
        a=n.args[0]
        if isinstance(a,ast.Constant) and isinstance(a.value,str):ids.append(a.value)
        elif isinstance(a,ast.BinOp) and isinstance(a.op,ast.Add) and isinstance(a.left,ast.Name) and isinstance(a.right,ast.Constant):
            ids.extend(v+a.right.value for v in values[a.left.id])
        else:raise ValueError('unsupported check population; update reader to follow executable truth')
    if not ids or len(ids)!=len(set(ids)):raise ValueError('empty/duplicate executable population')
    return set(ids)

def validate(report,repeats=3):
    assert report['toolSha256']==hashlib.sha256(PROBE.read_bytes()).hexdigest(),'wrong tool identity'
    runs=report['runs'];expected={(b,n) for b in ['chrome','firefox'] for n in range(1,repeats+1)}
    assert len(runs)==len(expected) and {(r['browser'],r['repeat']) for r in runs}==expected,'wrong run population'
    wanted=required()
    for run in runs:
        checks=run['checks']
        assert not run['error'] and len(checks)==len(wanted) and {c['id'] for c in checks}==wanted,'missing/duplicate checks'
        assert all(c['pass'] is True for c in checks),'false check'
        assert len(run['files'])==3 and len({f['path'] for f in run['files']})==3,'missing ODS snapshots'
    return len(runs)*len(wanted)

def artifacts(out,report):
    identity=json.loads((out/'mirror-sources.json').read_text());sources=identity['sha256'];assert sources,'empty identity'
    for relative,sha in sources.items():
        p=ROOT/'web'/relative if relative in ['ods-editor.html','ods-editor-app.js'] else ROOT/relative
        if relative.startswith('profiles/'):p=ROOT/'dist'/relative
        assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==sha,'candidate changed: '+relative
    if identity.get('engineSha256'):
        binding=json.loads((out/'v2-runner.json').read_text());profile=Path(binding['profile'])
        assert binding['wrapperSha256']==hashlib.sha256(PROBE.with_name('probe_calc_autosave_v2.py').read_bytes()).hexdigest(),'wrong v2 wrapper'
        assert binding['runnerSha256']==report['toolSha256'],'wrong autosave runner binding'
        manifest=json.loads((profile/'sdk-manifest.json').read_text())
        assert manifest['profile']=='ods-editor-v2' and 'cell-range-formatting' in manifest['capabilities'],'wrong successor'
        for name,sha in identity['engineSha256'].items():
            assert hashlib.sha256((profile/name).read_bytes()).hexdigest()==sha,'changed successor: '+name
    ns={'t':'urn:oasis:names:tc:opendocument:xmlns:table:1.0','text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
    for r in report['runs']:
        for f in r['files']:
            p=out/f['path'];assert p.parent==out,'unexpected artifact path'
            assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],'changed ODS bytes'
            with zipfile.ZipFile(p) as z:doc=ET.fromstring(z.read('content.xml'))
            table=doc.find('.//t:table',ns);rows=table.findall('t:table-row',ns)
            cells=rows[1].findall('t:table-cell',ns)
            text=lambda c:'\n'.join(''.join(n.itertext()) for n in c.findall('text:p',ns))
            expected='Idle '+r['browser']+' '+str(r['repeat']) if p.stem.endswith('-idle') else 'Hidden checkpoint' if p.stem.endswith('-hidden') else 'Final checkpoint'
            assert text(cells[0])=='鄰格必須保留' and text(cells[1])==expected,'ODS XML mismatch'

def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--red-cases',action='store_true');a=p.parse_args()
    report=json.loads((a.out/'report.json').read_text());total=validate(report);artifacts(a.out,report)
    controls=[]
    if a.red_cases:
        def test(name,mutate):
            r=copy.deepcopy(report);mutate(r)
            try:validate(r)
            except (AssertionError,KeyError,ValueError):controls.append({'id':name,'rejected':True});return
            raise AssertionError('red control passed: '+name)
        test('empty-runs',lambda r:r.update(runs=[]))
        test('missing-browser',lambda r:r.update(runs=[x for x in r['runs'] if x['browser']=='chrome']))
        test('empty-checks',lambda r:r['runs'][0].update(checks=[]))
        test('missing-check',lambda r:r['runs'][0]['checks'].pop())
        test('false-check',lambda r:r['runs'][0]['checks'][0].update({'pass':False}))
        test('wrong-tool',lambda r:r.update(toolSha256='0'*64))
    print(json.dumps({'pass':True,'checks':total,'perRun':len(required()),'redControls':controls},indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
