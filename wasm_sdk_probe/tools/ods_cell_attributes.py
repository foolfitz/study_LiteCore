"""Independent table-cell text attributes from saved ODS XML, without Calc.

Reads explicit styles, named parents, row/column defaults and family defaults
per ODF 1.3 part 3 sections 16.2 and 19.619. It does not interpret rich-text
span formatting. Repeated rows/columns are addressed without expanding them.
https://docs.oasis-open.org/office/OpenDocument/v1.3/os/part3-schema/OpenDocument-v1.3-os-part3-schema.html
"""
from xml.etree import ElementTree as ET
import zipfile

NS={'t':'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    's':'urn:oasis:names:tc:opendocument:xmlns:style:1.0'}

def q(prefix,name):return '{'+NS[prefix]+'}'+name

def axis(table,kind):
    containers={q('t','table-'+kind+'s'),q('t','table-'+kind+'-group'),q('t','table-header-'+kind+'s')}
    for node in table:
        if node.tag==q('t','table-'+kind):yield node
        elif node.tag in containers:yield from axis(node,kind)

def indexed(nodes,index,repeat):
    start=0
    for node in nodes:
        count=int(node.get(q('t',repeat),'1'))
        if count<1:raise ValueError('invalid ODF repeat')
        if start<=index<start+count:return node
        start+=count
    return None

def effective_attributes(path,part,column,row):
    if any(not isinstance(x,int) or x<0 for x in (part,column,row)):raise ValueError('invalid cell address')
    with zipfile.ZipFile(path) as z:
        content=ET.fromstring(z.read('content.xml'))
        roots=([ET.fromstring(z.read('styles.xml'))] if 'styles.xml' in z.namelist() else [])+[content]
    tables=content.findall('.//'+q('t','table'))
    if part>=len(tables):raise ValueError('missing sheet')
    table=tables[part]
    tr=indexed(axis(table,'row'),row,'number-rows-repeated')
    if tr is None:raise ValueError('cell row is not serialized')
    col=indexed(axis(table,'column'),column,'number-columns-repeated')
    cell=indexed((n for n in tr if n.tag in {q('t','table-cell'),q('t','covered-table-cell')}),column,'number-columns-repeated')
    if cell is None:raise ValueError('cell column is not serialized')
    styles={};defaults={}
    for root in roots:
        for style in root.findall('.//'+q('s','style')):
            if style.get(q('s','family'))=='table-cell':styles[style.get(q('s','name'))]=style
        for style in root.findall('.//'+q('s','default-style')):
            if style.get(q('s','family'))=='table-cell':
                props=style.find(q('s','text-properties'))
                if props is not None:defaults.update(props.attrib)
    def chain(name,seen=()):
        if not name:return {}
        if name in seen:raise ValueError('cyclic cell style: '+name)
        if name not in styles:raise ValueError('missing cell style: '+name)
        style=styles[name];attrs=chain(style.get(q('s','parent-style-name')),(*seen,name))
        props=style.find(q('s','text-properties'))
        if props is not None:attrs.update(props.attrib)
        return attrs
    attrs=dict(defaults)
    for name in [col.get(q('t','default-cell-style-name')) if col is not None else None,
                 tr.get(q('t','default-cell-style-name')),cell.get(q('t','style-name'))]:
        attrs.update(chain(name))
    return attrs
