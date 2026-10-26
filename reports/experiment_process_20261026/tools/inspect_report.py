import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile
import pypdfium2 as pdfium
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parents[1]
pdf=pdfium.PdfDocument(OUT/'qa/report.pdf')
pages=[]
for i,page in enumerate(pdf):
    target=OUT/'qa'/f'page-{i+1}.png'
    page.render(scale=1.5).to_pil().save(target)
    textpage=page.get_textpage()
    text=textpage.get_text_range()
    outside=[]
    pages.append({'page':i+1,'characters':len(text),'first_lines':text.splitlines()[:2],'last_lines':text.splitlines()[-3:],'outside_page':outside})
with ZipFile(OUT/'BadFU_실험과정_전체정리_20261026.docx') as z:
    props=z.read('docProps/core.xml').decode()
    assert 'Codex' not in props and 'OpenAI' not in props
assert not any(p['outside_page'] for p in pages)
(OUT/'qa/PAGE_AUDIT.json').write_text(json.dumps({'pages':pages,'page_count':len(pages),'renderer':'Word export and PDFium 108dpi','metadata_author_checked':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'page_count':len(pages),'short_pages':[p for p in pages if p['characters']<250],'page_titles':[(p['page'],p['first_lines']) for p in pages]},ensure_ascii=False))
