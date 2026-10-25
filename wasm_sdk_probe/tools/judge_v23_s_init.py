#!/usr/bin/env python3
"""Read the finite 72-cell S-init comparison; retain accepted residuals as NE."""
import argparse
import base64
import hashlib
import io
import json
import re
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v23_s_init_cases import CASES, PROFILES, BROWSERS, ROUNDS, REGION, MARKER, PARAGRAPH_MARKER, expected_mutations, config_bytes

NS = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
      'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
      'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0'}
def q(prefix, name): return '{' + NS[prefix] + '}' + name
def digest(data): return hashlib.sha256(data).hexdigest()
def decode(value): return base64.b64decode(value, validate=True)
def wire_bytes(value):
    assert value['encoding'] == 'base64', 'wire binary encoding missing'
    data = decode(value['data'])
    assert len(data) == value['bytes'], 'wire byte length differs'
    return data


def semantic(data):
    """Resolve paragraph/text style inheritance, retaining language/hyphenation.

    Ignore ZIP metadata, generated style names and office metadata; retain actual
    paragraph order/text, inline structure, list depth and effective properties.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        content = ET.fromstring(archive.read('content.xml'))
        roots = [ET.fromstring(archive.read('styles.xml')), content]
    defaults, styles, list_styles = {}, {}, {}
    for root in roots:
        for item in root.iter(q('text', 'list-style')):
            list_styles[item.get(q('style', 'name'))] = item
        for item in root.iter(q('style', 'default-style')):
            defaults[item.get(q('style', 'family'))] = item
        for item in root.iter(q('style', 'style')):
            styles[item.get(q('style', 'name'))] = item
    def own(item):
        if item is None: return {}
        return {child.tag + '/' + key: value for child in item for key, value in child.attrib.items()
                if not key.endswith('}rsid') and not key.endswith('}paragraph-rsid')}
    def properties(name, family, seen=()):
        assert name not in seen, 'cyclic saved style inheritance'
        item = styles.get(name)
        # Writer's SvxHyphenZoneItem::CreateDefault is false (paraitem.cxx).
        # Export may omit an explicit false; normalize that effective default.
        out = {q('style', 'text-properties') + '/' + q('fo', 'hyphenate'): 'false'} if family == 'paragraph' else {}
        if family == 'paragraph':
            # SvxColorItem defaults to opaque COL_BLACK; CharTransparence is
            # exported as 100-transparency. A second Writer save may make this
            # effective default explicit. Nondefault opacity still overrides it.
            out[q('style', 'text-properties') + '/{urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0}opacity'] = '100%'
        out.update(own(defaults.get(family)))
        if item is not None:
            parent = item.get(q('style', 'parent-style-name'))
            if parent: out.update(properties(parent, family, seen + (name,)))
            out.update(own(item))
        return out
    def text(node):
        if node.tag == q('text', 's'): return ' ' * int(node.get(q('text', 'c'), '1'))
        if node.tag == q('text', 'tab'): return '\t'
        if node.tag == q('text', 'line-break'): return '\n'
        return (node.text or '') + ''.join(text(ch) + (ch.tail or '') for ch in node)
    def inline(node):
        attrs = {key: value for key, value in node.attrib.items() if key != q('text', 'style-name')}
        style = properties(node.get(q('text', 'style-name')), 'text') if node.tag == q('text', 'span') else {}
        return {'tag': node.tag, 'attrs': attrs, 'text': node.text or '', 'tail': node.tail or '',
                'properties': style, 'children': [inline(ch) for ch in node]}
    paragraphs = []
    def list_definition(node):
        return {'tag': node.tag, 'attrs': {k:v for k,v in node.attrib.items() if k != q('style','name')},
                'children': [list_definition(child) for child in node]}
    def walk(node, depth=0, numbering=()):
        if node.tag == q('text','list'):
            name = node.get(q('text','style-name'))
            numbering = numbering + ((list_definition(list_styles[name]) if name in list_styles else None),)

        if node.tag in (q('text', 'p'), q('text', 'h')):
            paragraphs.append({'tag': node.tag, 'text': text(node), 'listDepth': depth, 'numbering': list(numbering),
                'properties': properties(node.get(q('text', 'style-name')), 'paragraph'),
                'children': [inline(ch) for ch in node]})
            return
        for child in node: walk(child, depth + (node.tag == q('text', 'list')), numbering)
    walk(content)
    assert paragraphs, 'saved ODT has no paragraphs'
    return paragraphs


def inspect_cell(page, config):
    profile, case_id = page['profile'], page['caseId']
    assert profile in PROFILES and case_id in CASES, 'wrong profile/case'
    assert page.get('complete') and not page.get('fatal'), 'incomplete/failed page'
    assert page['plan'] == CASES[case_id], 'case inputs differ'
    expected = config['profiles'][profile]
    assert page['artifacts'] == expected['artifacts'], 'actual served artifact/resource bytes differ'
    assert page['manifest']['profile'] == profile and page['manifest']['coreCommit'] == expected['coreCommit'], 'profile/core binding differs'
    assert page['servedSources'] == config['servedSources'], 'actual fetched instrument source bytes differ'
    assert page['configSha256'] == digest(config_bytes(config)), 'actual served config bytes differ'
    assert page['events'], 'no actual callback/event observations'
    assert page['steps'] and all(s.get('ok') is True for s in page['steps']), 'failed/missing public step'
    requests = page['requests']; responses = page['responses']
    keys = [(r['generation'], r['message']['requestId']) for r in requests]
    reply_keys = [(r['generation'], r['message']['requestId']) for r in responses]
    assert len(keys) == len(set(keys)) and len(reply_keys) == len(set(reply_keys)), 'duplicate request/response'
    assert set(keys) == set(reply_keys), 'missing or unmatched terminal response'
    replies = {key: r['message'] for key, r in zip(reply_keys, responses)}
    assert all(r.get('ok') is True for r in replies.values()), 'public request failed'
    def operations(name, generation=None):
        return [r for r in requests if r['message']['operation'] == name and
                (generation is None or r['generation'] == generation)]
    def response(request): return replies[(request['generation'], request['message']['requestId'])]['result']
    assert not operations('v23Diagnostic'), 'S-init must use public routes only'
    workers = {w['generation']: w for w in page['workers']}
    assert len(workers) == len(page['workers']) and all(w['terminatedAt'] is not None for w in workers.values()), 'owned worker cleanup missing'
    for gen, worker in workers.items():
        assert urlparse(worker['url']).path.endswith('/profiles/' + profile + '/sdk-worker.js'), 'actual worker URL uses another profile'
        initializations = operations('init', gen)
        assert len(initializations) == 1, 'actual worker init missing/nonunique'
        initialized = response(initializations[0])
        assert initialized['profile'] == profile and initialized['coreCommit'] == expected['coreCommit'], 'actual initialized worker/core differs'

    assert [o['fixtureName'] for o in page['observations']] == CASES[case_id]['fixtures'], 'fixture variants missing/different'
    expected_generations = {o['openGeneration'] for o in page['observations']}
    if case_id == 'direct-load-reopen': expected_generations.update(o['reopenGeneration'] for o in page['observations'])
    assert expected_generations == set(workers) == {r['generation'] for r in requests}, 'unplanned worker generation'
    normalized = []
    for obs in page['observations']:
        fixture, gen = obs['fixtureName'], obs['openGeneration']
        assert obs['fixtureSha256'] == config['fixtures'][fixture], 'fixture identity differs'
        opens = operations('open', gen)
        assert len(opens) == 1, 'no unique actual open'
        assert opens[0]['message']['payload']['name'] == fixture, 'loader name differs'
        assert digest(wire_bytes(opens[0]['message']['payload']['buffer'])) == config['fixtures'][fixture], 'actual opened fixture bytes differ'
        saved = decode(obs['saved']['base64'])
        assert digest(saved) == obs['saved']['sha256'], 'saved byte hash differs'
        saves = operations('save', gen)
        # Session may checkpoint before a public mutation; bind the final save.
        assert saves and wire_bytes(response(saves[-1])['buffer']) == saved, 'saved bytes not from actual terminal response'
        shape = semantic(saved)
        item = {'fixture': fixture, 'shape': shape}
        observers = {'init', 'open', 'save', 'editorGetStateV2', 'paint', 'pageRectangles'}
        mutations = [(r['message']['operation'], r['message']['payload'].get(
            'text' if r['message']['operation'] == 'insertText' else 'action'))
            for r in requests if r['generation'] == gen and r['message']['operation'] not in observers]
        assert mutations == expected_mutations(case_id), 'unplanned/missing public mutation sequence'
        inserts = operations('insertText', gen)
        if 'input' in CASES[case_id]:
            assert len(inserts) == 1 and inserts[0]['message']['payload']['text'] == CASES[case_id]['input'], 'exact public input not observed'
            method = response(inserts[0]).get('method')
            assert method in ('paste', 'postKeyEvent'), 'actual insertion method missing'
            item['method'] = method
            if case_id.startswith('input-'):
                before_revision = response(opens[0]).get('revision')
                after_revision = response(inserts[0]).get('revision')
                assert type(before_revision) is int and type(after_revision) is int and after_revision > before_revision, 'insert response did not advance actual revision'
                baseline = semantic(wire_bytes(opens[0]['message']['payload']['buffer']))
                substantive_text = any(p['text'].strip() for p in shape)
                new_list = case_id == 'input-number' and any(p['listDepth'] > 0 for p in shape) and not any(p['listDepth'] > 0 for p in baseline)
                assert shape != baseline and (substantive_text or new_list), 'input has no substantive saved insertion witness'

        else: assert not inserts, 'linguistic fixture was edited'
        if case_id == 'direct-load-reopen':
            newgen = obs['reopenGeneration']
            assert newgen != gen and gen in workers and newgen in workers, 'fresh worker restoration missing'
            assert workers[gen]['terminatedAt'] <= workers[newgen]['createdAt'], 'original worker not terminated before fresh worker'
            assert all(r['message']['operation'] in observers for r in requests if r['generation'] == newgen), 'unplanned restoration mutation'
            reopens = operations('open', newgen)
            assert len(reopens) == 1 and reopens[0]['message']['payload']['name'] == 'exact-saved-reopen.odt', 'missing exact saved reopen'
            assert wire_bytes(reopens[0]['message']['payload']['buffer']) == saved, 'reopen did not use exact saved bytes'
            assert obs['reopenInputSha256'] == digest(saved), 'reopen hash differs'
            reopened = decode(obs['reopened']['base64'])
            assert digest(reopened) == obs['reopened']['sha256'], 'reopened save hash differs'
            resaves = operations('save', newgen)
            assert resaves and wire_bytes(response(resaves[-1])['buffer']) == reopened, 'missing restoration save response'
            assert semantic(reopened) == shape and MARKER in ''.join(p['text'] for p in shape), 'roundtrip marker/structure changed'
            item['reopenedShape'] = semantic(reopened)
        if case_id == 'paragraph-break':
            setup = obs['paragraphSetup']
            placements = operations('editorPlaceCaretV2', gen)
            assert len(placements) == 1, 'missing/nonunique paired public placement'
            placed = placements[0]; place_id = placed['message']['requestId']
            insert_id = inserts[0]['message']['requestId']
            states = operations('editorGetStateV2', gen)
            initial = [s for s in states if s['message']['requestId'] < place_id]
            after = [s for s in states if place_id < s['message']['requestId'] < insert_id]
            assert initial and after and place_id < insert_id, 'placement must precede marker with fresh state witness'
            initial_state, placed_state = response(initial[-1]), response(after[0])
            assert setup['initialState'] == initial_state and setup['afterPlacementState'] == placed_state, 'setup state not bound to actual responses'
            caret = initial_state['caret']
            assert initial_state['selectionType'] == 'none', 'initial fixture caret is not empty selection'
            point = {'xTwips': caret['x'], 'yTwips': caret['y'] + caret['height'] // 2}
            assert setup['point'] == point and all(placed['message']['payload'].get(k) == v for k,v in point.items()), 'placement point not from actual initial caret'
            assert setup['placement'] == response(placed), 'placement result not bound to wire'
            assert placed_state['selection']['observed'] is True and placed_state['selection']['collapsed'] is True, 'public placement did not establish collapsed observation'
            actions = operations('editorActionV2', gen)
            assert len(actions) == 1, 'nonunique InsertPara'
            post = [s for s in states if insert_id < s['message']['requestId'] < actions[0]['message']['requestId']]
            assert post and setup['postMarkerState'] == response(post[-1]), 'fresh post-marker state missing'
            assert setup['postMarkerState']['selection']['observed'] is True and setup['postMarkerState']['selection']['collapsed'] is True, 'post-marker precondition absent'

            assert any(a['message']['payload'].get('action') == 'insert-paragraph-break' for a in actions), 'public InsertPara absent'
            assert [p['text'] for p in shape] == [PARAGRAPH_MARKER, ''], 'InsertPara paragraph order/structure differs'
        if case_id == 'linguistic-layout':
            render, geometry = obs['render'], obs['geometry']
            assert render['region'] == REGION, 'requested layout region differs'
            pixels = decode(render['rgbaBase64'])
            assert (render['width'], render['height']) == (600, 800) and len(pixels) == 600*800*4, 'pixel shape differs'
            assert digest(pixels) == render['rgbaSha256'], 'pixel hash differs'
            paints = operations('paint', gen)
            matching = [r for r in paints if all(r['message']['payload'].get(k) == v for k,v in REGION.items())]
            assert matching and wire_bytes(response(matching[-1])['pixels']) == pixels, 'actual rendered bytes/request absent'
            layouts = operations('pageRectangles', gen)
            assert layouts, 'page geometry request absent'
            raw = response(layouts[-1])
            assert geometry['parts'] == raw['parts'] and geometry['widthTwips'] == raw['documentWidthTwips'] and geometry['heightTwips'] == raw['documentHeightTwips'], 'geometry not bound to response'
            rectangles = [[int(v.strip()) for v in row.split(',')] for row in raw['rectangles'].split(';') if row.strip()]
            assert geometry['rectangles'] == [dict(zip(('x','y','width','height'), rect)) for rect in rectangles], 'page rectangles differ from wire'
            props = shape[0]['properties']
            expected_hyph = 'true' if fixture == 'hyphenation-on.odt' else 'false'
            assert any(k.endswith('/'+q('fo','hyphenate')) and v == expected_hyph for k,v in props.items()), 'saved hyphenation property absent/different'
            for key,value in (('language','en'),('country','US')):
                assert any(k.endswith('/'+q('fo',key)) and v == value for k,v in props.items()), 'saved language property absent/different'
            item.update(geometry={k: geometry[k] for k in ('parts','rectangles','widthTwips','heightTwips')},
                        rgbaSha256=digest(pixels), region=render['region'])
        normalized.append(item)
    return normalized


RESIDUALS = {
    'unprimedParagraphActionAsymmetry': 'KNOWN: prep03 v22 refused and r2 succeeded without setup; the comparison covers the explicitly paired public precondition',
    'serviceDictionaryAvailability': 'NOT_ESTABLISHED: no service inventory; equal renders do not establish dictionaries',
    'effectiveSpellingAutocorrectionConfiguration': 'NOT_ESTABLISHED: not exposed by current contract',
    'naturalKeyFallbackCoverage': 'NOT_ESTABLISHED unless the wire actually reports postKeyEvent',
    'longLivedAutoRecoveryEffects': 'NOT_ESTABLISHED: omitted disableRecovery side effect not measured',
}

def judge(cells, config):
    wanted = {(case, profile, browser, n) for case in CASES for profile in PROFILES for browser in BROWSERS for n in ROUNDS}
    keys = [(c['caseId'], c['profile'], c['browser'], c['round']) for c in cells]
    if len(keys) != len(set(keys)) or set(keys) != wanted:
        return {'verdict': 'NOT_ESTABLISHED', 'problems': ['missing/duplicate/extra Cartesian cells'], 'residuals': RESIDUALS}
    normalized, failures, page_hashes = {}, [], {}
    for key, cell in zip(keys, cells):
        try:
            assert not cell.get('fatal'), 'runner failed'
            assert (cell['page']['caseId'], cell['page']['profile']) == key[:2], 'page mislabeled'
            ua = cell['page'].get('userAgent', '')
            actual_family = 'firefox' if re.search(r'Firefox/\d', ua) else 'chrome' if re.search(r'(?:Headless)?Chrome/\d', ua) else None
            assert actual_family == cell['browser'], 'actual user-agent family differs from browser label'
            page_hash = digest(json.dumps(cell['page'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
            assert page_hash not in page_hashes, 'actual page observation reused across cells'
            page_hashes[page_hash] = key

            normalized[key] = inspect_cell(cell['page'], config)
        except (AssertionError, KeyError, ValueError, TypeError, ET.ParseError, zipfile.BadZipFile) as error:
            failures.append({'cell': key, 'reason': str(error)})
    for case in CASES:
        for browser in BROWSERS:
            refs = [normalized.get((case, PROFILES[0], browser, n)) for n in ROUNDS]
            if all(ref is not None for ref in refs) and not all(ref == refs[0] for ref in refs):
                failures.append({'case': case, 'browser': browser, 'reason': 'v22 reference unstable'})
            for n in ROUNDS:
                baseline = normalized.get((case, PROFILES[0], browser, n))
                candidate = normalized.get((case, PROFILES[1], browser, n))
                if baseline is not None and candidate is not None and baseline != candidate:
                    failures.append({'case': case, 'browser': browser, 'round': n, 'reason': 'observed public-route outcome differs'})
    linguistic_controls = []
    for key, items in normalized.items():
        if key[0] == 'linguistic-layout' and len(items) == 2:
            linguistic_controls.append({'profile': key[1], 'browser': key[2], 'round': key[3],
                'enabledDisabledPixelsDiffer': items[0]['rgbaSha256'] != items[1]['rgbaSha256'],
                'interpretation': 'bounded setting-control observation, not a service/dictionary inventory'})
    methods = sorted({obs['method'] for items in normalized.values() for obs in items if 'method' in obs})
    return {'verdict': 'FAIL' if failures else 'PASS', 'scope': 'bounded S-init product-route comparison',
            'cells': len(cells), 'failures': failures, 'observedInsertionMethods': methods,
            'linguisticControls': linguistic_controls,
            'residuals': dict(RESIDUALS, naturalKeyFallbackCoverage=
                'OBSERVED in bounded cases; not exhaustive fallback capability' if 'postKeyEvent' in methods else RESIDUALS['naturalKeyFallbackCoverage'])}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('report', type=Path)
    p.add_argument('--v22-wasm-sha256', required=True); p.add_argument('--candidate-wasm-sha256', required=True)
    a=p.parse_args()
    report=json.loads(a.report.read_text()); cells=[]
    from v23_s_init_cases import profile_identity, fixture_identity, instrument_identity, served_sources, verify_mirror
    config=report['config']
    assert report.get('counted') is True, 'preparation-only evidence is not a counted population'
    pins = dict(zip(PROFILES, (a.v22_wasm_sha256, a.candidate_wasm_sha256)))
    assert config['servedSources'] == served_sources(), 'executed source graph differs'
    assert report['mirrorBindings'] == verify_mirror(a.report.parent / 'mirror', config), 'mirror bindings differ'
    assert config['cases']==CASES and config['region']==REGION, 'recorded case table/region differs'
    assert config['fixtures']==fixture_identity(), 'actual pinned fixtures differ'
    assert config['instrumentSha256']==instrument_identity(), 'actual instrument sources differ'
    for profile in PROFILES:
        assert config['profiles'][profile]==profile_identity(profile, pins[profile]), 'actual frozen profile/resource identity differs'
    assert report['postIdentity']=={k:config[k] for k in ('profiles','fixtures','instrumentSha256')}, 'post-cohort identity absent/different'
    for record in report['runs']:
        path=a.report.parent/record['path']; data=path.read_bytes()
        assert digest(data)==record['sha256'], 'cell artifact changed'
        cells.append(json.loads(data))
    result=judge(cells,report['config']);print(json.dumps(result,indent=2))
    return 0 if result['verdict']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
