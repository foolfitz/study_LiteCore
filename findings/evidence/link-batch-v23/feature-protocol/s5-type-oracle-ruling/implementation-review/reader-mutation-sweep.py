import subprocess,sys,hashlib,shutil
from pathlib import Path
SDK=Path.cwd();target=SDK/'tools/read_v23_native_s5_type.py';src=target.read_text();h=hashlib.sha256(src.encode()).hexdigest()
backup=Path(sys.argv[1]);shutil.copy(target,backup)
MUT={'none':('',''),'no-x-order':("if not end<x[0]['atMs']:","if False:"),
     'no-text':("if between['getTextSelection']!=texts[0]:","if False:"),
     'no-silent-caret':("elif between.get('INVALIDATE_VISIBLE_CURSOR') not in afters:","elif False:"),
     'no-silent-collapsed':("if row.get('betweenSelectionType')!=0:","if False:"),
     'no-cap':("elif settled<0:","elif False:"),
     'no-missing-between':("return None,issues+['missing between-read']","pass"),
     'no-follow-shift':("if not shift[-1]['returnMs']<=start<=end:","if False:"),
     'no-per-cell':("issues+=why","pass"),
     'ignore-validate-cell':("issues,outputs=validate_cell(actual,item,setup,directory/'saves',artifacts)","_,outputs=validate_cell(actual,item,setup,directory/'saves',artifacts);issues=[]"),
     'no-before-fixture':("if 'before' in outputs and outputs['before']['paragraphs']!=fixture:","if False:"),
     'no-discovery-cursor':("if actual.get('expectedCursorRect')!=points.get(actual.get('expectedCursorPoint')):","if False:"),
     'no-rounds-agree':("if not (isinstance(texts,list) and len(texts)==3 and len(set(texts))==1):","if False:"),
     'status-from-witness-only':("results.append({'id':item['id'],'status':'NOT_ESTABLISHED' if issues else 'NATIVE_SAVE_AVAILABLE',","results.append({'id':item['id'],'status':'NOT_ESTABLISHED' if why else 'NATIVE_SAVE_AVAILABLE',")}
try:
    for name,(a,b) in MUT.items():
        if a:assert src.count(a)==1,name
        target.write_text(src.replace(a,b) if a else src)
        r=subprocess.run([sys.executable,'-m','unittest','tests.test_v23_native_s5_type'],cwd=SDK,capture_output=True,text=True)
        bad=[l.split(' ')[1] for l in r.stderr.splitlines() if l.startswith(('FAIL:','ERROR:'))]
        print(name,'GREEN' if r.returncode==0 else 'RED',bad)
finally:
    target.write_text(src)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==h;print('restored',h[:12])
