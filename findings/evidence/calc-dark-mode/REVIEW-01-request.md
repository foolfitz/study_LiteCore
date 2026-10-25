# Adversarial review: Calc inline editor dark host correction
Review only the supplied source. No tools. Identify concrete correctness regressions or a false acceptance claim; otherwise say no findings. Keep the reply short.

Context: actual Nextcloud global textarea CSS supplies light text under a dark palette; this inline editor uses white background. The correction scopes text/caret/color-scheme to that element. All 45 other package records are unchanged; no engine relink. Both Chrome/Firefox actual-host preview and installed probes measure color, caret, textFill and colorScheme under light/dark host palette variables. This is bounded palette observation, not a claim of browser auto-dark extension or OS forced-color coverage.

## Product diff
```diff
diff --git a/wasm_sdk_probe/web/ods-editor.html b/wasm_sdk_probe/web/ods-editor.html
index 9c280656..6851df1c 100644
--- a/wasm_sdk_probe/web/ods-editor.html
+++ b/wasm_sdk_probe/web/ods-editor.html
@@ -34,7 +34,8 @@ button:disabled { opacity:.4; cursor:default; }
 #active-cell { position:absolute; border:2px solid var(--accent); pointer-events:none; z-index:2; }
 #surface { user-select:none; }
 #cell-editor { user-select:text; }
-#cell-editor { position:absolute; z-index:3; min-width:80px; min-height:30px; margin:0; border:2px solid var(--accent); border-radius:0; background:#fff; padding:3px 5px; font-size:14px; line-height:21px; resize:none; box-shadow:0 3px 12px #163d2320; }
+/* Pair text and caret with the white document canvas under host themes. */
+#cell-editor { position:absolute; z-index:3; min-width:80px; min-height:30px; margin:0; border:2px solid var(--accent); border-radius:0; background:#fff; color:var(--ink); caret-color:currentColor; color-scheme:light; padding:3px 5px; font-size:14px; line-height:21px; resize:none; box-shadow:0 3px 12px #163d2320; }
 #cell-editor.grid-input { width:1px !important; height:1px !important; min-width:0; min-height:0; padding:0; border:0; opacity:0; box-shadow:none; pointer-events:none; }
 #empty { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px; color:var(--muted); pointer-events:none; }
 #empty strong { color:var(--ink); font-size:21px; font-weight:550; }

```
## Focused observation
```python
#!/usr/bin/env python3
"""Focused actual-host style observation; palettes change only the private DOM."""
import argparse,hashlib,json,re,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
from run_calc_editor_host import Harness,ODS
from probe_m3_gate0_coep import browser_login
from run_calc_editor_browser import select,wait
from probe_calc_input_range import press
from r7_support import evaluate,run_in_page
from v21_shakedown_common import browser_lock,close_browser

PALETTES={'light':('#222222','#ffffff'),'dark':('#ededed','#171717')}
def ratio(fg,bg):
 def lum(s):
  c=[float(x)/255 for x in re.findall(r'[\d.]+',s)[:3]]
  v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c]
  return sum(x*w for x,w in zip(v,[.2126,.7152,.0722]))
 a,b=sorted([lum(fg),lum(bg)]);return (b+.05)/(a+.05)
class Theme(Harness):
 def __init__(self,out,scratch,source):
  super().__init__(out,scratch,kind='admin');self.source=source
 def admin_round(self,browser):
  s=self.browser(browser,'theme');r={'browser':browser,'samples':[]};self.report['runs'].append(r)
  name=self.folder+'/'+browser+'.ods';self.paths.append(name)
  try:
   self.check(browser+'/upload',self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS})[0] in (200,201,204),name)
   browser_login(s,self.instance.base,self.instance.password)
   r['entry']=self.open_file(s,name,'ods-editor.html');self.ready_calc(s);evaluate(s,'window.__calcEditor.ready')
   if self.source:
    text=self.source.read_text();rules=re.findall(r'^#cell-editor \{[^}]+\}',text,re.M)
    assert len(rules)==2
    run_in_page(s,'(()=>{const n=document.createElement("style");n.textContent='+json.dumps('\n'.join(rules))+';document.head.append(n);})()')
    r['previewSourceSha256']=hashlib.sha256(self.source.read_bytes()).hexdigest()
   select(s,'B2');press(s,'F2');wait(s,'window.__calcEditor.state.editing==="inline"')
   for mode,(fg,bg) in PALETTES.items():
    run_in_page(s,'(()=>{const n=document.querySelector("#litecore-editor-root");n.style.setProperty("--color-main-text",'+json.dumps(fg)+');n.style.setProperty("--color-main-background",'+json.dumps(bg)+');n.style.colorScheme='+json.dumps(mode)+';})()')
    x=evaluate(s,'(()=>{const n=document.querySelector("#cell-editor"),c=getComputedStyle(n),r=n.getBoundingClientRect();return {color:c.color,background:c.backgroundColor,caret:c.caretColor,textFill:c.webkitTextFillColor||c.color,colorScheme:c.colorScheme,opacity:c.opacity,width:r.width,height:r.height,focus:document.activeElement.id,value:n.value,revision:window.__calcEditor.state.revision};})()')
    x['mode']=mode;x['contrast']=ratio(x['color'],x['background']);r['samples'].append(x)
    (self.out/(browser+'-'+mode+'.png')).write_bytes(s.screenshot())
    self.check(browser+'/'+mode+'/visible-contrast',x['contrast']>=4.5 and x['opacity']=='1' and x['width']>1 and x['focus']=='cell-editor',x)
   press(s,'Escape');release=self.leave(s,name)
   self.check(browser+'/normal-release',release['lock']!='1',release)
   code,body,_=self.dav('GET',name)
   self.check(browser+'/document-unchanged',code==200 and hashlib.sha256(body).hexdigest()==hashlib.sha256(self.fixture.read_bytes()).hexdigest(),{'status':code,'sha256':hashlib.sha256(body).hexdigest()})
  finally:r['browserClose']=close_browser(s)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-style',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 with browser_lock('calc-dark-mode'),tempfile.TemporaryDirectory(prefix='calc-theme-',dir=ROOT/'wasm_sdk_probe/build') as scratch:
  raise SystemExit(0 if Theme(a.out.resolve(),Path(scratch),a.source_style).run() else 1)

```
