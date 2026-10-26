import json
import re
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
records=[]
for group in ['detection','purification','mechanism','literature','pending']:
    for p in sorted((ROOT/'pr_reports'/group).glob('*.md')):
        raw=p.read_text(encoding='utf-8-sig')
        sections={m.group(1).strip():m.group(2).strip() for m in re.finditer(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',raw,re.M|re.S)}
        result=sections.get('결과','')
        if group=='detection' and p.stem=='D26':
            result='2026년 10월 19일 16시 58분 완료 70요청에서 공격 9/10, 대조 경보 2/60이었다. 같은 임계값 0.006에서 유지 분기만 쓰면 대조 경보 11/60, 두 분기를 함께 쓰면 2/60이었다. 후속 감사의 같은 요청 84건 비교는 공격 11/12와 대조 경보 3/72로 별도 보존됐다. 70건과 84건을 같은 시점의 결과로 합치지 않는다.'
        r={'source':p.relative_to(ROOT).as_posix(),'group':group,'old_id':p.stem,'title':raw.splitlines()[0].removeprefix('# '), 'hypothesis':sections.get('가설 한 줄',''),'method':sections.get('실험 한 줄',''),'result':result,'evidence':sections.get('검증과 근거','')}
        assert r['hypothesis'] and r['method'] and r['result'],str(p)
        records.append(r)
(OUT/'legacy_source_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
for r in records:
    if (r['group']=='detection' and int(re.sub(r'\D','',r['old_id']) or 0)<=25) or r['old_id'] in {'P10','P11'}:
        continue
    if '--quiet' not in sys.argv: print(json.dumps(r,ensure_ascii=False))
print('TOTAL',len(records))
