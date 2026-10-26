import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'research/experiment_registry.json'
data=json.loads(p.read_text(encoding='utf-8-sig'))
data['process_reporting']={'as_of':'2026-10-26','index':'reports/experiment_process_20261026/README.md','combined_report':'reports/experiment_process_20261026/FULL_REPORT.md','legacy_records':'reports/experiment_process_20261026/LEGACY_EXPERIMENTS.md','source_manifest':'reports/experiment_process_20261026/source_manifest.json','purpose':'기존 결과의 실행 과정 설명. 새로운 모델 검증 또는 실험 판정 변경이 아님.'}
for e in data['entries']:e['process_report']=f"reports/experiment_process_20261026/experiments/{e['id']}.md"
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
