Adversarial source-only review of a new native S5 reference instrument, before the owner compiles it. No tools. Report only concrete correctness/provenance faults or NO_CONCRETE_FINDING. The fixed protocol requires seven sequences over84 existing Shift shapes: Shift,Bksp; Shift,Delete; Shift,x; Shift,Bksp,Bksp; Shift,Delete,Delete; Bksp,Shift,Bksp; Delete,Shift,Delete. Native oracle sourceN1 is392 cells (196LR literal,196HomeEnd conditional on browser singleline). Up/Down use later settledWASM references, never this native oracle. Current unit claims sourcepreparation only; no native execution or browser acceptance. Existing signature setup source is pinned1e29f73bfa0a0b73a5ced6d5f5a91fbaac48bfdfa1fb1c1799514aa0913eef17 and unchanged. The included original exposes keycodes1026,1027,1028,1029 and posts0INPUT/1UP; shift4096. settle returns nonnegativequietduration or negativecap; makeShape/discoverAll are reused. Root already fixed asymmetric buildReceipt identity: both snapshots now validate/include it, tested with stand-in runner-to-reader normal and changedreceipt/source/header. Seek a real remaining execution/binding/content-comparison fault. No new thresholds/populations/frameworks. Reply in English.

FILE wasm_sdk_probe/tools/v23_native_s5.cpp
```
// Native continuation references only. Reuse the exact archived signature setup;
// never modify its source or presume its historical executable saves S5 results.
#define main v23_retained_signature_main
#include "link_native_extend_signatures.cpp"
#undef main
#include "v23_native_s5_sequence.hpp"
#include <filesystem>

static_assert(LOK_KEYEVENT_KEYINPUT==0 && LOK_KEYEVENT_KEYUP==1, "S5 recording protocol follows actual LOK event enums");

namespace {
std::string sequenceJson(const std::vector<v23s5::Post>& seq) {
    std::string out="[";
    for (std::size_t i=0;i<seq.size();++i) out+=(i?",":"")+q(seq[i].operation);
    return out+"]";
}
std::string cellId(const KeyDef& k,const std::string& shape,const std::string& family) {
    return "shift-"+std::string(k.name)+"@"+shape+"/"+family;
}
bool nativeKey(const KeyDef& k) {
    return std::string(k.name)=="Left" || std::string(k.name)=="Right" ||
           std::string(k.name)=="Home" || std::string(k.name)=="End";
}
void inventory() {
    for (const auto& shape:kShapes) for (const auto& k:kKeys) if (nativeKey(k))
        for (const auto* family:v23s5::families)
            std::cout<<"{\"id\":"<<q(cellId(k,shape,family))<<",\"sequence\":"
                     <<sequenceJson(v23s5::sequence(family,k.code,k.name))<<"}\n";
}
bool measured(LibreOfficeKit* kit,const std::string& url,const std::filesystem::path& out,
              const std::string& shape,const KeyDef& k,const std::string& family) {
    const auto id=cellId(k,shape,family);
    std::string stem=id;std::replace(stem.begin(),stem.end(),'/','_');
    const auto beforeFile=out/(stem+"-before.odt"),afterFile=out/(stem+"-after.odt");
    if (std::filesystem::exists(beforeFile)||std::filesystem::exists(afterFile)) return false;
    Doc s=openDoc(kit,url);
    if (!s.d) {std::cout<<"{\"id\":"<<q(id)<<",\"fatal\":\"documentLoad\"}\n";return false;}
    const auto opened=settle(s,800,8000);
    const auto made=makeShape(s,shape,800);
    const auto before=snap(s);
    const auto saveBefore=s.d->pClass->saveAs(s.d,("file://"+beforeFile.string()).c_str(),"odt",nullptr)!=0;
    const auto beforePost=snap(s);
    const int beforeType=s.d->pClass->getSelectionType(s.d);
    const auto seq=v23s5::sequence(family,k.code,k.name);
    const auto start=nowMs();
    struct Sent {int type,character,key;double at,returned;};
    std::vector<Sent> sent;sent.reserve(seq.size()*2);
    // 'x' is queued KEYINPUT(character=120,key=0), never synchronous paste.
    // Timing/metadata record no intervening LOK call or wait.
    v23s5::dispatch(seq,[&](int type,int character,int code) {
        const auto at=nowMs();
        s.d->pClass->postKeyEvent(s.d,type,character,code);
        sent.push_back({type,character,code,at-start,nowMs()-start});
    });
    const auto settled=settle(s,800,8000);
    const auto after=snap(s);
    const int afterType=s.d->pClass->getSelectionType(s.d);
    const auto saveAfter=s.d->pClass->saveAs(s.d,("file://"+afterFile.string()).c_str(),"odt",nullptr)!=0;
    std::cout<<"{\"id\":"<<q(id)<<",\"shape\":"<<q(shape)<<",\"key\":"<<q(k.name)
             <<",\"family\":"<<q(family)<<",\"sequence\":"<<sequenceJson(seq)
             <<",\"mode\":\"default-native-queued\",\"openedSettleMs\":"<<opened
             <<",\"setupSettleMs\":"<<made.settleMs<<",\"finalSettleMs\":"<<settled
             <<",\"expectedSelection\":"<<q(made.expectedSelection)
             <<",\"expectedCursorPoint\":"<<q(made.expectedCursorPoint)
             <<",\"expectedCursorRect\":"<<q(made.expectedCursorPoint.empty()?"":pt(made.expectedCursorPoint).rect)
             <<",\"beforeSelectionType\":"<<beforeType<<",\"afterSelectionType\":"<<afterType
             <<",\"before\":"<<snapJson(before)<<",\"beforePost\":"<<snapJson(beforePost)
             <<",\"after\":"<<snapJson(after)<<",\"savedBefore\":"<<(saveBefore?"true":"false")
             <<",\"savedAfter\":"<<(saveAfter?"true":"false")
             <<",\"beforeFile\":"<<q(beforeFile.filename().string())
             <<",\"afterFile\":"<<q(afterFile.filename().string())<<",\"posts\":[";
    for (std::size_t i=0;i<sent.size();++i) {
        const auto& p=sent[i];
        std::cout<<(i?",":"")<<"{\"type\":"<<p.type<<",\"character\":"<<p.character
                 <<",\"key\":"<<p.key<<",\"atMs\":"<<p.at<<",\"returnMs\":"<<p.returned<<"}";
    }
    std::cout<<"],\"callbacks\":"<<callbacksJson(s,start,-500)<<"}"<<std::endl;
    closeDoc(s);
    return saveBefore&&saveAfter&&opened>=0&&made.settleMs>=0&&settled>=0;
}
}
int main(int argc,char** argv) {
    if(argc==2&&std::string(argv[1])=="--inventory") {inventory();return 0;}
    if(argc==2&&std::string(argv[1])=="--paragraphs") return v23_retained_signature_main(argc,argv);
    if(argc!=5) {std::cerr<<"usage: v23-native-s5 INSTALL PROFILE_URL FIXTURE_URL FRESH_SAVE_DIRECTORY\n";return 2;}
    const std::filesystem::path out=std::filesystem::absolute(argv[4]);
    if(!std::filesystem::is_directory(out)||!std::filesystem::is_empty(out)) return 2;
    LibreOfficeKit* kit=lok_init_2(argv[1],argv[2]);if(!kit)return 3;
    if(!discoverAll(kit,argv[3],1,800))return 4;
    bool ok=true;
    for(const auto& shape:kShapes)for(const auto& k:kKeys)if(nativeKey(k))
        for(const auto* family:v23s5::families)
            if(!measured(kit,argv[3],out,shape,k,family))ok=false;
    return ok?0:5;
}

```

FILE wasm_sdk_probe/tools/v23_native_s5_sequence.hpp
```
#ifndef V23_NATIVE_S5_SEQUENCE_HPP
#define V23_NATIVE_S5_SEQUENCE_HPP
#include <array>
#include <stdexcept>
#include <string>
#include <vector>
namespace v23s5 {
struct Post { int character; int key; std::string operation; };
inline const std::array<const char*,7> families = {{"backspace", "delete", "type", "backspace-twice", "delete-twice", "backspace-before-and-after", "delete-before-and-after"}};
inline std::vector<Post> sequence(const std::string& family, int shiftKey, const std::string& keyName) {
    const Post shift{0, shiftKey | 0x1000, "Shift+" + keyName};
    const Post back{0,1283,"Backspace"}, del{0,1286,"Delete"}, text{120,0,"text:x"};
    if (family=="backspace") return {shift,back};
    if (family=="delete") return {shift,del};
    if (family=="type") return {shift,text};
    if (family=="backspace-twice") return {shift,back,back};
    if (family=="delete-twice") return {shift,del,del};
    if (family=="backspace-before-and-after") return {back,shift,back};
    if (family=="delete-before-and-after") return {del,shift,del};
    throw std::invalid_argument("unknown S5 family");
}
// Only two FIFO key calls per original member; no read, paste, wait or save seam.
template<typename Send> void dispatch(const std::vector<Post>& posts, Send send) {
    for (const auto& post : posts) {
        send(0,post.character,post.key); // LOK_KEYEVENT_KEYINPUT
        send(1,post.character,post.key); // LOK_KEYEVENT_KEYUP
    }
}
}
#endif

```

FILE wasm_sdk_probe/tools/build_v23_native_s5_owner.py
```
#!/usr/bin/env python3
"""OWNER ONLY: compile the small S5 harness from captured source bytes; no core build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
TOOLS=ROOT/'wasm_sdk_probe/tools'
COMPILED=('v23_native_s5.cpp','v23_native_s5_sequence.hpp','link_native_extend_signatures.cpp')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists():p.error('build output must be fresh')
    compiler=shutil.which('g++')
    if not compiler:p.error('g++ unavailable')
    include=ROOT/'libreoffice-26-8/include'
    headers={str(p.relative_to(ROOT)):sha(p) for p in sorted((include/'LibreOfficeKit').glob('*.h*')) if p.is_file()}
    if not headers:p.error('LibreOfficeKit headers missing')
    sources={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED}
    out.mkdir(parents=True);snap=out/'source';snap.mkdir()
    for name in COMPILED:shutil.copyfile(TOOLS/name,snap/name)
    binary=out/'v23-native-s5'
    command=[compiler,'-std=c++17','-O2','-I'+str(include),str(snap/'v23_native_s5.cpp'),'-ldl','-lpthread','-o',str(binary)]
    receipt={'schema':1,'sources':sources,'headers':headers,'argv':command,
             'compiler':{'path':compiler,'sha256':sha(Path(compiler)),'version':subprocess.check_output([compiler,'--version'],text=True)}}
    (out/'build-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    with (out/'build.stdout').open('x') as stdout,(out/'build.stderr').open('x') as stderr:
        result=subprocess.run(command,stdout=stdout,stderr=stderr)
    receipt['exitCode']=result.returncode
    receipt['protectedInputsUnchanged']=all(sha(ROOT/p)==v for p,v in {**sources,**headers}.items())
    receipt['snapshotsMatch']=all(sha(snap/n)==sources[str((TOOLS/n).relative_to(ROOT))] for n in COMPILED)
    receipt['binary']={'path':str(binary),'sha256':sha(binary)} if binary.is_file() else None
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    return result.returncode or int(not receipt['protectedInputsUnchanged'] or not receipt['snapshotsMatch'])
if __name__=='__main__':raise SystemExit(main())

```

FILE wasm_sdk_probe/tools/run_v23_native_s5.py
```
#!/usr/bin/env python3
"""Finite native S5 reference execution; never compiles. One run, no retry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import v23_feature_s_cases as source
ROOT=source.ROOT
TOOLS=Path(__file__).resolve().parent
SOURCES=[TOOLS/name for name in ('v23_native_s5.cpp','v23_native_s5_sequence.hpp',
    'link_native_extend_signatures.cpp','run_v23_native_s5.py','read_v23_native_s5.py',
    'v23_feature_s_cases.py','run_merge_wasm_shakedown.py','odt_paragraphs.py','build_v23_native_s5_owner.py')]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cases():
    if sha(TOOLS/'link_native_extend_signatures.cpp')!=source.PINS['tool-source-as-run.cpp']:
        raise ValueError('retained native shape source changed')
    table=source.derive(source.read_rounds())
    return table,[row for row in table['S5'] if row['referencePolicy']!='settled-wasm']

def validate_build_receipt(binary,build_receipt):
    from build_v23_native_s5_owner import COMPILED
    receipt=json.loads(build_receipt.read_text())
    if receipt.get('exitCode')!=0 or receipt.get('protectedInputsUnchanged') is not True or receipt.get('snapshotsMatch') is not True:
        raise ValueError('owner build receipt is not successful')
    if receipt.get('binary')!={'path':str(binary),'sha256':sha(binary)}:
        raise ValueError('binary differs from actual owner build receipt')
    required={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED}
    if receipt.get('sources')!=required:raise ValueError('compiled sources differ from owner build receipt')
    for name,value in receipt['headers'].items():
        if sha(ROOT/name)!=value:raise ValueError('compiled header changed: '+name)
    if not receipt.get('headers'):raise ValueError('owner build receipt has no headers')
    return {'path':str(build_receipt.resolve()),'sha256':sha(build_receipt)}

def pins(binary,install,build_receipt):
    receipt_binding=validate_build_receipt(binary.resolve(),build_receipt)
    # Record actual libraries, not an asserted core label. This existing core is never rebuilt here.
    libraries=sorted(install.glob('*.so'))+sorted(install.glob('*.so.*'))
    libraries=sorted(set(p.resolve() for p in libraries if p.is_file()))
    if not libraries:raise ValueError('native install has no shared libraries')
    return {'buildReceipt':receipt_binding,'binary':{'path':str(binary.resolve()),'sha256':sha(binary)},
            'sources':{str(p.relative_to(ROOT)):sha(p) for p in SOURCES},
            'libraries':{str(p):sha(p) for p in libraries},
            'inputPins':{str(ROOT/p):value for p,value in cases()[0]['inputPins'].items()}}

def expected_inventory(rows):return {r['id']:r['sequence'] for r in rows}
def read_inventory(text,rows):
    data=[json.loads(line) for line in text.splitlines() if line.strip()]
    if len(data)!=len(rows) or {r['id']:r['sequence'] for r in data}!=expected_inventory(rows):
        raise ValueError('compiled native inventory differs from source-derived S5 cells')
    return data

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','install','out','build-receipt'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.binary=a.binary.resolve();a.install=a.install.resolve();a.out=a.out.resolve()
    if a.out.exists():p.error('output must be fresh; failed runs are preserved')
    table,rows=cases();identity=pins(a.binary,a.install,a.build_receipt)
    # These modes only enumerate inputs, before any native document is opened.
    inventory=subprocess.check_output([str(a.binary),'--inventory'],text=True)
    read_inventory(inventory,rows)
    paragraphs=subprocess.check_output([str(a.binary),'--paragraphs'],text=True).splitlines()
    from odt_paragraphs import paragraph_texts_from_xml
    fixture=ROOT/table['fixture']['path']
    if paragraphs!=paragraph_texts_from_xml(fixture.read_bytes()):raise ValueError('compiled fixture text mismatch')
    a.out.mkdir(parents=True);(a.out/'profile').mkdir();(a.out/'saves').mkdir()
    shutil.copyfile(fixture,a.out/'fixture.fodt')
    (a.out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    (a.out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
    (a.out/'inventory.jsonl').write_text(inventory)
    env=dict(os.environ,SAL_USE_VCLPLUGIN='svp');env.pop('SAL_LOK_OPTIONS',None);env.pop('OC_A11Y',None)
    cmd=['nice','-n','10',str(a.binary),str(a.install),(a.out/'profile').as_uri(),
         (a.out/'fixture.fodt').as_uri(),str(a.out/'saves')]
    (a.out/'command.json').write_text(json.dumps({'argv':cmd,'mode':'default-native-queued',
        'environment':{'SAL_USE_VCLPLUGIN':'svp','SAL_LOK_OPTIONS':None,'OC_A11Y':None},
        'executionsPerCell':1,'homeEndConditional':True},indent=2)+'\n')
    with (a.out/'native.jsonl').open('x') as stdout,(a.out/'native.stderr').open('x') as stderr:
        result=subprocess.run(cmd,stdout=stdout,stderr=stderr,env=env)
    try:after=pins(a.binary,a.install,a.build_receipt)
    except (OSError,ValueError,KeyError) as error:after={'captureError':str(error)}
    (a.out/'completion.json').write_text(json.dumps({'exitCode':result.returncode,
        'protectedInputsUnchanged':after==identity,'afterIdentity':after,
        'artifacts':{str(f.relative_to(a.out)):sha(f) for f in sorted(list((a.out/'saves').glob('*.odt'))+[a.out/n for n in ('native.jsonl','native.stderr','identity.json','cases.json','inventory.jsonl','command.json','fixture.fodt')])}},indent=2)+'\n')
    return result.returncode or (0 if after==identity else 1)
if __name__=='__main__':raise SystemExit(main())

```

FILE wasm_sdk_probe/tools/read_v23_native_s5.py
```
#!/usr/bin/env python3
"""Read actual native continuation saves. Availability is not browser parity."""
import argparse
import json
import math
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_v23_native_s5 import ROOT,TOOLS,SOURCES,cases,sha,read_inventory,validate_build_receipt
from odt_paragraphs import paragraph_texts_from_xml
from run_merge_wasm_shakedown import reduce_content
KEYS={'Left':1026,'Right':1027,'Home':1028,'End':1029}

def content(path):
    with zipfile.ZipFile(path) as z:return z.read('content.xml')

def comparison(path,family):
    data=content(path)
    return paragraph_texts_from_xml(data) if family=='type' else reduce_content(data)

def compare_saved(reference,candidate,family):
    """Literal comparator only; caller must first establish the oracle's applicability."""
    return comparison(reference,family)==comparison(candidate,family)

def expected_posts(row):
    result=[]
    for op in row['sequence']:
        if op.startswith('Shift+'):char,key=0,KEYS[op[6:]]|0x1000
        elif op=='text:x':char,key=120,0
        else:char,key=0,{'Backspace':1283,'Delete':1286}[op]
        result.extend({'type':t,'character':char,'key':key} for t in (0,1))
    return result

def validate_cell(row,expected,setup,saves,artifacts):
    issues=[]
    if row.get('sequence')!=expected['sequence']:issues.append('sequence mismatch')
    if row.get('mode')!='default-native-queued':issues.append('wrong native mode')
    if row.get('family')!=expected['family'] or row.get('key')!=setup['key'] or row.get('shape')!=setup['shape']:
        issues.append('source identity mismatch')
    posts=row.get('posts',[])
    if [{k:p.get(k) for k in ('type','character','key')} for p in posts]!=expected_posts(expected):
        issues.append('actual FIFO key posts differ')
    previous=-1
    for post in posts:
        start,end=post.get('atMs'),post.get('returnMs')
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (start,end)) or start<previous or end<start:
            issues.append('invalid actual post ordering');break
        previous=end
    for field in ('openedSettleMs','setupSettleMs','finalSettleMs'):
        value=row.get(field)
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            issues.append('unestablished settle: '+field)
    selection=setup['setup']['expectedSelection']
    if row.get('expectedSelection')!=selection:issues.append('setup declaration differs from retained source')
    if row.get('expectedCursorPoint')!=setup['setup']['expectedMovingPointName'] or not row.get('expectedCursorRect'):
        issues.append('missing or wrong logical setup point')
    for which in ('before','beforePost'):
        state=row.get(which,{})
        if state.get('getTextSelection')!=selection or state.get('INVALIDATE_VISIBLE_CURSOR')!=row.get('expectedCursorRect'):
            issues.append('missing or wrong actual pre-key selection/caret: '+which)
    if row.get('beforeSelectionType')!=(1 if setup['setup']['expectRange'] else 0):
        issues.append('actual pre-key selection type differs')
    if row.get('afterSelectionType') not in (0,1,2) or not isinstance(row.get('after',{}).get('getTextSelection'),str):
        issues.append('missing actual post-key selection')
    outputs={}
    for label in ('before','after'):
        name=row.get(label+'File','')
        if not name or Path(name).name!=name or not name.endswith('.odt'):
            issues.append('invalid save path: '+label);continue
        path=saves/name
        if row.get('saved'+label.title()) is not True or not path.is_file():
            issues.append('missing actual save: '+label);continue
        if artifacts.get('saves/'+name)!=sha(path):issues.append('save not bound to completion: '+label)
        try:
            raw=content(path);paragraphs=paragraph_texts_from_xml(raw);reduced=reduce_content(raw)
            import hashlib
            outputs[label]={'path':str(path),'sha256':sha(path),'paragraphs':paragraphs,
                'reducedContentSha256':hashlib.sha256(reduced).hexdigest()}
        except (ValueError,KeyError,zipfile.BadZipFile) as exc:issues.append('unreadable saved content: '+str(exc))
    return issues,outputs

def read(directory):
    table,expected=cases();problems=[];results=[]
    identity=json.loads((directory/'identity.json').read_text())
    completion=json.loads((directory/'completion.json').read_text())
    if completion.get('exitCode')!=0 or completion.get('protectedInputsUnchanged') is not True or completion.get('afterIdentity')!=identity:
        problems.append('native run failed or protected inputs changed')
    if json.loads((directory/'cases.json').read_text())!=expected:problems.append('case schedule differs')
    read_inventory((directory/'inventory.jsonl').read_text(),expected)
    for group in ('sources','libraries','inputPins'):
        if not identity.get(group):problems.append('empty input binding: '+group)
        for name,value in identity.get(group,{}).items():
            path=Path(name) if Path(name).is_absolute() else ROOT/name
            if not path.is_file() or sha(path)!=value:problems.append('changed bound input: '+name)
    if identity.get('sources')!={str(p.relative_to(ROOT)):sha(p) for p in SOURCES}:
        problems.append('source closure differs')
    if identity.get('inputPins')!={str(ROOT/p):v for p,v in table['inputPins'].items()}:
        problems.append('historical input bindings differ')
    receipt=identity.get('buildReceipt',{})
    if not receipt.get('path') or not Path(receipt['path']).is_file() or sha(receipt['path'])!=receipt.get('sha256'):
        problems.append('owner build receipt missing or changed')
    else:
        try:
            if validate_build_receipt(Path(identity['binary']['path']),Path(receipt['path']))!=receipt:
                problems.append('owner build receipt binding changed')
        except (OSError,ValueError,KeyError) as error:problems.append('invalid owner build receipt: '+str(error))
        build=json.loads(Path(receipt['path']).read_text())
        from build_v23_native_s5_owner import COMPILED
        if build.get('sources')!={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED} or build.get('binary')!=identity.get('binary') or build.get('exitCode')!=0 or build.get('protectedInputsUnchanged') is not True or build.get('snapshotsMatch') is not True:
            problems.append('owner build receipt does not bind compiled source/binary')
    binary=identity.get('binary',{})
    if not binary.get('path') or not Path(binary['path']).is_file() or sha(binary['path'])!=binary.get('sha256'):
        problems.append('owner binary missing or changed')
    artifacts=completion.get('artifacts',{})
    for name,value in artifacts.items():
        path=directory/name
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.is_file() or sha(path)!=value:
            problems.append('changed native output: '+name)
    required={'native.jsonl','native.stderr','identity.json','cases.json','inventory.jsonl','command.json','fixture.fodt'}
    if not required<=artifacts.keys():problems.append('missing output bindings')
    if sha(directory/'fixture.fodt')!=table['fixture']['sha256']:problems.append('fixture differs')
    rows=[json.loads(line) for line in (directory/'native.jsonl').read_text().splitlines() if line.strip()]
    if any(r.get('fatal') for r in rows):problems.append('native discovery/load failure')
    measured=[r for r in rows if 'id' in r]
    byid={r['id']:r for r in measured}
    if len(measured)!=len(expected) or set(byid)!={r['id'] for r in expected}:problems.append('missing/extra/duplicate native cells')
    setups={r['id']:r for r in table['cases']}
    points={p['name']:p.get('rect') for r in rows if r.get('arm','').startswith('discover-') for p in r.get('steps',[])}
    if not points:problems.append('missing actual discovery points')
    for item in expected:
        if item['id'] not in byid:continue
        issues,outputs=validate_cell(byid[item['id']],item,setups[item['sourceArm']],directory/'saves',artifacts)
        actual=byid[item['id']]
        if actual.get('expectedCursorRect')!=points.get(actual.get('expectedCursorPoint')):
            issues.append('setup cursor not bound to actual native discovery')
        if 'before' in outputs and outputs['before']['paragraphs']!=paragraph_texts_from_xml((directory/'fixture.fodt').read_bytes()):
            issues.append('before save differs from fixture paragraph text')
        problems.extend(item['id']+': '+issue for issue in issues)
        results.append({'id':item['id'],'status':'NOT_ESTABLISHED' if issues else 'NATIVE_SAVE_AVAILABLE',
            'referencePolicy':item['referencePolicy'],'requiresBrowserSingleLineWitness':item['referencePolicy']!='native',
            'browserParity':'NOT_ESTABLISHED_UNPERFORMED','comparison':item['comparison'],'saves':outputs})
    return {'schema':1,'verdict':'NOT_ESTABLISHED' if problems else 'NATIVE_S5_SAVES_AVAILABLE',
            'nativeExecutionsPerCell':1,'cells':results,'problems':problems,
            'scope':'Native reference availability only; Home/End remains conditional; no browser or Up/Down parity claim'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:result=read(a.directory.resolve())
    except (OSError,ValueError,KeyError,TypeError) as error:result={'verdict':'NOT_ESTABLISHED','problems':[str(error)]}
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')
    return int(result['verdict']!='NATIVE_S5_SAVES_AVAILABLE')
if __name__=='__main__':raise SystemExit(main())

```

FILE wasm_sdk_probe/tests/test_v23_native_s5_boundary.py
```
"""Runner-to-reader receipt boundary, fake files/process only; never loads LOK."""
import contextlib
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import run_v23_native_s5 as runner
import read_v23_native_s5 as reader
from build_v23_native_s5_owner import COMPILED

class Boundary(unittest.TestCase):
    def test_complete_receipt_binding_and_changed_inputs(self):
        original_table,allrows=runner.cases()
        expected=next(r for r in allrows if r['id']=='shift-Right@caret-mid/backspace')
        setup=next(r for r in original_table['cases'] if r['id']==expected['sourceArm'])
        fixture=(runner.ROOT/original_table['fixture']['path']).read_bytes()
        xml=fixture.replace(b'<office:document ',b'<office:document-content ').replace(b'</office:document>',b'</office:document-content>')
        for mutation in ('none','receipt','source','header'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp,contextlib.ExitStack() as stack:
                p=Path(tmp);tools=p/'tools';tools.mkdir();install=p/'install';install.mkdir()
                (install/'libstandin.so').write_bytes(b'standin library')
                sources=[]
                for name in COMPILED:
                    f=tools/name;f.write_text('standin '+name);sources.append(f)
                header=p/'header.h';header.write_text('standin header')
                binary=p/'binary';binary.write_bytes(b'standin binary; execution mocked')
                fx=p/'fixture.fodt';fx.write_bytes(fixture)
                receipt=p/'build-receipt.json'
                build={'exitCode':0,'protectedInputsUnchanged':True,'snapshotsMatch':True,
                       'binary':{'path':str(binary),'sha256':runner.sha(binary)},
                       'sources':{str(f.relative_to(p)):runner.sha(f) for f in sources},
                       'headers':{'header.h':runner.sha(header)}}
                receipt.write_text(json.dumps(build))
                table=copy.deepcopy(original_table);table['fixture']={'path':'fixture.fodt','sha256':runner.sha(fx)}
                table['inputPins']={'fixture.fodt':runner.sha(fx)}
                for module in (runner,reader):
                    for key,value in [('ROOT',p),('TOOLS',tools),('SOURCES',sources)]:stack.enter_context(patch.object(module,key,value))
                    stack.enter_context(patch.object(module,'cases',return_value=(table,[expected])))
                out=p/'out'
                argv=['runner','--binary',str(binary),'--install',str(install),'--build-receipt',str(receipt),'--out',str(out)]
                stack.enter_context(patch.object(sys,'argv',argv))
                def check_output(command,**kw):
                    if command[-1]=='--inventory':return json.dumps({'id':expected['id'],'sequence':expected['sequence']})+'\n'
                    self.assertEqual(command[-1],'--paragraphs')
                    return '\n'.join(reader.paragraph_texts_from_xml(fixture))+'\n'
                stack.enter_context(patch.object(runner.subprocess,'check_output',side_effect=check_output))
                def execute(command,stdout,stderr,env):
                    self.assertEqual(command[3],str(binary))
                    self.assertNotIn('SAL_LOK_OPTIONS',env)
                    for label in ('before','after'):
                        with zipfile.ZipFile(out/'saves'/f'{label}.odt','w') as z:z.writestr('content.xml',xml)
                    sel=setup['setup']['expectedSelection'];point=setup['setup']['expectedMovingPointName'];rect='10,20,0,30'
                    state={'getTextSelection':sel,'INVALIDATE_VISIBLE_CURSOR':rect}
                    row={'id':expected['id'],'shape':setup['shape'],'key':setup['key'],'family':expected['family'],
                         'sequence':expected['sequence'],'mode':'default-native-queued','expectedSelection':sel,
                         'expectedCursorPoint':point,'expectedCursorRect':rect,'before':state,'beforePost':state,
                         'after':state,'beforeSelectionType':0,'afterSelectionType':0,
                         'openedSettleMs':800,'setupSettleMs':800,'finalSettleMs':800,
                         'savedBefore':True,'savedAfter':True,'beforeFile':'before.odt','afterFile':'after.odt',
                         'posts':[dict(x,atMs=i,returnMs=i+.1) for i,x in enumerate(reader.expected_posts(expected))]}
                    stdout.write(json.dumps({'arm':'discover-stub','steps':[{'name':point,'rect':rect}]})+'\n'+json.dumps(row)+'\n')
                    if mutation=='receipt':receipt.write_text(receipt.read_text()+'\n')
                    elif mutation=='source':sources[0].write_text('changed source')
                    elif mutation=='header':header.write_text('changed header')
                    return type('Result',(),{'returncode':0})()
                stack.enter_context(patch.object(runner.subprocess,'run',side_effect=execute))
                self.assertEqual(runner.main(),0 if mutation=='none' else 1)
                completion=json.loads((out/'completion.json').read_text())
                self.assertEqual(completion['protectedInputsUnchanged'],mutation=='none')
                if mutation=='none':
                    self.assertEqual(completion['afterIdentity'],json.loads((out/'identity.json').read_text()))
                    self.assertIn('buildReceipt',completion['afterIdentity'])
                result=reader.read(out)
                self.assertEqual(result['verdict']=='NATIVE_S5_SAVES_AVAILABLE',mutation=='none',result['problems'])

if __name__=='__main__':unittest.main()

```

FILE handoff/RUNBOOK-2026-10-26-v23-native-s5.md
```
# Native S5 continuation references: owner build boundary

## Authority and limits

The canonical protocol is `handoff/PROTOCOL-2026-10-26-v23-abi6-feature.md`, ordered-command appendices21/22. Astra scope approved one fresh native execution per native-capable source/family (no historical N3 multiplier), all seven exact families, and the existing default-native queued Writer route. Source population is generated by `v23_feature_s_cases.py`:392 entries from588 where referencePolicy is not settled-WASM. Left/Right196 are native-literal candidates; Home/End196 remain conditional on the later browser's actual single-line witness. Up/Down and other layout-dependent browser references are **not** supplied by this run.

No feature/native/core build or native execution has been performed by this preparation. The only C++ test compilation is a tiny standalone recording stub for the pure sequence header. Product/core/diagnostic artifacts are untouched. No browser counts or parity are implied by native-save availability.

## Source units

- `wasm_sdk_probe/tools/v23_native_s5_sequence.hpp`: seven finite sequences, posted INPUT then UP for every member. Literal `x` is character120/key0 through the same queue, following the existing native `typeChar` implementation; no synchronous paste.
- `wasm_sdk_probe/tools/v23_native_s5.cpp`: includes the unchanged archived-signature source with its main renamed. Its SHA-256 remains `1e29f73bfa0a0b73a5ced6d5f5a91fbaac48bfdfa1fb1c1799514aa0913eef17`. Discovery and shape setup are reused verbatim, performed once per process and per fresh document respectively. Before-save/pre-key selection, actual key calls, post-sequence selection and after-save are recorded. No sleep/read/save occurs between sequence members. Existing800ms quiet/8000ms cap are native observation/setup handling, not a product timing threshold; a cap result is NE, without retry.
- `build_v23_native_s5_owner.py`: owner-only harness compiler, captures three actual compiled source files and LibreOfficeKit header hashes, compiles captured source bytes, records compiler/argv/stdout/stderr and binary receipt. No core build.
- `run_v23_native_s5.py`: finite dispatcher; requires the successful owner build receipt and exact binary/source binding, compares compiled inventory and fixture paragraphs with the source-derived population before opening documents. Uses one process, fresh profile, fresh fixture copy and one new document per cell. Retains all failed outputs; no automatic retry or cleanup.
- `read_v23_native_s5.py`: actual source/core/binary/output binding, membership, actual FIFO post sequence, discovery/selection/caret checks and saved content parsing. Output status is `NATIVE_S5_SAVES_AVAILABLE`, never browser PASS. `compare_saved` uses the unchanged paragraph-merge `reduce_content` for deletion or paragraph text for typing; no hash-only manifest assertion substitutes for content comparison.
- `tests/test_v23_native_s5_boundary.py`: runner-to-reader normal completion and changed receipt/source/header controls with stand-in files and a mocked native process, no LOK. The same validated build receipt is included in both identity snapshots.
- `tests/test_v23_native_s5.py`: focused finite-population, recording-stub, wrong-post/order/setup/save and structural/text comparator red controls. Does not launch LOK.

## Owner-only harness build

From `/home/jiajun/LibreOffice/study_LiteCore`, inspect load and concurrent builds first. The following command compiles only the small harness, normally seconds to about a minute; it is not a core or feature relink. The builder refuses an existing output directory and records the exact expanded g++ command. The current included headers are `libreoffice-26-8/include/LibreOfficeKit`; compiler links only dl/pthread and loads the existing native core at runtime.

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
uptime
pgrep -a make
python3 -I wasm_sdk_probe/tools/build_v23_native_s5_owner.py --build --out wasm_sdk_probe/build/native/v23-s5-owner-01
```

Return the exit status and `wasm_sdk_probe/build/native/v23-s5-owner-01/build-receipt.json`, `build.stdout`, `build.stderr`. On failure, preserve the directory and investigate; do not overwrite it or run a historical signature binary instead. Source or header changes after compilation invalidate the receipt check and need a separately authorized fresh harness build.

## Execution after the owner build receipt is reviewed

This is a separate native measurement, expected roughly20–40minutes depending on native load/discovery. Do not overlap load-sensitive browser measurements; root coordinates scheduling. No compiling command is in the runner. The existing runtime install is `/home/jiajun/LibreOffice/study_LiteCore/native-lok-26-8/build/instdir/program` (directory and `libmergedlo.so` verified present read-only during preparation); runner binds its actual shared libraries and rereads them at completion. It sets `SAL_USE_VCLPLUGIN=svp`, explicitly removes `SAL_LOK_OPTIONS` and `OC_A11Y`, and runs `nice -n 10`. This is default-native queued input, not unipoll completion proof.

```bash
python3 -I wasm_sdk_probe/tools/run_v23_native_s5.py \
  --binary wasm_sdk_probe/build/native/v23-s5-owner-01/v23-native-s5 \
  --build-receipt wasm_sdk_probe/build/native/v23-s5-owner-01/build-receipt.json \
  --install native-lok-26-8/build/instdir/program \
  --out findings/evidence/link-batch-v23/feature-protocol/s5-native/run-01
python3 -I wasm_sdk_probe/tools/read_v23_native_s5.py \
  findings/evidence/link-batch-v23/feature-protocol/s5-native/run-01 \
  --output findings/evidence/link-batch-v23/feature-protocol/s5-native/reader-01.json
```

The runner creates only the new output directory and owned profile/fixture/save children. An interrupted process lacking completion, failed settle, missing save, failed setup or changed binding is NE. Do not restart into run-01 or retry until green. The reader must enumerate the entire source-derived native-capable set; no percentage or selected clean subset closes availability.

The before/after ODTs remain actual oracle evidence. Consumers must additionally establish browser fixture/shape/direction and, for Home/End, single-line applicability. Fresh same-browser settled references still require independent browser work: wait only after the Shift terminal and the existing at-least500ms state witness, preserve prefix-delete→Shift and consecutive following deletes. This native tool never promotes a timed candidate save to its own oracle, never supplies Up/Down layout parity, and never supplies the browser overlap witness.

```
