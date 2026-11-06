"""Document import regression checks (run directly with Python)."""
import importlib.util, tempfile, zipfile, subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=r/'system/apps/shell/scripts/typing_import.py'
s=importlib.util.spec_from_file_location('typing_import',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
    d=Path(d)
    p=d/'text.txt'; p.write_text('hello\n world'); assert m.extract(str(p))=='hello world'
    p=d/'web.html'; p.write_text('<p>Hello</p><script>secret</script><p>world</p>'); assert m.extract(str(p))=='Hello world'
    p=d/'test.docx'
    with zipfile.ZipFile(p,'w') as z: z.writestr('word/document.xml','<document><p><r><t>Hello</t></r></p><p><r><t>world</t></r></p></document>')
    assert m.extract(str(p))=='Hello world'
    p=d/'empty.txt'; p.write_text(' ')
    try: m.extract(str(p)); raise AssertionError('empty accepted')
    except ValueError: pass
    # Minimal real PDF, with xref offsets calculated from its actual bytes.
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>', b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    stream=b'BT /F1 12 Tf 72 720 Td (Hello typing) Tj ET'
    objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    data=b'%PDF-1.4\n'; offsets=[0]
    for i,obj in enumerate(objects,1): offsets.append(len(data)); data+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(data); data+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{n:010} 00000 n \n'.encode() for n in offsets[1:])+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    p=d/'test.pdf'; p.write_bytes(data); assert m.extract(str(p))=='Hello typing'
print('Text, HTML sanitization, DOCX paragraphs, empty rejection and real PDF extraction passed')
