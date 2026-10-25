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
    step=lambda n:{'name':n,'ok':True,'startedAt':0,'finishedAt':1}
    r={'profile':c.PROFILE,'artifacts':HASHES.copy(),'arm':arm,'complete':True,
       'fixtures':{'frame':{'sha256':INPUTS['frame']}},'steps':[step(n) for n in
       ('open-frame','040-anchor','040-select','040-complex-read')],
       'preSelection':{'selectionType':'complex'},'events':[],'requests':[],'responses':[]}
    if arm=='frame':
        r['steps'].append(step('frame-close'))
        r['requests']=[{'generation':1,'operation':'close','requestId':5}]
        r['responses']=[{'generation':1,'message':{'requestId':5,'ok':True,'result':{}}}]
        r['requests'].append({'generation':1,'requestId':1,'operation':'open','payload':{'buffer':{'sha256':c.FRAME_SHA256}}})
        r['responses'].append({'generation':1,'message':{'requestId':1,'ok':True,'result':{}}})
        return r
    kind=9 if arm=='html-positive' else 3
    r['requests']=[{'generation':1,'operation':'v23Diagnostic','requestId':5,'payload':{'kind':kind}}]
    r['events']=[{'generation':1,'message':{'detail':{'type':'v23-control','kind':kind,'requestId':5}}}]
    if kind==9:
        html='<p>IV-ASCHAR <img src="data:image/png;base64,AA=="></p>'
        r['control']={'result':{'html':html,'bytes':len(html.encode())}}
        r['events'].append({'generation':1,'message':{'detail':{'type':'v23-html-return','requestId':5,'html':html,'bytes':len(html.encode())}}})
    else:
        r['control']={'error':{'code':'TIMEOUT','details':{'timeoutMs':30000}},'stateAfter':{'state':'recoverable-error'}}
        r['recovered']={'state':'ready'}
        r['workers']=[{'terminatedAt':30001},{'createdAt':30002}]
        r['steps'] += [step('040-restart'),step('040-recovery-save')]
    # Raw wire setup and actual frame open, independent of page summaries.
    r['requests'][:0]=[
      {'generation':1,'requestId':1,'operation':'open','payload':{'buffer':{'sha256':c.FRAME_SHA256}}},
      {'generation':1,'requestId':2,'operation':'search','payload':{'query':'IV-ASCHAR'}},
      {'generation':1,'requestId':3,'operation':'editorSelectRangeV2','payload':{'startXTwips':10,'startYTwips':25,'endXTwips':8010,'endYTwips':25}},
      {'generation':1,'requestId':4,'operation':'getSelection'}]
    for i,result in [(1,{}),(2,{'found':True,'selections':[{'rectangles':'10,20,100,10'}]}),(3,{}),(4,{'selectionType':'complex'})]:
      r['responses'].append({'generation':1,'message':{'requestId':i,'ok':True,'result':result}})
    if kind==9:r['responses'].append({'generation':1,'message':{'requestId':5,'ok':True,'result':r['control']['result'].copy()}})
    else:
      r['requests'].append({'generation':2,'requestId':1,'operation':'open','payload':{'buffer':{'sha256':c.FRAME_SHA256}}})
      r['responses'].append({'generation':2,'message':{'requestId':1,'ok':True,'result':{}}})
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
        r=sample('frame');r['responses'][0]['message']['ok']=False;self.assertEqual(self.verdict(r),j.FAIL)
    def test_wire_cannot_be_overridden_by_page_labels(self):
        r=sample('html-negative');r['responses'].append({'generation':1,'message':{'requestId':5,'ok':False,'error':{'code':'DIAGNOSTIC_CONTROL_RETURNED'}}})
        self.assertEqual(self.verdict(r),j.FAIL)
        r=sample();r['requests'][2]['payload']['endXTwips']=99;self.assertEqual(self.verdict(r),j.FAIL)
        r=sample();r['responses'][3]['message']['result']['selectionType']='none';self.assertEqual(self.verdict(r),j.NE)
    def test_actual_corpus_nonempty_and_frame_xml(self):
        files,pop=c.fixtures();self.assertEqual(pop['selected']['expected']['pageCount'],100)
        self.assertTrue(files['frame'].is_file());self.assertTrue(pop['excluded'])

if __name__=='__main__':unittest.main()
