"""Build research navigation from the registry; never opens tensors or changes evidence."""
import argparse, hashlib, json, re, stat, subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'research'
REGISTRY = RESEARCH / 'experiment_registry.json'
TRACKED = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0'))

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(rel, label=None):
    assert (ROOT/rel).exists(), rel
    if rel not in TRACKED and not any(p.startswith(rel.rstrip('/') + '/') for p in TRACKED):
        return f'`{label or rel}` (로컬 보관)'
    href=rel.removeprefix('research/') if rel.startswith('research/') else '../'+rel
    return f'[{label or rel}]({href})'
def card(e): return f"[{e['id']} · {e['title']}](EXPERIMENT_CARDS.md#{e['id'].lower()})"
def reparse(p): return bool(p.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
def write(p,s,check):
    if check:
        assert p.exists() and p.read_text(encoding='utf-8')==s, f'Stale generated index: {p}'
    else: p.write_text(s,encoding='utf-8')

def collect_inventory(entries):
    # Directory navigation only; no recursive traversal into runtime/data/checkpoint trees.
    roots=['research','research_20261018','research_20261019','research_audit_20261019',
           'review_BadFU_defend/experiments','pr_reports']
    out=[]
    for base in roots:
        parent=ROOT/base
        if not parent.exists(): continue
        for p in sorted(parent.iterdir(),key=lambda p:p.name.casefold()):
            if not p.is_dir() or p.name in {'index_tools','__pycache__','.git'} or reparse(p): continue
            rel=p.relative_to(ROOT).as_posix()
            related=[e['id'] for e in entries if any(f==rel or f.startswith(rel+'/') or rel.startswith(f+'/') for f in e['folders'])]
            docs=[q.relative_to(ROOT).as_posix() for q in sorted(p.iterdir(),key=lambda q:q.name.casefold())
                  if q.is_file() and q.suffix.lower() in {'.md','.txt','.json'}
                  and re.search(r'README|REPORT|RESULT|SUMMARY|PROTOCOL|DECISION|STATUS|COMPLETE|AUDIT|EVIDENCE|INDEX|PROOF|COUNTEREXAMPLE',q.name,re.I)]
            out.append(dict(path=rel,related_cards=related,top_level_documents=docs,
                review='대표 기록 재검토·카드 연결' if related else '폴더 색인만·내용 판정 미재검토'))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
    data=load(REGISTRY);entries=data['entries'];ids=[e['id'] for e in entries];assert len(ids)==len(set(ids))
    for e in entries:
        assert '\n' not in e['hypothesis'] and e['hypothesis'].strip()
        for k in ['conditions','controls','result','non_iid_lesson','do_not_repeat','revisit_condition']: assert e[k]
        for rel in e['sources']+e['folders']: assert (ROOT/rel).exists(), (e['id'],rel)
        if e.get('process_report'): assert (ROOT/e['process_report']).exists(), (e['id'],e['process_report'])
    sources={s:digest(ROOT/s) for e in entries for s in e['sources']}
    inventory=collect_inventory(entries)
    covered=sum(bool(v['related_cards']) for v in inventory)
    groups=list(dict.fromkeys(e['group'] for e in entries))

    main_text='''# 연구 실험 인덱스 — 제안·해석·실행 전에 먼저 읽기

**핵심 제약: 단순 반응량으로는 큰 정상 non-IID 참여자의 탈퇴와 공격을 구별하지 못했다.** 반응이 크다, 전후에 많이 변한다, 한 클래스로 쏠린다, 비용이 줄었다는 관측만으로 공격이라고 판단하지 않는다. **실제 트리거를 모르는 특정 패턴 탐색과 트리거 종류에 의존하지 않는 탐지는 다르다.**

2026-10-23 정리. 이 문서는 현재 해석의 입구다. 원 보고서·수치·실패 기록·체크포인트 경로는 보존했다. 옛 문서의 ‘현재 후보’, ‘다음 실험’, ‘진행 중’은 작성 당시 기록이며 자동 재개 지시가 아니다.

실험 과정을 읽으려면 [분야별 실험 목록](../experiments/README.md)에서 시작한다. 각 실험 폴더에 시작 이유·모델과 자료·실행 순서·결과·판단과 원 근거를 연결했다. 아래는 해석과 새 실험 검토를 위한 인덱스다.

## 매번 읽는 순서

1. **이 인덱스의 핵심 반례와 금지 사항**을 먼저 읽는다.
2. 제안하려는 방법과 관련된 **[실험 카드](EXPERIMENT_CARDS.md)**를 읽고, 카드에 연결된 **원 보고서의 조건·결과·정정**을 확인한다. 키워드만 보고 새 방법이라고 제안하지 않는다.
3. 모델을 사용할 때만 추가로 [궤적 README](00_trajectories/README.md)와 [catalog.json](00_trajectories/catalog.json)을 읽고 명시적 case ID·허용 용도로 선택한다.
4. [실험 원칙](EXPERIMENT_RULES.md)을 따른다. 새 제안에는 **관련 기존 카드 ID / 무엇이 새 관측인가 / 기존 non-IID 반례를 왜 구별할 수 있나 / 구별 못하면 중단할 기준**을 적는다. 근거가 없으면 미검증·보류다.

## 먼저 확인할 핵심 반례

| 이미 해본 것 | 실제 관측 | 남겨야 할 판단 |
|---|---|---|
| [D08 같은 잔류 참여자·능동 개입·정상 참조 보정](EXPERIMENT_CARDS.md#d08) | 공격0.75848, 큰 정상 탈퇴0.75525/0.76188 | 공격이 정상 두 값 사이. 협조·개입을 추가해도 반응량은 악성 표지가 아님 |
| [D06 정상 과제 망각](EXPERIMENT_CARDS.md#d06) | 공격 누적CE27.291, 큰 정상 탈퇴67.143 | 정상 기여 상실의 반응이 더 큼 |
| [D02 영향력과 정상 참조](EXPERIMENT_CARDS.md#d02) | 공격1.9765, 정상 주요 클래스 삭제2.0677 | 참조를 뺐다고 non-IID가 제거되지 않음 |
| [D05 특징 공간·출력 쏠림](EXPERIMENT_CARDS.md#d05) | 대표 공격12.983, 이전 정상14.570 | 잠재 공간으로 바꾸는 것만으로 해결되지 않음 |
| [D11 이미지별 변형 비용](EXPERIMENT_CARDS.md#d11) | 진단 공격11.30, 정상27.49; 최소 비용이 새 오류를 버리는 수학 예 | 경계·마진 요약도 공격 특이성을 보장하지 않음; FUBA 재현 한계 별도 |
| [D15 전후 공동 탐색+정상 협조자](EXPERIMENT_CARDS.md#d15) | 추가 학습 시드의 공개 오류 공격7.00%, 큰 정상8.00% | 정상 자료 추가 확인도 자동 해결책이 아님 |

숫자는 서로 다른 실험의 원문 단위·평가기록이다. 행 사이의 크기를 비교하지 않는다. 재학습·근사FU·진단 복사본, 독립 FL 시드·탐색 초기화, 정상 요청·깨끗한 모델을 각각 구분한다.

## 반복하지 않을 제안

- FC/Conv norm·cosine·CKA·RMS·민감도·drift 등 **단순 변화량을 이름만 바꿔 주력으로 재제안하지 않는다.** [D16 철회 기록](EXPERIMENT_CARDS.md#d16)
- ‘전후 차분’, ‘정상 참조’, ‘클래스 균등’, ‘협조 참여자’, ‘능동 함정’을 붙였다는 이유로 정상 큰 탈퇴를 제거했다고 주장하지 않는다. D02/D06/D07/D08/D15를 읽는다.
- ‘특징 공간’, ‘생성기’, ‘시맨틱 변환’, ‘최소 경계 거리’가 아직 안 해본 근본 해결책인 것처럼 소개하지 않는다. D05/D09/D11/D13/D14를 읽는다.
- **직전 신뢰 기준 모델 제안도 미검증·보류다.** 추가 정보의 획득 가능성과 정상 탈퇴에서도 같은 반례가 나오는지를 설명하지 못하면 새 실행의 기본 방향으로 삼지 않는다. [N01](EXPERIMENT_CARDS.md#n01)
- 모든 반응 기반 방법의 수학적 불가능성을 증명했다고 확대하지 않는다. 기각한 구체적 지표·조건과 미검증 영역을 구분한다.

## 최근 결과의 정확한 위치

**[D17 직접400/800·노출400](EXPERIMENT_CARDS.md#d17):** 직접400에서 두 BadFU 공격56.22/56.00%, 정상 대조14.78/5.22/7.33%의 제한된 분리를 관측했다. 유리한 관측은 지우지 않는다. 하지만 강한 후보는 마스크였고, 실제 학습2시드·같은 분할·큰 정상 탈퇴1건·FUBA 제외다. **트리거 종류에 독립적인 non-IID 탐지의 주력 주장은 미확보다.** 노출400은 공격2.67/69.22%로 갈려 안정적 개선 가설이 기각됐다. 이전 D15보다 나아진 이유를 횟수 하나로 확정하지 않는다.

**[R02 FUBA](EXPERIMENT_CARDS.md#r02):** 현재 승인된 잠복 활성화 전후쌍이 없다. 미완료·억제 실패·정상 모델로 생성기 전이가 큰 진단 조건은 유효한 잠복 공격 대조를 대체하지 못한다. FUBA와 별도 FedUBA 명칭을 섞지 않는다.

## 연구 갈래

```mermaid
flowchart TD
    A["연구 인덱스 먼저 읽기"] --> R["재현·모델 출처 R01–R02"]
    A --> D["1단계 탐지: 정상 non-IID와 구별"]
    D --> H["이력·영향력 D01–D02"]
    D --> M["반응·내부 통계 D03–D06·D16"]
    D --> I["능동 개입·함정 D07–D08"]
    D --> C["경계·비용 D09–D11"]
    D --> W["기능 반례 탐색 D12–D15·D17"]
    A --> T["원인·수학 T01: 서버 증거와 구분"]
    A --> P["정화 P01–P03: 탐지 성공과 구분"]
    A --> N["미검증 제안 N01: 자동 실행 금지"]
```

## 카드 목록

'''
    for g in groups:
        main_text+=f'### {g}\n\n| 실험 카드 | 현재 판정 |\n|---|---|\n'
        for e in entries:
            if e['group']==g: main_text+=f"| {card(e)} | {e['status']} |\n"
        main_text+='\n'
    main_text+=f'''## 범위와 유지 방법

- 대표 기록을 다시 읽어 **{len(entries)}개 카드**로 묶었다. 독립 실험 {len(entries)}회를 새로 했다는 뜻이 아니다. 한 폴더의 파생 방법은 관련 카드에 연결했다.
- [전체 폴더 색인](EXPERIMENT_FOLDERS.md): 지정한 연구 보관 경로의 직접 하위 **{len(inventory)}개 폴더**, 그중 **{covered}개**가 위 카드에 연결된다. 연결되지 않은 폴더는 **내용 판정 미재검토**로 명시했다. 실험 복제본·런타임·개별 모델 폴더 전체를 각각 독립 실험으로 세지 않는다.
- [구조화 원본](experiment_registry.json) · [문서 출처와 해시](INDEX_AUDIT.json). 판정은 원 보고서와 정정의 검토이며 원시 수치의 새 재계산이 아니다.
- 새 결과는 기존 실패를 삭제하지 않고 관련 카드에 연결한다. 새 카드에는 가설 한 줄, 조건, 정상 대조, 결과, non-IID 교훈, 반복 금지, 재검토 조건, 원문을 모두 넣는다.
- 유지보수: `python research/index_tools/rebuild_index.py`로 생성하고 `--check`로 파일·링크·출처 변경을 확인한다. 모델 카탈로그를 대신하는 도구가 아니다.
'''
    cards='# 실험 카드 — 가설·정상 대조·실패 이유\n\n[먼저 연구 인덱스 읽기](INDEX.md) · [전체 폴더](EXPERIMENT_FOLDERS.md)\n\n'+data['review_scope']+'\n\n'+data['hypothesis_note']+'\n\n'
    fields=[('conditions','조건'),('controls','정상 대조·비교'),('result','결과'),('non_iid_lesson','non-IID에 대해 남길 교훈'),('do_not_repeat','반복하지 않을 주장'),('revisit_condition','재검토 조건')]
    for e in entries:
        cards+=f"<a id=\"{e['id'].lower()}\"></a>\n\n## {e['id']} · {e['title']}\n\n**가설 한 줄: {e['hypothesis']}**\n\n**판정: {e['status']}**\n\n"
        if e.get('process_report'): cards+=ref(e['process_report'],'실험 시작 이유와 실제 실행 과정 읽기')+'\n\n'
        for k,label in fields: cards+=f"- **{label}:** {e[k]}\n"
        if e.get('provenance'): cards+=f"- **출처 구분:** {e['provenance']}\n"
        cards+='\n**원문·증거:**\n\n'+'\n'.join('- '+ref(s) for s in e['sources'])+'\n\n'
        if e['folders']:cards+='**묶은 폴더:** '+' · '.join(ref(f,f.split('/')[-1]) for f in e['folders'])+'\n\n'
    folder_text='# 전체 연구 폴더 색인\n\n[연구 인덱스](INDEX.md) · [실험 카드](EXPERIMENT_CARDS.md)\n\n'
    folder_text+='원본을 이동하지 않은 탐색용 목록이다. 직접 하위 폴더 단위의 재고이며, 행 하나가 독립 실험 또는 완료 실행 하나라는 뜻은 아니다. 연결 카드가 있어도 폴더 안의 모든 세부 파일을 이번에 재검토한 것은 아니다. 링크된 원문과 정정이 현재 해석의 근거다. Git에 포함되지 않은 경로는 로컬 보관으로 표시한다.\n\n'
    for base in list(dict.fromkeys(v['path'].rsplit('/',1)[0] for v in inventory)):
        folder_text+=f'## {base}\n\n| 원본 폴더 | 관련 카드·검토 범위 | 바로 아래 대표 문서 |\n|---|---|---|\n'
        for v in inventory:
            if v['path'].rsplit('/',1)[0]!=base:continue
            links=' · '.join(f'[{i}](EXPERIMENT_CARDS.md#{i.lower()})' for i in v['related_cards']) or '**내용 판정 미재검토**'
            docs=' · '.join(ref(p,p.split('/')[-1]) for p in v['top_level_documents'][:5])
            if len(v['top_level_documents'])>5: docs+=f" · 외{len(v['top_level_documents'])-5}개(구조화 목록 참조)"
            folder_text+=f"| {ref(v['path'],v['path'].split('/')[-1])} | {links} | {docs or '폴더에서 하위 기록 확인'} |\n"
        folder_text+='\n'
    audit=dict(schema='research-index-audit-v1',as_of=data['as_of'],review_scope=data['review_scope'],
        registry_sha256=digest(REGISTRY),cards=len(entries),unique_source_documents=len(sources),
        top_level_folders=len(inventory),folders_linked_to_cards=covered,source_sha256=sources,
        no_source_experiment_moved=True,no_model_or_raw_result_modified=True,no_new_experiment_run=True,
        inventory=inventory)
    outputs={'INDEX.md':main_text,'EXPERIMENT_CARDS.md':cards,'EXPERIMENT_FOLDERS.md':folder_text,
             'INDEX_AUDIT.json':json.dumps(audit,ensure_ascii=False,indent=2)+'\n'}
    for name,s in outputs.items(): write(RESEARCH/name,s,a.check)
    for name in ['INDEX.md','EXPERIMENT_CARDS.md','EXPERIMENT_FOLDERS.md']:
        content=outputs[name]
        for match in re.finditer(r'\]\(([^)]+)\)',content):
            target=match.group(1);part=target.split('#')[0]
            if part and not re.match(r'https?://',part): assert (RESEARCH/part).exists(),(name,target)
            if target.startswith('EXPERIMENT_CARDS.md#'):assert target.split('#')[1].upper() in ids
    print(json.dumps(dict(state='checked' if a.check else 'built',cards=len(entries),sources=len(sources),
        folders=len(inventory),linked_folders=covered,all_generated_links_resolve=True),ensure_ascii=True))

if __name__=='__main__':main()
