#!/usr/bin/env python3
"""Synthetic instrument checks, not actual040/browser evidence."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import judge_v23_remaining as j
import v23_remaining_cases as c
HASHES={k:'a'*64 for k in c.ARTIFACTS}
INPUTS={'frame':c.FRAME_SHA256,'largest':'c'*64}


def sample(arm='html-positive'):
    def request(i,op,payload=None,gen=1):
        return {'generation':gen,'requestId':i,'operation':op,'payload':payload or {},'at':float(i)}
    def reply(i,result=None,gen=1):
        return {'generation':gen,'message':{'requestId':i,'ok':True,'result':result or {}}}
    step=lambda n:{'name':n,'ok':True,'startedAt':0,'finishedAt':1}
    r={'profile':c.PROFILE,'artifacts':HASHES.copy(),'arm':arm,'complete':True,
       'fixtures':{'frame':{'sha256':INPUTS['frame']}},'steps':[step('open-frame')],
       'preSelection':{'selectionType':'complex'},'events':[],'requests':[
        request(1,'init'),request(2,'open',{'buffer':{'sha256':c.FRAME_SHA256}})],
       'responses':[reply(1),reply(2,{'documentHandle':7})]}
    if arm=='frame':
        r['steps'].append(step('frame-close'));r['requests'].append(request(3,'close',{'documentHandle':7}));r['responses'].append(reply(3))
        return r
    r['steps'] += [step(n) for n in ('040-anchor','040-select','040-complex-read')]
    kind=9 if arm=='html-positive' else 3
    r['requests'] += [request(3,'editorGetStateV2'),request(4,'search',{'query':'IV-ASCHAR','documentHandle':7}),
        request(5,'editorSelectRangeV2',{'documentHandle':7,'startXTwips':10,'startYTwips':25,'endXTwips':8010,'endYTwips':25}),
        request(6,'getSelection',{'documentHandle':7}),request(7,'v23Diagnostic',{'kind':kind})]
    r['responses'] += [reply(3),reply(4,{'found':True,'selections':[{'rectangles':'10,20,100,10'}]}),reply(5),reply(6,{'selectionType':'complex'})]
    r['events']=[{'generation':1,'message':{'detail':{'type':'v23-control','kind':kind,'requestId':7}}}]
    if kind==9:
        html='<p>IV-ASCHAR <img src="data:image/png;base64,AA=="></p>'
        r['control']={'result':{'html':html,'bytes':len(html.encode())}}
        r['events'].append({'generation':1,'message':{'detail':{'type':'v23-html-return','requestId':7,'html':html,'bytes':len(html.encode())}}})
        r['responses'].append(reply(7,r['control']['result'].copy()))
        r['requests'].append(request(8,'editorGetStateV2'));r['responses'].append(reply(8))
    else:
        r['control']={'error':{'code':'TIMEOUT','details':{'timeoutMs':30000}},'stateAfter':{'state':'recoverable-error'},'startedAt':6.5,'finishedAt':30008}
        r['cancels']=[{'kind':'cancel','generation':1,'requestId':7,'at':30007}]
        r['recovered']={'state':'ready'};r['workers']=[{'terminatedAt':30009},{'createdAt':30010}]
        r['steps'] += [step('040-restart'),step('040-recovery-save')]
        r['requests'] += [request(1,'init',gen=2),request(2,'open',{'buffer':{'sha256':c.FRAME_SHA256}},2),request(3,'editorGetStateV2',gen=2),request(4,'save',gen=2)]
        r['responses'] += [reply(1,gen=2),reply(2,{'documentHandle':7},2),reply(3,gen=2),reply(4,gen=2)]
    return r


class Checks(unittest.TestCase):
    def verdict(self,r):return j.judge(r,HASHES,INPUTS,c.PROFILE)['verdict']
    def test_synthetic_positive(self):
        for a in ('frame','html-positive','html-negative'):self.assertEqual(self.verdict(sample(a)),j.PASS)
    def test_none_precondition_ne(self):
        r=sample('html-negative');r['preSelection']['selectionType']='none';self.assertEqual(self.verdict(r),j.NE)
    def test_sibling_cannot_prove_literal(self):
        r=sample();r['events'].pop();self.assertEqual(self.verdict(r),j.NE)
    def test_wrong_html_fails(self):
        r=sample();r['control']['result']['html']='<p>IV-ASCHAR</p>';self.assertNotEqual(self.verdict(r),j.PASS)
    def test_returning_negative_fails(self):
        r=sample('html-negative');r['control']['error']['code']='DIAGNOSTIC_CONTROL_RETURNED';self.assertEqual(self.verdict(r),j.FAIL)
    def test_wrong_artifact_and_fixture(self):
        r=sample();r['profile']='e2-editor-v22';self.assertEqual(self.verdict(r),j.FAIL)
        r=sample();r['fixtures']['frame']['sha256']='wrong';self.assertEqual(self.verdict(r),j.FAIL)
    def test_close_recovery_is_not_destroy_return(self):
        r=sample('frame');r['responses'][2]['message']['ok']=False;self.assertEqual(self.verdict(r),j.FAIL)
    def test_wire_cannot_be_overridden_by_page_labels(self):
        r=sample('html-negative');r['responses'].append({'generation':1,'message':{'requestId':7,'ok':False,'error':{'code':'DIAGNOSTIC_CONTROL_RETURNED'}}})
        self.assertEqual(self.verdict(r),j.FAIL)
        r=sample();r['requests'][4]['payload']['endXTwips']=99;self.assertEqual(self.verdict(r),j.FAIL)
        r=sample();r['responses'][5]['message']['result']['selectionType']='none';self.assertEqual(self.verdict(r),j.NE)
    def test_wire_document_attribution(self):
        r=sample();r['requests'][4]['payload']['documentHandle']=8;self.assertEqual(self.verdict(r),j.FAIL)
    def test_wrong_document_close_red(self):
        r=sample('frame');r['requests'][-1]['payload']['documentHandle']=99;self.assertEqual(self.verdict(r),j.FAIL)
        r=sample('frame');r['requests'][-1]['generation']=2;self.assertNotEqual(self.verdict(r),j.PASS)
    def test_extra_mutation_after_complex_red(self):
        r=sample();r['requests'].insert(6,{'generation':1,'requestId':6.5,'operation':'insertText','payload':{'text':'x'}})
        self.assertEqual(self.verdict(r),j.FAIL)
        r=sample();r['requests'].insert(6,{'generation':1,'requestId':6.5,'operation':'editorGetStateV2'})
        self.assertEqual(self.verdict(r),j.FAIL)
    def test_fabricated_timeout_lacks_sdk_cancel(self):
        r=sample('html-negative');r['control']['finishedAt']=8;r['cancels']=[];self.assertEqual(self.verdict(r),j.NE)
        r=sample('html-negative');r['cancels'][0]['requestId']=999;self.assertEqual(self.verdict(r),j.FAIL)
        r=sample('html-negative');r['cancels'][0]['at']=31000;self.assertEqual(self.verdict(r),j.FAIL)
    def test_import_graph_and_executed_mirror_controls(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            mirror=Path(tmp)
            served=c.served_instruments()
            for name in served:
                source=c.PROJECT/({'e2-editor.html':'web/v23-remaining.html','v23-remaining.js':'web/v23-remaining.js'}.get(name,name))
                target=mirror/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
            report={'instrument':{str(p.relative_to(c.PROJECT)):c.sha(p) for p in c.instrument_files()},
                    'mirrorInstrument':served.copy(),'runs':[{'page':{'instrumentServed':{k:served[k] for k in ('e2-editor.html','v23-remaining.js')}}}]}
            c.verify_bindings(report,mirror)
            for key in ('instrument','mirrorInstrument'):
                red=copy.deepcopy(report);red.pop(key)
                with self.assertRaises(ValueError):c.verify_bindings(red,mirror)
            red=copy.deepcopy(report);red['instrument']['sdk/document-sdk.js']='wrong'
            with self.assertRaises(ValueError):c.verify_bindings(red,mirror)
            for name in ('e2-editor.html','v23-remaining.js','sdk/document-sdk.js'):
                target=mirror/name;raw=target.read_bytes();target.write_bytes(raw+b' changed')
                with self.assertRaises(ValueError):c.verify_bindings(report,mirror)
                target.write_bytes(raw)
            red=copy.deepcopy(report);red['runs'][0]['page']['instrumentServed']['e2-editor.html']='wrong'
            with self.assertRaises(ValueError):c.verify_bindings(red,mirror)
    def test_actual_corpus_nonempty_and_frame_xml(self):
        files,pop=c.fixtures();self.assertEqual(pop['selected']['expected']['pageCount'],100)
        self.assertTrue(files['frame'].is_file());self.assertTrue(pop['excluded'])

if __name__=='__main__':unittest.main()
