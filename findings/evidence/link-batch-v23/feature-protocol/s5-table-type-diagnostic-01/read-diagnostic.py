#!/usr/bin/env python3
"""Read the first table/type failure and its fresh two-browser positive/negative controls."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[3]
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
import judge_v23_feature_selection as judge
from odt_paragraphs import paragraph_texts_from_xml
from v23_feature_selection_cases import encoded


def sha(raw):return hashlib.sha256(raw).hexdigest()
def paragraphs(raw):return paragraph_texts_from_xml(zipfile.ZipFile(io.BytesIO(raw)).read('content.xml'))


def read_cell(directory,report,receipt):
    path=directory/receipt['path']
    raw=path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
    assert sha(raw)==receipt['sha256']
    cell=json.loads(raw);page=cell['page'];plan=report['config'];row=plan['s5'][cell['caseId']]
    value=json.loads(encoded(judge.inspect(page,plan,cell['browser'])))
    assert value==cell['inspection']
    arm=page['s5cand'];generation=arm['open']['generation'];window=arm['sequence']
    requests=page['requests'][window['requestStart']:window['requestEnd']]
    insert=[r for r in requests if r['generation']==generation and r['message']['operation']=='insertText']
    extend=[r for r in requests if r['generation']==generation and r['message']['operation']=='editorActionV2'
            and r['message']['payload'].get('extendSelection') is True]
    assert len(insert)==len(extend)==1 and insert[0]['message']['payload']['text']=='x'
    def terminal(request):
        matching=[r for r in page['responses'] if r['generation']==generation and r['message']['requestId']==request['message']['requestId']]
        assert len(matching)==1 and matching[0]['message']['ok'] is True
        return matching[0]
    inserted=terminal(insert[0]);extended=terminal(extend[0])
    assert inserted['message']['result']['method']=='paste'
    assert extended['at']<insert[0]['at']<inserted['at']
    saved={}
    for side,key in [('before','originalSave'),('after','finalSave')]:
        raw=base64.b64decode(arm[key]['base64'],validate=True);assert sha(raw)==arm[key]['sha256']
        saved[side]={'sha256':sha(raw),'paragraphs':paragraphs(raw)}
    assert saved['before']['paragraphs']==plan['fixtureParagraphs']
    native={}
    for side,item in row['native'].items():
        raw=(ROOT/item['path']).read_bytes();assert sha(raw)==item['sha256']
        native[side]={**item,'paragraphs':paragraphs(raw)}
    assert native['before']['paragraphs']==saved['before']['paragraphs']
    return {'cohort':directory.name,'browser':cell['browser'],'caseId':cell['caseId'],'cellSha256':receipt['sha256'],
            'configSha256':sha(encoded(plan)),'verdict':value['verdict'],'inspection':value,
            'family':row['family'],'referencePolicy':row['referencePolicy'],'nativeOrderWitness':row['nativeOrderWitness'],
            'open':arm['open'],'original':saved['before'],'final':saved['after'],'native':native,
            'insertRequest':insert[0],'insertResponse':inserted,'extensionRequest':extend[0],
            'extensionResponse':extended,'insertionPostedAfterExtensionTerminal':True,
            'changedParagraphs':[i for i,(a,b) in enumerate(zip(saved['before']['paragraphs'],saved['after']['paragraphs'])) if a!=b]}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result={'schema':1,'scope':'Existing counted failure plus fresh uncounted controls; no native execution or oracle change',
            'readerSha256':sha(Path(__file__).read_bytes()),'reports':{},'observations':[],'sourceReadings':[]}
    for name in ('s5-counted-02','s5-prep-07'):
        directory=BASE/name;raw=(directory/'report.json').read_bytes();report=json.loads(raw)
        result['reports'][name]={'sha256':sha(raw),'preparationOnly':report['preparationOnly'],'observed':len(report['runs'])}
        receipts=report['runs'][-1:] if name=='s5-counted-02' else report['runs']
        for receipt in receipts:result['observations'].append(read_cell(directory,report,receipt))
    assert len({r['configSha256'] for r in result['observations']})==1
    assert all(r['verdict']==('FAIL' if '@cell-end/' in r['caseId'] else 'PASS') for r in result['observations'])
    assert {r['browser'] for r in result['observations'] if r['cohort']=='s5-prep-07'}=={'chrome','firefox'}
    readings={
        'wasm_sdk_probe/src/probe_engine.cpp':['void handleInsertText(', 'gState.document->pClass->paste('],
        'wasm_sdk_probe/sdk/sdk-worker.js':['case "insertText":'],
        'libreoffice-26-8/desktop/source/lib/init.cxx':['static bool doc_paste(LibreOfficeKitDocument* pThis, const char* pMimeType, const char* pData, size_t nSize)'],
        'libreoffice-26-8/desktop/source/lib/lokclipboard.cxx':['LOKTransferable::LOKTransferable(const size_t', 'aContent <<= OUString(pInStreams[i], pInSizes[i], RTL_TEXTENCODING_UTF8);'],
        'libreoffice-26-8/sw/source/uibase/dochdl/swdtflvr.cxx':['!rSh.IsTableMode() && rSh.HasSelection()', 'sData.getLength() * sizeof( sal_Unicode )', 'aAOpt.SetCharSet( RTL_TEXTENCODING_UCS2 );'],
        'libreoffice-26-8/sw/source/filter/basflt/shellio.cxx':['void SwAsciiOptions::Reset()', 'nError = po->Read(*mxDoc, msBaseURL, *pPam, maFileName);', 'pPam = pPam->GetNext();'],
        'libreoffice-26-8/sw/source/filter/ascii/parasc.cxx':['m_aOption.ResetASCIIOpts();', "// Found control char, replace with '#'"]}
    for path,needles in readings.items():
        raw=(ROOT/path).read_bytes();text=raw.decode();anchors=[]
        for needle in needles:
            assert needle in text,(path,needle)
            anchors.append({'text':needle,'line':text[:text.index(needle)].count('\n')+1})
        result['sourceReadings'].append({'path':path,'sha256':sha(raw),'anchors':anchors})
    result['coreSourceHead']=subprocess.check_output(['git','-C',str(ROOT/'libreoffice-26-8'),'rev-parse','HEAD'],text=True).strip()
    result['sourceInference']='Table paste skips selected-content deletion. A UTF-16 stream is reused for multiple PaMs; ASCII options reset after each read. A later read using a single-byte charset could turn the NUL after x into #. This is consistent with the saves, not a runtime trace or a native-paste measurement.'
    with args.output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps([{'cohort':r['cohort'],'browser':r['browser'],'caseId':r['caseId'],'verdict':r['verdict'],
                       'tableParagraphs':r['final']['paragraphs'][8:12]} for r in result['observations']]))


if __name__=='__main__':main()
