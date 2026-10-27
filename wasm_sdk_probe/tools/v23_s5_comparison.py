"""Shared S5 byte comparators; native references retain ruling 2's exact guards."""
import difflib
import io
import re
import zipfile
from judge_v23_feature_pre_red import NotEstablished,need
from odt_paragraphs import paragraph_texts_from_xml
from run_merge_wasm_shakedown import reduce_content


def odt_content(raw):
    try:return zipfile.ZipFile(io.BytesIO(raw)).read('content.xml')
    except (zipfile.BadZipFile,KeyError) as error:raise NotEstablished('saved ODT unreadable: '+str(error))


def strip_ffd(content):
    """Ruling 2: remove only the single nonempty environment-specific font-face declaration."""
    pattern=rb'<office:font-face-decls>(.*?)</office:font-face-decls>'
    found=re.findall(pattern,content,re.S)
    need(len(found)==1,'font-face-decls not uniquely present')
    need(found[0].strip()!=b'','font-face-decls empty')
    rest=re.sub(pattern,b'',content,count=1,flags=re.S)
    need(b'<office:body>' in rest,'office:body absent after removing font-face-decls')
    return rest


def s5_reduced(raw,native):
    content=reduce_content(odt_content(raw))
    return strip_ffd(content) if native else content


def s5_compare(family,candidate,reference,native):
    if family=='type':
        return paragraph_texts_from_xml(odt_content(candidate))==paragraph_texts_from_xml(odt_content(reference))
    return s5_reduced(candidate,native)==s5_reduced(reference,native)


def validate_settled_pair(before,after,queued_before):
    """Own-before controls, not a transitive substitute for the browser's own-before check."""
    need(s5_compare('delete',queued_before,before,True),'settled native before differs from queued native before')
    if s5_reduced(before,True)==s5_reduced(after,True):
        need(odt_content(before)==odt_content(after),'reduction collapses settled native edit')


def reduced_difference(candidate,reference,native):
    a=s5_reduced(candidate,native).decode().replace('><','>\n<').splitlines()
    b=s5_reduced(reference,native).decode().replace('><','>\n<').splitlines()
    return list(difflib.unified_diff(a,b,fromfile='candidate',tofile='reference',n=1,lineterm=''))
