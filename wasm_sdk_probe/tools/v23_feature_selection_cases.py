"""Actual ABI6 selection population and logical setup plans; no browser execution."""
import hashlib
import json
import re
from pathlib import Path
from odt_paragraphs import paragraph_texts_from_xml
from v23_feature_s_cases import ROOT, ARCHIVE, PINS, MOVES, derive, read_rounds

PROJECT=ROOT/'wasm_sdk_probe'
PROFILE='e2-editor-v23'
BROWSERS=('chrome','firefox')
BUNDLE='e2/editor-shell-v2-bundle-v76.json'
BUNDLE_FILE_SHA256='555590f6eb6e7600ed313b7d866a6a0ba30f190efc6e9c97bb86483b05627093'
PAGE_SHA256='c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490'
ARTIFACT_PINS={
 'probe.wasm':'fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658',
 'probe.js':'4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e',
 'sdk-worker.js':'3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5',
 'sdk-manifest.json':'2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91'}
ARCHIVED_PROFILE=PROJECT/'build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6'
FIXTURE=ROOT/ARCHIVE/'fixture-as-run.fodt'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
def sha(path):return digest(Path(path).read_bytes())

def paragraphs():
    raw=FIXTURE.read_bytes()
    if digest(raw)!=PINS['fixture-as-run.fodt']:raise ValueError('native fixture differs')
    return paragraph_texts_from_xml(raw)

def point_plan(name,texts):
    """Native names identify logical inputs; no native coordinates are copied."""
    if name in ('w.l1start','w.l1end'):
        return {'name':name,'paragraph':4,'query':texts[4],
                'anchor':'search-first-displayed-line','offset':0 if name.endswith('start') else 'visual-end',
                'prefixRule':'empty' if name.endswith('start') else 'nonempty-query-prefix',
                'requiredWitness':'actual-first-line-start-and-end-affinity'}
    match=re.fullmatch(r'p([0-9]+)\.([0-9]+|end)',name)
    if not match:raise ValueError('unknown native logical point: '+name)
    paragraph=int(match[1]);offset=match[2]
    if not 0<=paragraph<len(texts):raise ValueError('logical paragraph outside fixture')
    if not texts[paragraph]:
        if name!='p3.0':raise ValueError('undeclared empty-paragraph traversal')
        return {'name':name,'paragraph':paragraph,'searchParagraph':2,'query':texts[2],
                'anchor':'search-text-start','offset':'next-empty','prefix':texts[2]+'\n',
                'requiredWitness':'preceding-paragraph-end-right-empty-caret'}
    if offset=='end':offset=len(texts[paragraph])
    else:offset=int(offset)
    if offset>len(texts[paragraph]):raise ValueError('logical offset outside fixture')
    return {'name':name,'paragraph':paragraph,'query':texts[paragraph],
            'anchor':'search-text-start','offset':offset,'prefix':texts[paragraph][:offset],
            'requiredWitness':'actual-text-start-prefix-and-restored-caret'}

def cases(table=None):
    table=table if table is not None else derive(read_rounds());texts=paragraphs();result={}
    for row in table['cases']:
        setup=row['setup'];names=setup['logicalPointNames']
        if row['id'] in result:raise ValueError('duplicate selection case')
        method=setup['method']
        if method not in ('click','drag','click+Shift+Right x3','click+End'):
            raise ValueError('unmapped native shape method: '+method)
        if len(names)!=(2 if method=='drag' else 1):raise ValueError('native shape point arity differs')
        points={n:point_plan(n,texts) for n in dict.fromkeys(names+[setup['expectedMovingPointName']])}
        # Actual executable route remains declared separately from native provenance.
        result[row['id']]={**row,'pointPlans':points,'nativeSetupMethod':method,
            'anchorPointName':names[0], 'movingPointName':setup['expectedMovingPointName'],
            'productKey':{'key':{'Left':'ArrowLeft','Right':'ArrowRight','Up':'ArrowUp','Down':'ArrowDown',
                                 'Home':'Home','End':'End'}[row['key']], 'shiftKey':row['extendSelection']},
            'reference':{'freshOriginalDocument':True,'fromPoint':setup['expectedMovingPointName'],
                         'key':row['key'],'shiftKey':False,
                         'logicalEndpointWitness':'NOT_ESTABLISHED_UNPERFORMED',
                         'nativeLiteralRequired':row['key'] in ('Left','Right'),
                         'singleLineRequiredForHomeEndNative':row['key'] in ('Home','End')},
            'default':'NOT_ESTABLISHED_UNPERFORMED'}
    if len(result)!=108:raise ValueError('selection population differs')
    return result

def interactions(table,rounds,texts):
    """S4: every native kind=interaction row; its caret-mid origin comes from the S1 shape table."""
    origins={tuple(r['setup']['logicalPointNames']) for r in table['cases'] if r['shape']=='caret-mid'}
    if len(origins)!=1 or len(next(iter(origins)))!=1:raise ValueError('caret-mid origin not unique')
    origin=next(iter(origins))[0]
    keys={'Shift+Right':('ArrowRight','move-character-right'),'Shift+Down':('ArrowDown','move-line-down'),
          'Shift+End':('End','move-line-end')}
    methods={'a':'click','b':'drag','c':'public-select-range'}
    result={}
    for row in table['S4']:
        natives=[]
        for ref in row['nativeReferences']:
            native=rounds[ref['round']-1][ref['line']-1]
            if native.get('sourceLine')!=ref['line'] or native.get('arm')!=row['id'] or native.get('kind')!='interaction':
                raise ValueError('native interaction reference differs')
            natives.append(native)
        names=row['logicalPointNames']
        if row['id'] in result or row['step'] not in methods or row['firstKey'] not in keys or len(natives)!=3 \
                or len(names)!=(1 if row['step']=='a' else 2):
            raise ValueError('unmapped native interaction')
        key,action=keys[row['firstKey']]
        result[row['id']]={**row,'method':methods[row['step']],'originPointName':origin,
            'firstProductKey':{'key':key,'shiftKey':True},'firstAction':action,
            'pointPlans':{n:point_plan(n,texts) for n in dict.fromkeys([origin]+names)},
            'nativeAfterFirstKeyText':[n['afterFirstKey']['getTextSelection'] for n in natives],
            'nativeAfterStepText':[n['afterStep']['getTextSelection'] for n in natives],
            'nativeShiftHomeAfterClickText':[n['shiftHomeAfterClick'] for n in natives] if row['step']=='a' else None,
            'memberships':['S4'],'default':'NOT_ESTABLISHED_UNPERFORMED'}
    if len(result)!=9:raise ValueError('S4 population differs')
    return result

NATIVE_S5=ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native'
NATIVE_S5_READER_SHA256='014c1e0d51f6a522101c2acc6395797a8f974822cf085c8ea7f8f978b64ec538'
NATIVE_S5_TYPE_READER_SHA256='305306785509764f1130709650ca44c8a6c0cc320b0d79bb632bbe0817870706'
NATIVE_S5_EMPTY_MARK_READER_SHA256='fc62e6adb4aaba82a75c868337b3988efa2c30ddb3ad66b613776445a9767974'
S5_KEYS={'Shift+Left':('ArrowLeft',('shift',)),'Shift+Right':('ArrowRight',('shift',)),'Shift+Up':('ArrowUp',('shift',)),
         'Shift+Down':('ArrowDown',('shift',)),'Shift+Home':('Home',('shift',)),'Shift+End':('End',('shift',)),
         'Backspace':('Backspace',()),'Delete':('Delete',()),'text:x':('x',())}

# Fable ruling 3 Addendum 1 item 2: fallback A only for the ruling's named witness reasons,
# (i) post order, (ii) the between-read, (iii) cap or missing read.  Any other reader reason
# is an instrument failure; the plan then refuses, so S5 cannot count until it is resolved.
TYPE_WITNESS_REASONS=frozenset({'actual FIFO key posts differ','invalid actual post ordering',
    'missing Shift settle','Shift settle reached its cap','missing between-read','Shift/x posts not uniquely recorded',
    'between-read does not follow the Shift posts','between-read does not complete before the x post',
    'between-read selection differs from the three native rounds','silent member not collapsed at the between-read',
    'native round caret not comparable with this run','silent member caret not at the moving point'})

def type_fallback(cell):
    reasons=cell.get('reasons')
    if cell.get('status')!='NOT_ESTABLISHED' or not reasons:raise ValueError('native S5 type cell neither witnessed nor reasoned: '+cell['id'])
    invalid=[r for r in reasons if r not in TYPE_WITNESS_REASONS]
    if invalid:raise ValueError('native S5 type cell failed validity, not its witness: '+cell['id']+': '+'; '.join(invalid))
    return reasons

def empty_mark_route(row_id,cell):
    """Fable ruling 4: (emptyMark, witness record, orderIndependent) from the bound witness reader."""
    if cell is None:raise ValueError('empty-mark witness missing: '+row_id)
    record=cell.get('witness')
    if cell.get('status')!='WITNESSED' or not isinstance(cell.get('emptyMark'),bool) or not isinstance(record,dict) \
       or cell.get('orderIndependent') not in (True,False):raise ValueError('empty-mark witness malformed: '+row_id)
    empty=record.get('selectionType')==0 and record.get('text')=='' and record.get('TEXT_SELECTION')==''
    nonempty=record.get('selectionType')!=0 and (record.get('text')!='' or record.get('TEXT_SELECTION')!='')
    if cell['emptyMark']!=empty or not (empty or nonempty):raise ValueError('empty-mark witness malformed: '+row_id)
    return cell['emptyMark'],{'run':'empty-mark-witness-01','text':record['text'],'selectionType':record['selectionType']},cell['orderIndependent']

def native_saves(run,cell):
    saves={}
    for side in ('before','after'):
        path=NATIVE_S5/run/'saves'/Path(cell['saves'][side]['path']).name
        if sha(path)!=cell['saves'][side]['sha256']:raise ValueError('native S5 save bytes differ: '+cell['id'])
        saves[side]={'path':str(path.relative_to(ROOT)),'sha256':cell['saves'][side]['sha256']}
    return saves

def s5(table,cases_by_id):
    """S5: every Table 1 arm by the seven families, with the native references bound by hash:
    run-01 for the deletion families, run-03 for type (fable ruling 3; run-02 printed timestamps
    too coarse to witness order).  run-01's type saves measured x-then-Shift and are never an
    oracle; a type cell without run-03's order witness takes the fresh settled-WASM
    reference (fallback A), its reasons recorded.  A deletion cell whose bound native witness
    shows an empty mark after its Shift (fable ruling 4) takes the settled-WASM arm too."""
    raw=(NATIVE_S5/'reader-01.json').read_bytes()
    if digest(raw)!=NATIVE_S5_READER_SHA256:raise ValueError('native S5 reader output differs')
    native=json.loads(raw)
    if native.get('verdict')!='NATIVE_S5_SAVES_AVAILABLE' or native.get('problems')!=[]:raise ValueError('native S5 references unavailable')
    native={c['id']:c for c in native['cells']}
    raw=(NATIVE_S5/'reader-03.json').read_bytes()
    if digest(raw)!=NATIVE_S5_TYPE_READER_SHA256:raise ValueError('native S5 type reader output differs')
    typed=json.loads(raw)
    if typed.get('verdict')!='NATIVE_S5_TYPE_SAVES_READ' or typed.get('problems')!=[]:raise ValueError('native S5 type references unavailable')
    typed={c['id']:c for c in typed['cells']}
    raw=(NATIVE_S5/'empty-mark-reader-01.json').read_bytes()
    if digest(raw)!=NATIVE_S5_EMPTY_MARK_READER_SHA256:raise ValueError('native S5 empty-mark reader output differs')
    marks=json.loads(raw)
    if marks.get('verdict')!='NATIVE_S5_EMPTY_MARK_WITNESS_READ' or marks.get('problems')!=[]:raise ValueError('native S5 empty-mark witness unavailable')
    marks={c['id']:c for c in marks['cells']}
    result={}
    for row in table['S5']:
        source=cases_by_id.get(row['sourceArm'])
        if row['id'] in result or source is None or not source['extendSelection']:raise ValueError('unmapped S5 source arm')
        keys=[S5_KEYS[k] for k in row['sequence']]
        shift=[i for i,k in enumerate(row['sequence']) if k.startswith('Shift+')]
        if len(shift)!=1 or row['sequence'][shift[0]]!='Shift+'+source['key']:raise ValueError('S5 sequence differs from its source arm')
        reference=witness=fallback=empty=mark=independent=None
        if row['referencePolicy']!='settled-wasm' and row['family']=='type':
            cell=typed.get(row['id'])
            if cell is None:raise ValueError('native S5 type cell missing: '+row['id'])
            if cell.get('status')=='NATIVE_SAVE_AVAILABLE' and cell.get('orderWitness') in ('selection-before-x','settle-only'):
                reference=native_saves('run-03',cell);witness=cell['orderWitness']
                # The strong label needs a between-read that Shift changed; else only settle-only
                # is witnessed (review item D; 0 of run-03's 47 strong cells are affected).
                if witness=='selection-before-x' and cell['between']['getTextSelection']==source['setup']['expectedSelection']:
                    raise ValueError('strong order witness without a Shift-changed selection: '+row['id'])
            else:fallback=type_fallback(cell)
        elif row['referencePolicy']!='settled-wasm':
            cell=native.get(row['id'])
            if cell is None or cell.get('status')!='NATIVE_SAVE_AVAILABLE':raise ValueError('native S5 save missing: '+row['id'])
            # Fable ruling 4: an empty-mark cell's run-01 save records Writer's empty-mark deletion,
            # not the target; it compares with its settled-WASM arm and carries no native save.
            empty,mark,independent=empty_mark_route(row['id'],marks.get(row['id']))
            if not empty:reference=native_saves('run-01',cell)
        result[row['id']]={'id':row['id'],'sourceArm':row['sourceArm'],'family':row['family'],'sequence':row['sequence'],
            'keys':[{'key':k,'mods':list(m)} for k,m in keys],'shiftIndex':shift[0],'comparison':row['comparison'],
            'referencePolicy':row['referencePolicy'],'native':reference,'nativeOrderWitness':witness,'nativeFallback':fallback,
            'emptyMark':empty,'emptyMarkWitness':mark,'nativeOrderIndependent':independent,
            'memberships':['S5'],'settledReference':row['referencePolicy']!='native' or reference is None,
            'default':'NOT_ESTABLISHED_UNPERFORMED'}
    if len(result)!=588:raise ValueError('S5 population differs')
    return result

# ---- R1 (handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md) ----------------------------------------
# The population is collect_v23_r1_inputs.collect(), bound to the committed index by hash; the
# fixture of every cell is the one whose native text rendering equals the cell's native text.
R1_INDEX=ROOT/'findings/evidence/link-batch-v23/feature-protocol/r1/native-inputs.json'
R1_INDEX_SHA256='6e13c04d6acc901bdc7988d65ac4e616a9bf35ddbcce5549dbb76f6e40ab6fdd'
R1_TABLE='urn:oasis:names:tc:opendocument:xmlns:table:1.0'
R1_KEYS={'Left':'ArrowLeft','Right':'ArrowRight','Up':'ArrowUp','Down':'ArrowDown','Home':'Home','End':'End'}
MOVES_R1={k:v[0] for k,v in MOVES.items()}
# The Shape table of the source-as-run (tools/f129_native_point_click.cpp, bound by collect()),
# restated as logical inputs; no native coordinate enters.  An offset is {'offset': n} or
# {'wrapDelta': d}, d counted from the shape paragraph's first visual wrap W, which the browser
# discovers itself (its own Right walk).  Drag and Shift+End points follow from the native
# selected text.  Every entry is cross-checked against the native records in r1().
R1_SHAPES={
 'p2-forward':{'fixture':'arrow-selection','method':'keys','key':'Right','count':10,'anchor':(1,{'offset':9}),'point':(1,{'offset':19})},
 'p2-backward':{'fixture':'arrow-selection','method':'keys','key':'Left','count':10,'anchor':(1,{'offset':19}),'point':(1,{'offset':9})},
 's1':{'fixture':'arrow-selection-shapes','wrap':'s1','paragraph':0,'method':'keys','key':'Right','count':10,'anchor':(0,{'wrapDelta':-10}),'point':(0,{'wrapDelta':0})},
 's2':{'fixture':'arrow-selection-shapes','method':'keys','key':'Right','count':11,'anchor':(1,{'offset':9}),'point':(1,{'offset':20})},
 's3':{'fixture':'arrow-selection-shapes','method':'keys','key':'Right','count':10,'anchor':(2,{'offset':25}),'point':(3,{'offset':0})},
 's4':{'fixture':'arrow-selection-shapes','method':'keys','key':'Right','count':7,'anchor':(5,{'offset':3}),'point':(5,{'offset':10})},
 's5':{'fixture':'arrow-selection-shapes','method':'keys','key':'Right','count':5,'anchor':(5,{'offset':11}),'point':(6,{'offset':0}),'cellSelection':True},
 's1e':{'fixture':'arrow-selection-shapes','wrap':'s1','paragraph':0,'method':'shift-end','anchor':(0,{'wrapDelta':-10})},
 'm1r':{'fixture':'arrow-selection-wrap','wrap':'m1','paragraph':0,'method':'keys','key':'Right','count':10,'anchor':(0,{'wrapDelta':-10}),'point':(0,{'wrapDelta':0})},
 'm1e':{'fixture':'arrow-selection-wrap','wrap':'m1','paragraph':0,'method':'shift-end','anchor':(0,{'wrapDelta':-10})},
 's1d':{'fixture':'arrow-selection-shapes','wrap':'s1','paragraph':0,'method':'drag'},
 'm1d':{'fixture':'arrow-selection-wrap','wrap':'m1','paragraph':0,'method':'drag'},
}

def r1_layout(raw):
    """Paragraphs in paragraph_texts_from_xml order and each one's container: 'body' or [table,row,cell]."""
    import xml.etree.ElementTree as ET
    from odt_paragraphs import PARAGRAPHS,CONTAINERS,OFFICE,_inline
    t=lambda name:'{'+R1_TABLE+'}'+name
    body=ET.fromstring(raw).find('{'+OFFICE+'}body')
    if body is None:raise ValueError('R1 fixture has no office:body')
    parent={child:node for node in body.iter() for child in node}
    tables=[x for x in body.iter() if x.tag==t('table')];texts=[];where=[]
    for element in body.iter():
        if element.tag not in PARAGRAPHS:continue
        parts=[];_inline(element,parts);texts.append(''.join(parts))
        chain=[];node=element
        while node in parent:node=parent[node];chain.append(node)
        if any(x.tag in CONTAINERS for x in chain):raise ValueError('R1 fixture: note/frame/annotation paragraph not modelled')
        cells=[x for x in chain if x.tag in (t('table-cell'),t('covered-table-cell'))]
        if not cells:where.append('body');continue
        if len(cells)!=1 or cells[0].tag!=t('table-cell'):raise ValueError('R1 fixture: nested or covered cell not modelled')
        cell=cells[0];row=parent[cell];table=parent.get(row)
        if row.tag!=t('table-row') or table is None or table.tag!=t('table'):raise ValueError('R1 fixture: row group not modelled')
        rows=[x for x in table if x.tag==t('table-row')];columns=[x for x in row if x.tag in (t('table-cell'),t('covered-table-cell'))]
        if any(x.get(t(a)) for x in rows+columns for a in ('number-rows-repeated','number-columns-repeated','number-columns-spanned','number-rows-spanned')):
            raise ValueError('R1 fixture: repeated or spanned cell not modelled')
        where.append([tables.index(table),rows.index(row),columns.index(cell)])
    if texts!=paragraph_texts_from_xml(raw):raise ValueError('R1 fixture paragraph order differs')
    return texts,where

def r1_rendering(texts,where):
    """The native `.uno:SelectAll` text/plain form: paragraphs joined by newline, cells of one table
    row by tab, a line break (U+2028 in the save) as newline.  Returns the text and each
    paragraph's [start,end] span in it (code points)."""
    out='';spans=[]
    for i,text in enumerate(texts):
        if i:
            a,b=where[i-1],where[i]
            out+='\t' if a!='body' and b!='body' and a[:2]==b[:2] and a[2]!=b[2] else '\n'
        start=len(out);out+=text.replace('\u2028','\n');spans.append((start,len(out)))
    return out,spans

def r1_position(spans,index):
    """Native text index -> the unique (paragraph, code-point offset)."""
    found=[(i,index-s) for i,(s,e) in enumerate(spans) if s<=index<=e]
    if len(found)!=1:raise ValueError('native text index maps to no or several logical positions')
    return found[0]

def r1_index(spans,position):
    p,o=position
    if not 0<=p<len(spans) or not 0<=o<=spans[p][1]-spans[p][0]:raise ValueError('logical position outside the fixture')
    return spans[p][0]+o

def r1_marker(fixtures,text):
    """A native marked text -> (fixture stem, (paragraph, offset)); unique, and round-tripped."""
    if not isinstance(text,str) or text.count('#')!=1:raise ValueError('native marker not unique')
    g=text.index('#');plain=text[:g]+text[g+1:]
    found=[stem for stem,f in fixtures.items() if f['rendering']==plain]
    if len(found)!=1:raise ValueError('native text does not identify exactly one fixture')
    f=fixtures[found[0]];p,o=r1_position(f['spans'],g)
    marked=list(f['paragraphs']);marked[p]=marked[p][:o]+'#'+marked[p][o:]
    if r1_rendering(marked,f['containers'])[0]!=text:raise ValueError('marker position not consistent with the fixture paragraphs')
    return found[0],(p,o)

def r1_saved_marker(saved,original):
    """Saved paragraphs -> (paragraph, offset) of the one '#'; everything else must be the original."""
    hits=[(p,t.index('#')) for p,t in enumerate(saved) if '#' in t]
    if len(saved)!=len(original) or len(hits)!=1 or saved[hits[0][0]].count('#')!=1:return None
    p,o=hits[0]
    if saved[p][:o]+saved[p][o+1:]!=original[p] or any(a!=b for i,(a,b) in enumerate(zip(saved,original)) if i!=p):return None
    return p,o

def r1_point_plan(texts,spec,wrap=None):
    """A located point's logical plan, the shape the page's locate() takes.  The query is the
    paragraph's text up to its first hard break, so no prefix crosses one."""
    p=spec['paragraph']
    if not 0<=p<len(texts):raise ValueError('R1 point outside the fixture')
    segment=lambda q:texts[q].split('\u2028')[0]
    base={'name':spec['name'],'paragraph':p}
    if spec['kind']=='next-empty':
        if texts[p] or p==0 or not texts[p-1] or '\u2028' in texts[p-1]:raise ValueError('undeclared empty-paragraph traversal')
        return {**base,'searchParagraph':p-1,'query':texts[p-1],'anchor':'search-text-start','offset':'next-empty',
                'prefix':texts[p-1]+'\n','requiredWitness':'preceding-paragraph-end-right-empty-caret'}
    if not texts[p]:raise ValueError('an empty paragraph is reached by next-empty only')
    if spec['kind']=='visual-end':
        return {**base,'query':segment(p),'anchor':'search-text-start','offset':'visual-end','requiredWitness':'actual-first-line-end'}
    if spec['kind']!='offset':raise ValueError('unknown R1 point kind')
    if spec.get('wrapDelta') is None:offset=spec['offset']
    elif type(wrap) is int:offset=wrap+spec['wrapDelta']
    else:raise ValueError('wrap-relative point without a discovered wrap')
    if type(offset) is not int or not 0<=offset<=len(segment(p)):raise ValueError('logical offset outside the paragraph line segment')
    return {**base,'query':segment(p),'anchor':'search-text-start','offset':offset,'prefix':texts[p][:offset],
            'requiredWitness':'actual-text-start-prefix-and-restored-caret'}

def r1_logical(plan,selected=None):
    """(paragraph, offset) of a located point; a line end takes its actual prefix length."""
    if plan['offset']=='next-empty':return (plan['paragraph'],0)
    if plan['offset']=='visual-end':
        if not isinstance(selected,str):raise ValueError('line end without its prefix')
        return (plan['paragraph'],len(selected))
    return (plan['paragraph'],plan['offset'])

def r1_walk_logical(texts,start,key,count):
    p,o=start
    for _ in range(count):
        if key=='Right':
            if o<len(texts[p]):o+=1
            elif p+1<len(texts):p,o=p+1,0
            else:raise ValueError('logical walk leaves the fixture')
        else:
            if o>0:o-=1
            elif p>0:p,o=p-1,len(texts[p-1])
            else:raise ValueError('logical walk leaves the fixture')
    return p,o

def r1_native_wraps(collected):
    """The as-run discover rows (wrapOffset per round) beside the ref/emu records collect() binds."""
    from collect_v23_r1_inputs import NATIVE,SOURCES,ROUNDS
    wraps={}
    for _,directory in SOURCES:
        for round_id in ROUNDS:
            rel=str(NATIVE/directory/f'arms-r{round_id}.jsonl');raw=(ROOT/rel).read_bytes()
            if collected['files'].get(rel)!=digest(raw):raise ValueError('native discover rows not bound: '+rel)
            for line in raw.decode().splitlines():
                row=json.loads(line) if line.strip() else {}
                if str(row.get('arm','')).startswith('discover-'):
                    wraps.setdefault(row['arm'].removeprefix('discover-'),set()).add(row.get('wrapOffset'))
    if any(len(v)!=1 or not isinstance(next(iter(v)),int) for v in wraps.values()):raise ValueError('native wrap discovery unstable')
    return {k:next(iter(v)) for k,v in wraps.items()}

def r1_fixtures(collected):
    out={}
    for path,pin in collected['fixtures'].items():
        raw=(ROOT/path).read_bytes()
        if digest(raw)!=pin:raise ValueError('R1 fixture bytes differ: '+path)
        texts,where=r1_layout(raw)
        if any('#' in t for t in texts):raise ValueError('R1 fixture already contains the marker')
        rendering,spans=r1_rendering(texts,where);stem=Path(path).stem
        out[stem]={'path':path,'sha256':pin,'servedName':'r1-'+stem+'.odt','paragraphs':texts,'containers':where,
                   'rendering':rendering,'spans':[list(s) for s in spans]}
    return out

def r1_setup(shape,recipe,texts,where,made,native_wrap):
    """Executable setup of one shape, plus its native logical setup (native W only here)."""
    spec=lambda name,p,o:{'name':name,'paragraph':p,'kind':'next-empty' if not texts[p] else 'offset',**o}
    walk=None
    if recipe.get('wrap'):
        p=recipe['paragraph']
        if 'anchor' in recipe and recipe['anchor'][0]!=p:raise ValueError('R1 wrap shape leaves its paragraph')
        walk={'paragraph':p,'query':texts[p].split('\u2028')[0],'limit':len(texts[p])}
    method=recipe['method']
    if method=='keys':
        (ap,ao),(pp,po)=recipe['anchor'],recipe['point']
        points=[spec('anchor',ap,ao),spec('point',pp,po)]
        selection=('anchor','point')
        if recipe.get('cellSelection'):
            points.append(spec('selectionEnd',ap,{'offset':len(texts[ap])}));selection=('anchor','selectionEnd')
        caret={'kind':'equals','point':'point'};point_name='point'
    else:
        p=walk['paragraph']
        anchor=recipe['anchor'][1] if method=='shift-end' else {'wrapDelta':-len(made)}
        end=anchor['wrapDelta']+len(made) if method=='shift-end' else 0
        points=[spec('anchor',p,anchor),{'name':'line1End','paragraph':p,'kind':'visual-end'},spec('selectionEnd',p,{'wrapDelta':end})]
        selection=('anchor','selectionEnd');point_name='selectionEnd'
        caret={'kind':'equals' if method=='shift-end' else 'line1-at-or-after','point':'line1End'}
    setup={'method':method,'walk':walk,'points':points,'caret':caret,'selection':list(selection),'pointName':point_name,
           'productKey':None if method=='drag' else R1_KEYS[recipe['key'] if method=='keys' else 'End'],
           'action':None if method=='drag' else MOVES_R1[recipe['key'] if method=='keys' else 'End'],
           'count':recipe['count'] if method=='keys' else None,'cellSelection':bool(recipe.get('cellSelection'))}
    # Native cross-check: the recipe with the native W reproduces the native selected text.
    plans={s['name']:r1_point_plan(texts,s,native_wrap) for s in points if s['kind']!='visual-end'}
    anchor=r1_logical(plans['anchor']);point=r1_logical(plans[point_name])
    if method=='keys' and r1_walk_logical(texts,anchor,recipe['key'],recipe['count'])!=point:raise ValueError('R1 shape walk differs: '+shape)
    rendering,spans=r1_rendering(texts,where);a,b=sorted((r1_index(spans,anchor),r1_index(spans,point)))
    if setup['cellSelection']:
        s0=spans[anchor[0]][0];s1=spans[point[0]][1]
        if made!=rendering[s0:s1]+'\n':raise ValueError('R1 cell selection differs from native: '+shape)
    elif rendering[a:b]!=made:raise ValueError('R1 shape does not reproduce the native selected text: '+shape)
    return setup,{'anchor':list(anchor),'point':list(point)}

def r1_premise(texts,where,point):
    p=point[0]
    if not texts[p]:return 'empty-paragraph'
    if '\u2028' in texts[p]:return 'hard-break-line'
    return 'table-cell-line' if where[p]!='body' else 'single-visual-line'

def r1(collected=None):
    """R1: every generated cell, its fixture, oracle class, control rule and native logical landing."""
    from collect_v23_r1_inputs import collect
    if collected is None:
        # The live collection and the committed index are both the pinned bytes.
        collected=collect()
        if digest(encoded(collected))!=R1_INDEX_SHA256 or digest(R1_INDEX.read_bytes())!=R1_INDEX_SHA256:
            raise ValueError('R1 native index differs from the committed native-inputs.json')
    fixtures=r1_fixtures(collected);wraps=r1_native_wraps(collected)
    controls={c['id']:c for c in collected['wrongOldClickControls']}
    if set(R1_SHAPES)!={c['shape'] for c in collected['cells']}:raise ValueError('R1 shape table differs from the native population')
    result={};setups={}
    for cell in collected['cells']:
        if cell['id'] in result:raise ValueError('duplicate R1 cell')
        recipe=R1_SHAPES[cell['shape']];native=cell['native']
        stem,marker=r1_marker(fixtures,native['text'])
        if stem!=recipe['fixture']:raise ValueError('R1 cell fixture differs from its shape: '+cell['id'])
        f=fixtures[stem];texts,where=f['paragraphs'],f['containers']
        if native['selectedAfterKey']!='':raise ValueError('native move did not collapse: '+cell['id'])
        wrap=wraps[recipe['wrap']] if recipe.get('wrap') else None
        setup,setup_logical=r1_setup(cell['shape'],recipe,texts,where,native['made'],wrap)
        if setups.setdefault(cell['shape'],(setup,setup_logical))!=(setup,setup_logical):raise ValueError('R1 shape setup unstable')
        wrapped=bool(recipe.get('wrap'))
        literal=cell['key'] in ('Left','Right') or (cell['key'] in ('Home','End') and not wrapped)
        old=controls.get(cell['id'])
        if old and literal:raise ValueError('wrong-old-click control on a literal cell')
        emulated=None
        if old:
            emulated=list(r1_position(f['spans'],old['emulatedMarkerIndex']))
            if old['nativeMarkerIndex']!=cell['nativeMarkerIndex'] or not cell['oldClickEmulationDiffers']:raise ValueError('wrong-old-click control differs')
        elif cell['oldClickEmulationDiffers']:raise ValueError('undeclared old-click difference')
        result[cell['id']]={'id':cell['id'],'group':cell['group'],'shape':cell['shape'],'key':cell['key'],'memberships':['R1'],
            'fixture':stem,'productKey':{'key':R1_KEYS[cell['key']],'shiftKey':False},'action':MOVES_R1[cell['key']],
            'oracle':'literal' if literal else 'layout-relative',
            'control':None if literal else {'rule':'emuend' if old else 'emu','freshOriginalDocument':True,'key':cell['key'],'shiftKey':False},
            'literalPremise':r1_premise(texts,where,setup_logical['point']) if literal and cell['key'] in ('Home','End') else None,
            'wrongOldClickControl':None if not old else {'rounds':old['rounds'],'nativeMarkerIndex':old['nativeMarkerIndex'],
                                                         'emulatedMarkerIndex':old['emulatedMarkerIndex'],'emulatedLogical':emulated},
            'setup':setup,
            'native':{'made':native['made'],'selectedAfterKey':native['selectedAfterKey'],'markerIndex':cell['nativeMarkerIndex'],
                      'markerLogical':list(marker),'setupLogical':setup_logical,'wrapOffset':wrap,'observations':cell['observations']},
            'default':'NOT_ESTABLISHED_UNPERFORMED'}
    oracles=[r['oracle'] for r in result.values()]
    if len(result)!=72 or oracles.count('literal')!=36 or oracles.count('layout-relative')!=36:raise ValueError('R1 population/partition differs')
    if sorted(i for i,r in result.items() if r['control'] and r['control']['rule']=='emuend')!=sorted(controls) or len(controls)!=3:
        raise ValueError('R1 emuend controls differ')
    return result,{stem:{k:v for k,v in f.items() if k in ('path','sha256','servedName','paragraphs','containers')} for stem,f in fixtures.items()}

def identity():
    directory=PROJECT/'dist/profiles'/PROFILE
    for name,expected in ARTIFACT_PINS.items():
        if sha(directory/name)!=expected or sha(ARCHIVED_PROFILE/name)!=expected:
            raise ValueError('actual feature/archive identity differs: '+name)
    manifest=json.loads((directory/'sdk-manifest.json').read_text())
    if manifest['profile']!=PROFILE or manifest['editorContract']['abiVersion']!=6:
        raise ValueError('actual feature ABI/profile differs')
    if sha(PROJECT/BUNDLE)!=BUNDLE_FILE_SHA256:raise ValueError('final shell manifest differs')
    bundle=json.loads((PROJECT/BUNDLE).read_text())
    for row in bundle['included']:
        path=row['path'];served=path.removeprefix('web/')
        if sha(PROJECT/path)!=row['sha256'] or sha(PROJECT/'dist'/served)!=row['sha256']:
            raise ValueError('final shell source/dist differs: '+path)
    if sha(PROJECT/'web/e2-editor-app.js')!=PAGE_SHA256:raise ValueError('final page differs')
    paths=set(ARTIFACT_PINS)
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks',[]):paths.update((pack['data'],pack['metadata']))
    return {'profile':PROFILE,'editorAbi':6,'artifacts':{n:sha(directory/n) for n in sorted(paths)},
            'bundleFileSha256':BUNDLE_FILE_SHA256,'bundleSha256':bundle['bundleSha256'],
            'pageSha256':PAGE_SHA256,'originalHtmlSha256':sha(PROJECT/'web/e2-editor.html')}

def sources():
    import posixpath
    bundle=json.loads((PROJECT/BUNDLE).read_text());out={}
    for row in bundle['included']:
        raw=(PROJECT/row['path']).read_bytes()
        if digest(raw)!=row['sha256']:raise ValueError('frozen source differs')
        out[row['path'].removeprefix('web/')]=raw
    original=(PROJECT/'web/e2-editor.html').read_bytes()
    needle=b'<script type="module" src="./e2-editor-app.js"></script>'
    if original.count(needle)!=1:raise ValueError('product HTML entry differs')
    out['e2-editor.html']=original.replace(needle,b'<script type="module" src="./v23-feature-selection.js"></script>')
    out['v23-feature-selection.js']=(PROJECT/'web/v23-feature-selection.js').read_bytes()
    for name,raw in out.items():
        if not name.endswith('.js'):continue
        for spec in re.findall(r'(?:from\s*|import\s*\(?)\s*[\"\']([^\"\']+)[\"\']',raw.decode()):
            if spec.startswith('.') and posixpath.normpath(posixpath.join(posixpath.dirname(name),spec)) not in out:
                raise ValueError('missing executed import: '+spec)
    return out

def config():
    import ast
    pending=[PROJECT/'tools'/n for n in ('v23_feature_selection_cases.py','run_v23_feature_selection.py','judge_v23_feature_selection.py')]+[PROJECT/'web/serve.py']
    closure=set()
    while pending:
        path=pending.pop().resolve()
        if path in closure:continue
        closure.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                candidate=PROJECT/'tools'/Path(*name.split('.')).with_suffix('.py')
                if candidate.is_file():pending.append(candidate)
    texts=paragraphs();rounds=read_rounds();table=derive(rounds);selection=cases(table)
    s5_plan=s5(table,selection);interaction_plan=interactions(table,rounds,texts);r1_plan,r1_fixture_plan=r1()
    if len({*selection,*interaction_plan,*s5_plan,*r1_plan})!=len(selection)+len(interaction_plan)+len(s5_plan)+len(r1_plan):
        raise ValueError('population identifiers overlap')
    return {'schema':1,'profile':identity(),'servedSources':{n:digest(v) for n,v in sources().items()},
            'instrumentSources':{str(p.relative_to(PROJECT)):sha(p) for p in sorted(closure)},
            'cases':selection,'interactions':interaction_plan,'s5':s5_plan,'r1':r1_plan,'r1Fixtures':r1_fixture_plan,'sourceTable':table,'fixtureSha256':PINS['fixture-as-run.fodt'],
            'fixtureParagraphs':texts,'fixtureManifest':{'fixtures':[{'id':'list-contexts'}]},
            'readinessPoint':point_plan('p0.0',texts),
            'mappingPoints':[point_plan(f'p{i}.0',texts) for i in range(len(texts))]}

def mirror(target,plan):
    target.mkdir(parents=True,exist_ok=False)
    (target/'profiles').symlink_to(PROJECT/'dist/profiles',target_is_directory=True)
    for name,raw in sources().items():
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    (target/'e1-fixtures').mkdir()
    (target/'e1-fixtures/manifest.json').write_bytes(encoded(plan['fixtureManifest']))
    for name in ('e1-fixtures/list-contexts.odt','feature-selection.odt'):(target/name).write_bytes(FIXTURE.read_bytes())
    # R1: each original FODT under its own .odt alias (the SDK's non-ODS suffix guard), opened by fresh().
    for f in plan.get('r1Fixtures',{}).values():(target/f['servedName']).write_bytes((ROOT/f['path']).read_bytes())
    (target/'selection-config.json').write_bytes(encoded(plan))

def verify_mirror(target,plan):
    for name,want in plan['servedSources'].items():
        if sha(target/name)!=want:raise ValueError('actual source mirror differs: '+name)
    for name in ('e1-fixtures/list-contexts.odt','feature-selection.odt'):
        if sha(target/name)!=plan['fixtureSha256']:raise ValueError('actual fixture mirror differs')
    for name,value in [('selection-config.json',plan),('e1-fixtures/manifest.json',plan['fixtureManifest'])]:
        if (target/name).read_bytes()!=encoded(value):raise ValueError('actual config mirror differs')
    receipt={'sources':plan['servedSources'],'fixtureSha256':plan['fixtureSha256'],'configSha256':digest(encoded(plan))}
    if plan.get('r1Fixtures'):
        for f in plan['r1Fixtures'].values():
            if sha(target/f['servedName'])!=f['sha256']:raise ValueError('actual R1 fixture mirror differs: '+f['servedName'])
        receipt['r1Fixtures']={f['servedName']:f['sha256'] for f in plan['r1Fixtures'].values()}
    return receipt
