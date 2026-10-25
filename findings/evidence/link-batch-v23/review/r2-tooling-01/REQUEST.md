Adversarial review, English, no tools, max250words. Find concrete bugs in the new r2 bounded-cohort composition, not speculative broad concerns. Scope ruling: original candidate 24cells were18PASS+6NE (plainNONE negativeinput invalid). Corrected r2 has18direct smoke/proof/hang cells plus references to6 separately executed counted040 frame-html-js negatives (bothbrowsersN3), total24logical obligations. Must not invent new executions or accept duplicate copies. Remaining040 judge independently verifies exact pinnedframefixture/openbufferhash, actualwire search/range/COMPLEX setup, exact operationorder, kind3/controlentry, no terminal reply, SDK30000 TIMEOUT and actualcancel, recoverableerror, oldworkertermination/newworkerrestore+save. cases.verify_bindings verifies exact actualsources/fullmirroredJS and browser-fetched entryhashes. cases.fixtures derives fixedsourcefixture/population. identity verifies explicitr2 profile+ABI5+4actualartifact hashes against ownerpin. Do not weaken these predicates or require new productfeatures. Review supplied orchestration for concrete attribution/population problems. If none, say no concrete finding.

def corrected_references(paths, expected):
    """Rejudge six actual corrected040 negatives; references never create new runs."""
    import judge_v23_remaining as remaining
    import v23_remaining_cases as cases
    references=[]
    _, population=cases.fixtures()
    for path in paths:
        path=Path(path).resolve();report=json.loads(path.read_text())
        if report.get('profile')!=R2_PROFILE or report.get('identity')!=expected:
            raise ValueError('corrected040 reference is not bound to actual r2 identity')
        cases.verify_bindings(report,path.parent/'mirror')
        if report.get('population')!=population:raise ValueError('corrected040 input population drift')
        for name,digest in report['fixtures'].items():
            if cases.sha(path.parent/'mirror'/f'{name}.odt')!=digest:raise ValueError('corrected040 fixture drift')
        report_sha=hashlib.sha256(path.read_bytes()).hexdigest()
        for index,run in enumerate(report.get('runs',[])):
            page=run.get('page') or {}
            if run.get('arm')!='html-negative' or page.get('arm')!='html-negative':
                raise ValueError('only corrected frame-html-js observations may replace r2 logical js-thread obligations')
            verdict=remaining.judge(page,expected,report['fixtures'],R2_PROFILE)
            references.append(dict(browser=run.get('browser'),round=run.get('round'),arm='js-thread',
                source={'path':str(path),'sha256':report_sha,'runIndex':index,
                        'pageSha256':hashlib.sha256(json.dumps(page,sort_keys=True).encode()).hexdigest(),
                        'caseId':'frame-html-js'}, **verdict))
    return references


def summarize(results, references, profile):
    problems=[]
    if profile==R2_PROFILE:
        if any(r.get('arm')=='js-thread' for r in results):problems.append('generic r2 js-thread cell cannot count')
        keys=[(r.get('browser'),r.get('round')) for r in references]
        wanted={(b,n) for b in ('chrome','firefox') for n in range(1,4)}
        if len(keys)!=6 or set(keys)!=wanted:problems.append('missing/extra/duplicate corrected040 references')
        ids=[(r.get('source',{}).get('sha256'),r.get('source',{}).get('runIndex')) for r in references]
        pages=[r.get('source',{}).get('pageSha256') for r in references]
        if len(ids)!=len(set(ids)) or len(pages)!=len(set(pages)) or any(x is None for x in pages):
            problems.append('duplicate or unidentified corrected040 observation')
    elif references:problems.append('original identity does not use corrected r2 references')
    cells=results+references
    population={(b,n,a) for b in ('chrome','firefox') for n in range(1,4) for a in ARMS}
    actual=[(r.get('browser'),r.get('round'),r.get('arm')) for r in cells]
    complete=len(actual)==24 and len(set(actual))==24 and set(actual)==population and not problems
    verdict=NE if not complete or any(r['verdict']==NE for r in cells) else FAIL if any(r['verdict']==FAIL for r in cells) else PASS
    return {'verdict':verdict,'populationComplete':complete,'problems':problems,
            'directCells':len(results),'referencedCells':len(references),'results':cells,
            'scope':'24 logical bounded obligations; six r2 negatives reuse uniquely identified corrected040 observations',
            'notClosed':['W-D','S-init','040-W frame/destroy/engine-HTML','large fixtures/64KiB/long60',
                         'idle layout/tile timing','feature gates','host/K']}


def main():
    from v23_diagnostic_instruments import verify_bindings
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--profile',choices=PROFILES,default=PROFILE)
    parser.add_argument('--profile-dir',type=Path,required=True)
    parser.add_argument('--wasm-sha256',required=True)
    parser.add_argument('--corrected-040-report',type=Path,action='append',default=[])
    args=parser.parse_args();expected=identity(args.profile_dir,args.wasm_sha256,args.profile)
    report=json.loads(args.report.read_text())
    if report.get('profile')!=args.profile or report.get('identity')!=expected:raise ValueError('report candidate identity mismatch')
    verify_bindings(report,args.report.parent/'mirror')
    fixture=hashlib.sha256((args.report.parent/'mirror/fixture.odt').read_bytes()).hexdigest()
    if report.get('fixtureSha256')!=fixture:raise ValueError('actual fixture identity mismatch')
    results=[]
    for run in report.get('runs',[]):
        page=run.get('page') or {}
        if page.get('fixtureSha256')!=fixture:raise ValueError('browser fixture identity mismatch')
        if run.get('arm')!=page.get('arm'):raise ValueError('run/page arm mismatch')
        results.append(dict(browser=run.get('browser'),round=run.get('round'),arm=run.get('arm'),
                            **judge(page,expected,args.profile)))
    references=corrected_references(args.corrected_040_report,expected)
    result=summarize(results,references,args.profile)
    print(json.dumps(result,indent=2));return 0 if result['verdict']==PASS else 1

if __name__=='__main__':raise SystemExit(main())
