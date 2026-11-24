import sys
from zipfile import ZipFile
from xml.etree import ElementTree as ET
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(sys.argv[1]) as z:
    assert z.testzip() is None
    for name in z.namelist():
        if name.endswith(('.xml','.rels')): ET.fromstring(z.read(name))
    book=ET.fromstring(z.read('xl/workbook.xml'))
    assert [s.attrib['name'] for s in book.findall('s:sheets/s:sheet',ns)]==['Legacy','V4 AI Performance','V4 AI Prediction Details','V4 Suggested Performance','V4 Suggested Parlays','V4 Suggested Legs']
    def cell(sheet,ref):
        return ET.fromstring(z.read(f'xl/worksheets/sheet{sheet}.xml')).find(f".//s:c[@r='{ref}']",ns)
    assert cell(1,'A1').find('s:is/s:t',ns).text=='Original'
    assert float(cell(2,'E2').find('s:v',ns).text)==.75
    assert cell(3,'A2').find('s:is/s:t',ns).text=='A & B'
    assert 'No authentic' in cell(4,'A1').find('s:is/s:t',ns).text
    assert cell(6,'B2').find('s:v',ns).text=='1'
print('PASS: actual XLSX ZIP integrity, XML, six sheets, legacy data, numeric accuracy and linked leg')
