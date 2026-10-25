import sys
from pathlib import Path
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ods_cell_attributes import effective_attributes

class EffectiveAttributes(unittest.TestCase):
    def fixture(self,cell='',row='',column='',style_extra=''):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        p=Path(directory.name)/'test.ods'
        ns='xmlns:t="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:s="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
        content=f'''<root {ns}><t:table><t:table-column-group><t:table-column t:number-columns-repeated="5" {column}/></t:table-column-group><t:table-header-rows><t:table-row t:number-rows-repeated="3" {row}><t:table-cell t:number-columns-repeated="5" {cell}/></t:table-row></t:table-header-rows></t:table></root>'''
        styles=f'''<root {ns}><s:default-style s:family="table-cell"><s:text-properties weight="normal" posture="none" underline="none"/></s:default-style><s:style s:name="parent" s:family="table-cell"><s:text-properties weight="bold"/></s:style><s:style s:name="column" s:family="table-cell" s:parent-style-name="parent"><s:text-properties posture="italic"/></s:style><s:style s:name="row" s:family="table-cell"><s:text-properties weight="normal"/></s:style><s:style s:name="cell" s:family="table-cell"><s:text-properties underline="solid"/></s:style>{style_extra}</root>'''
        with zipfile.ZipFile(p,'w') as z:z.writestr('content.xml',content);z.writestr('styles.xml',styles)
        return p
    def test_column_default_parent_and_repeated_axes(self):
        p=self.fixture(column='t:default-cell-style-name="column"')
        self.assertEqual(effective_attributes(p,0,4,2),{'weight':'bold','posture':'italic','underline':'none'})
    def test_row_and_cell_precedence_per_property(self):
        p=self.fixture(cell='t:style-name="cell"',row='t:default-cell-style-name="row"',column='t:default-cell-style-name="column"')
        self.assertEqual(effective_attributes(p,0,1,1),{'weight':'normal','posture':'italic','underline':'solid'})
    def test_family_default_and_unserialized_address(self):
        p=self.fixture();self.assertEqual(effective_attributes(p,0,0,0)['weight'],'normal')
        for address in [(1,0,0),(0,5,0),(0,0,3)]:
            with self.assertRaises(ValueError):effective_attributes(p,*address)
    def test_unknown_and_cyclic_styles_fail_instead_of_assuming_default(self):
        p=self.fixture(cell='t:style-name="missing"')
        with self.assertRaisesRegex(ValueError,'missing'):effective_attributes(p,0,0,0)
        p=self.fixture(cell='t:style-name="loop"',style_extra='<s:style s:name="loop" s:family="table-cell" s:parent-style-name="loop"/>')
        with self.assertRaisesRegex(ValueError,'cyclic'):effective_attributes(p,0,0,0)

if __name__=='__main__':unittest.main()
