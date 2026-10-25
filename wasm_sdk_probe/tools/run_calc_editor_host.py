#!/usr/bin/env python3
"""Focused H-write on owned files/users; never clears the lock table."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import secrets
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

from check_m3_skeleton_open import Instance, DEFAULT_DDEV, FIXTURE, product_state
from check_m3_host_entry import LOCK_PROPS, host_record
from create_calc_edit_fixture import create
from probe_m3_gate0_coep import browser_login
from r7_support import evaluate, run_in_page
from run_browser_probe import ChromeSession
from run_calc_editor_browser import wait, select, type_text, key, double_click
from run_calc_cell_native import cells_from_xml
from run_e2_c_page_smoke import navigate, POINT_AT
from v21_shakedown_common import browser_lock, open_browser, close_browser

ODS = 'application/vnd.oasis.opendocument.spreadsheet'
ODT = 'application/vnd.oasis.opendocument.text'
NS = {'d':'DAV:', 'oc':'http://owncloud.org/ns', 'nc':'http://nextcloud.org/ns'}

# Observe actual page fetches after login. Never retain cookies, CSRF/lock tokens,
# passwords, authorization, or request bodies. If/If-Match facts are independent
# of the host's conclusion about whether a save succeeded.
OBSERVE = '''(() => {
 const original=window.fetch.bind(window); window.__cellHostRequests=[];
 window.fetch=async function(resource,options={}) {
  const method=(options.method||'GET').toUpperCase();
  if(!['PUT','UNLOCK'].includes(method)) return original(resource,options);
  const h=new Headers(options.headers), r={method,url:String(resource),
    contentType:h.get('Content-Type'),ifMatch:h.get('If-Match'),
    ifNoneMatch:h.get('If-None-Match'),withToken:h.has('If')};
  window.__cellHostRequests.push(r);
  try {const response=await original(resource,options);r.status=response.status;return response;}
  catch(error){r.error=String(error);throw error;}
 };
})();'''

class Harness:
    def __init__(self,out):
        self.out=out; self.instance=Instance(DEFAULT_DDEV)
        self.report={'checks':[], 'runs':[], 'cleanup':{}}
        self.folder='M4-cell-host-'+time.strftime('%Y%m%dT%H%M%S')
        self.user='m4_cell_'+secrets.token_hex(4); self.password=secrets.token_urlsafe(24)
        self.share=None; self.created_user=False; self.created_folder=False
        self.report['ownedFolder']=self.folder; self.report['temporaryUser']=self.user
        self.fixture=create(out/'fixture'); self.paths=[]

    def check(self,id,ok,raw):
        self.report['checks'].append({'id':id,'ok':bool(ok),'raw':raw})
        if not ok: raise AssertionError(id)

    def request(self,method,path,body=None,headers=None):
        url=self.instance.base+path
        request=urllib.request.Request(url,data=body,method=method,headers=headers or {})
        request.add_header('Authorization','Basic '+base64.b64encode(('admin:'+self.instance.password).encode()).decode())
        try:
            with urllib.request.urlopen(request,context=self.instance.tls,timeout=90) as r:
                return r.status,r.read(),dict(r.headers)
        except urllib.error.HTTPError as e: return e.code,e.read(),dict(e.headers)

    def dav(self,method,name,body=None,headers=None):
        return self.request(method,'/remote.php/dav/files/admin/'+urllib.parse.quote(name),body,headers)

    def ocs(self,method,path,data=None):
        code,body,_=self.request(method,'/ocs/v2.php/'+path+'?format=json',
            urllib.parse.urlencode(data).encode() if data is not None else None,
            {'OCS-APIRequest':'true','Content-Type':'application/x-www-form-urlencoded'})
        parsed=json.loads(body); meta=parsed['ocs']['meta']
        if code>=300 or meta['status']!='ok': raise RuntimeError(f'OCS {method} {path}: {code} {meta}')
        return parsed['ocs']['data']

    def props(self,name):
        code,body,_=self.dav('PROPFIND',name,LOCK_PROPS,{'Depth':'0','Content-Type':'application/xml'})
        root=ET.fromstring(body)
        token=root.findtext('.//d:locktoken/d:href',namespaces=NS)
        return {'status':code,'fileId':root.findtext('.//oc:fileid',namespaces=NS),
            'lock':root.findtext('.//nc:lock',namespaces=NS),'token':token}

    def leave(self,session,name):
        navigate(session,self.instance.base+'/apps/files/files?dir='+urllib.parse.quote('/'+self.folder),timeout=120)
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            p=self.props(name)
            if p['lock']!='1': return {k:v for k,v in p.items() if k!='token'}
            time.sleep(.3)
        # Record a real release failure. Cleanup later sends UNLOCK for this
        # runner's own files only, preserving every pre-existing lock.
        return {k:v for k,v in p.items() if k!='token'}

    def open_file(self,session,name,page,folder=True):
        directory='/'+self.folder if folder else '/'
        navigate(session,self.instance.base+'/apps/files/files?dir='+urllib.parse.quote(directory),timeout=120)
        leaf=name.split('/')[-1]
        selector=f'[data-cy-files-list-row-name={json.dumps(leaf)}] [data-cy-files-list-row-name-link]'
        wait(session,f'Boolean(document.querySelector({json.dumps(selector)}))',60)
        before=evaluate(session,'location.href'); session.click(selector)
        wait(session,f'location.pathname.endsWith({json.dumps("/"+page)})',90)
        return {'from':before,'landed':evaluate(session,'location.href')}

    def ready_calc(self,session):
        wait(session,'window.__calcEditor?.state?.state === "ready" && Boolean(window.__calcEditor.state.cell)',180)
        return evaluate(session,'window.__calcEditor.state')

    def calc_input(self,session,address,text):
        select(session,address); type_text(session,'#formula-input',text); key(session,'Enter')
        wait(session,'!window.__calcEditor.state.busy && !window.__calcEditor.state.editing')
        return evaluate(session,'window.__calcEditor.state.cell')

    def save(self,session,count):
        session.click('#save-button')
        wait(session,f'(()=>{{const x=JSON.parse(document.documentElement.getAttribute("data-litecore"));return x.saves.length>={count} && x.saves[{count-1}].settled;}})()',150)
        wait(session,'!window.__calcEditor.state.busy && !window.__calcEditor.state.saving')
        return host_record(session)

    def xml_cell(self,path,key):
        _,cells=cells_from_xml(path)
        return ''.join(cells[key].itertext())

    def admin_round(self,browser):
        run={'browser':browser}; self.report['runs'].append(run)
        session=open_browser(browser)
        name=self.folder+'/'+browser+'.ods'; writer=self.folder+'/'+browser+'.odt'
        self.paths.extend([name,writer])
        try:
            self.check(browser+'/upload-ods',self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS})[0] in (200,201,204),name)
            self.check(browser+'/upload-odt',self.dav('PUT',writer,FIXTURE.read_bytes(),{'Content-Type':ODT})[0] in (200,201,204),writer)
            browser_login(session,self.instance.base,self.instance.password)
            run['entry']=self.open_file(session,name,'ods-editor.html'); state=self.ready_calc(session)
            p=self.props(name); run['openedHost']=host_record(session)
            self.check(browser+'/files-writable-route',not state['readOnly'] and run['openedHost']['file']['writable'],run['entry'])
            self.check(browser+'/real-lock',p['lock']=='1' and bool(p['token']) and run['openedHost']['lock']['state']=='held', {k:v for k,v in p.items() if k!='token'})
            # A second client without the held token must be refused by DAV.
            code,_,_=self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS})
            self.check(browser+'/lock-refuses-unrelated-write',code==423,code)
            run_in_page(session,OBSERVE)
            marker='Host inline '+browser+' 中文'
            box=evaluate(session,'(()=>{const a=document.querySelector("#selection").getBoundingClientRect();return {x:a.x+a.width/2,y:a.y+a.height/2};})()')
            double_click(session,box['x'],box['y']); wait(session,'window.__calcEditor.state.editing === "inline"')
            type_text(session,'#cell-editor',marker);key(session,'Enter');wait(session,'!window.__calcEditor.state.busy')
            self.calc_input(session,'B1','17'); result=self.calc_input(session,'C1','=B1*5')
            self.check(browser+'/formula-before-save',result['value']==85,result)
            select(session,'B2')
            for fmt in ('bold','italic','underline'):
                session.click(f'[data-format="{fmt}"]');wait(session,'!window.__calcEditor.state.busy')
            saved=self.save(session,1);run['savedHost']=saved
            requests=evaluate(session,'window.__cellHostRequests');run['requests']=requests
            puts=[r for r in requests if r['method']=='PUT']
            self.check(browser+'/conditional-ods-put',len(puts)==1 and puts[0]['contentType']==ODS and bool(puts[0]['ifMatch']) and puts[0]['withToken'] and puts[0]['status'] in (200,201,204),puts)
            self.check(browser+'/host-saved',saved['saves'][0]['outcome']=='saved' and not evaluate(session,'window.__calcEditor.state.dirty'),saved['saves'])
            code,body,headers=self.dav('GET',name);path=self.out/(browser+'-server-saved.ods');path.write_bytes(body)
            run['serverSaved']={'status':code,'sha256':hashlib.sha256(body).hexdigest(),'contentType':headers.get('Content-Type')}
            self.check(browser+'/server-xml-input',self.xml_cell(path,(0,0,0))==marker, self.xml_cell(path,(0,0,0)))
            self.check(browser+'/server-xml-result',self.xml_cell(path,(0,2,0))=='85',self.xml_cell(path,(0,2,0)))
            self.check(browser+'/server-mimetype',headers.get('Content-Type','').split(';')[0]==ODS,headers.get('Content-Type'))
            release=self.leave(session,name);self.check(browser+'/leave-releases-own-lock',release['lock']!='1',release)
            run['reentry']=self.open_file(session,name,'ods-editor.html');self.ready_calc(session)
            cell=self.calc_read(session,'C1');self.check(browser+'/actual-host-reopen',cell['input']=='=B1*5' and cell['value']==85,cell)
            cell=self.calc_read(session,'B2');self.check(browser+'/host-reopen-formats',all(cell[f] for f in ('bold','italic','underline')),cell)
            self.calc_input(session,'A1','Conflict local '+browser)
            p=self.props(name);token=p['token']; token=token if token.startswith('opaquelocktoken:') else 'opaquelocktoken:'+token
            code,_,_=self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS,'If':f'(<{token}>)'})
            self.check(browser+'/external-owned-write',code in (200,201,204),code)
            conflict=self.save(session,1);run['conflictHost']=conflict
            copy=conflict['saves'][0].get('conflictCopy',{})
            self.check(browser+'/ods-conflict-copy',conflict['saves'][0]['outcome']=='copy' and copy.get('name','').endswith('.ods') and not copy.get('failed'),copy)
            copyname=self.folder+'/'+copy['name'];self.paths.append(copyname)
            code,original,_=self.dav('GET',name)
            self.check(browser+'/conflict-preserves-original',code==200 and original==self.fixture.read_bytes(),{'status':code,'sha256':hashlib.sha256(original).hexdigest()})
            code,copied,headers=self.dav('GET',copyname);cp=self.out/(browser+'-conflict-copy.ods');cp.write_bytes(copied)
            self.check(browser+'/conflict-preserves-local-input',code==200 and self.xml_cell(cp,(0,0,0))=='Conflict local '+browser,{'status':code,'cell':self.xml_cell(cp,(0,0,0)),'contentType':headers.get('Content-Type')})
            self.check(browser+'/copy-success-clears-dirty',not evaluate(session,'window.__calcEditor.state.dirty'),evaluate(session,'window.__calcEditor.state'))
            run['conflictRelease']=self.leave(session,name)
            # Existing Writer product path, same real Files action and save host.
            run['writerEntry']=self.open_file(session,writer,'e2-editor.html')
            wait(session,'document.querySelector("#state-pill")?.dataset.state === "ready"',180)
            evaluate(session,POINT_AT.replace('ARG_X','0.35').replace('ARG_Y','0.28'))
            wait(session,'document.querySelector("#s-latency").textContent.includes("定位游標")')
            revision=product_state(session)['revision']
            evaluate(session,'(()=>{document.querySelector("#text").value='+json.dumps('WRITER-'+browser)+';document.querySelector("[data-action=insert-text]").click();return true;})()')
            wait(session,'document.querySelector("#s-revision").textContent !== '+json.dumps(revision),120)
            session.click('[data-action="save"]')
            wait(session,'(()=>{const r=JSON.parse(document.documentElement.getAttribute("data-litecore"));return r.saves.some(s=>s.settled && s.outcome === "saved");})()',180)
            code,body,_=self.dav('GET',writer); wp=self.out/(browser+'-writer-saved.odt');wp.write_bytes(body)
            with zipfile.ZipFile(io.BytesIO(body)) as z: text=z.read('content.xml').decode()
            self.check(browser+'/writer-still-opens-saves',code==200 and 'WRITER-'+browser in text,{'status':code,'sha256':hashlib.sha256(body).hexdigest(),'host':host_record(session)})
            run['writerRelease']=self.leave(session,writer)
            run['screenshot']=str(self.out/(browser+'-host.png'))
        finally:
            try: (self.out/(browser+'-last.png')).write_bytes(session.screenshot())
            except Exception: pass
            run['browserClose']=close_browser(session)

    def calc_read(self,session,address):
        select(session,address);return evaluate(session,'window.__calcEditor.state.cell')

    def readonly_round(self,browser):
        session=open_browser(browser);run={'browser':browser,'kind':'readonly'};self.report['runs'].append(run)
        try:
            navigate(session,self.instance.base+'/login',timeout=60)
            if isinstance(session,ChromeSession):
                session.evaluate('(()=>{window.__readonlyLogin=null;fetch("/login",{method:"POST",body:new URLSearchParams({user:'+json.dumps(self.user)+',password:'+json.dumps(self.password)+',requesttoken:document.head.dataset.requesttoken})}).then(r=>window.__readonlyLogin=r.status);return true;})()')
                wait(session,'window.__readonlyLogin === 200',45)
            else:
                for selector,text in (('#user',self.user),('#password',self.password)):
                    element=session.command('POST','/element',{'using':'css selector','value':selector})['element-6066-11e4-a52e-4f735466cecf']
                    session.command('POST',f'/element/{element}/value',{'text':text})
                session.click('button[type="submit"]');wait(session,'!location.pathname.endsWith("/login")',45)
            run['entry']=self.open_file(session,self.folder+'/readonly.ods','ods-viewer.html',False)
            wait(session,'document.querySelector("#state-pill")?.dataset.state === "ready"',180)
            state=evaluate(session,'({saveButtons:document.querySelectorAll("#save-button,[data-action=save]").length,hostSave:typeof window.liteCoreHost?.save,host:document.documentElement.getAttribute("data-litecore")})')
            self.check(browser+'/readonly-files-route',state['saveButtons']==0 and state['hostSave']=='undefined',state)
            p=self.props(self.folder+'/readonly.ods')
            self.check(browser+'/readonly-no-lock',p['lock']!='1',{k:v for k,v in p.items() if k!='token'})
            (self.out/(browser+'-readonly.png')).write_bytes(session.screenshot())
        finally: run['browserClose']=close_browser(session)

    def run(self):
        try:
            code,_,_=self.dav('MKCOL',self.folder); self.check('owned-folder',code==201,code);self.created_folder=True
            self.ocs('POST','cloud/users',{'userid':self.user,'password':self.password});self.created_user=True
            name=self.folder+'/readonly.ods';self.paths.append(name)
            code,_,_=self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS});self.check('readonly-fixture',code in (200,201,204),code)
            share=self.ocs('POST','apps/files_sharing/api/v1/shares',{'path':'/'+name,'shareType':0,'shareWith':self.user,'permissions':1})
            self.share=share['id'];self.report['readonlyShare']={'id':self.share,'permissions':share['permissions']}
            for browser in ('chrome','firefox'):
                self.admin_round(browser);self.readonly_round(browser)
        except Exception as error:
            self.report['error']=str(error);self.report['traceback']=traceback.format_exc()
        finally:
            cleanup=self.report['cleanup'];cleanup['ownedUnlocks']=[]
            for name in self.paths:
                try:
                    p=self.props(name)
                    if p['token']:
                        token=p['token'];token=token if token.startswith('opaquelocktoken:') else 'opaquelocktoken:'+token
                        code,_,_=self.dav('UNLOCK',name,headers={'Lock-Token':f'<{token}>'})
                        cleanup['ownedUnlocks'].append({'name':name,'status':code})
                except Exception as e: cleanup.setdefault('errors',[]).append(str(e))
            if self.share:
                try: self.ocs('DELETE','apps/files_sharing/api/v1/shares/'+str(self.share));cleanup['shareRemoved']=True
                except Exception as e: cleanup.setdefault('errors',[]).append(str(e))
            if self.created_user:
                try: self.ocs('DELETE','cloud/users/'+self.user);cleanup['userRemoved']=True
                except Exception as e: cleanup.setdefault('errors',[]).append(str(e))
            if self.created_folder:
                code,_,_=self.dav('DELETE',self.folder);cleanup['folderDeleteStatus']=code
            self.report['ok']=not self.report.get('error') and not cleanup.get('errors') and all(c['ok'] for c in self.report['checks'])
            (self.out/'report.json').write_text(json.dumps(self.report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'ok':self.report['ok'],'checks':len(self.report['checks']),'error':self.report.get('error'),'cleanup':self.report['cleanup']},ensure_ascii=False))
        return self.report['ok']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    with browser_lock('run_calc_editor_host'):
        raise SystemExit(0 if Harness(args.out.resolve()).run() else 1)
