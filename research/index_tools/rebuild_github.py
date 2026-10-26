"""Maintain the GitHub reading structure from the experiment registry.

Does not move experiment sources, load models, or run research code.
Use --initialize once to import the reviewed process narratives.
Use --check to verify generated navigation and Git-index link targets.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'research/experiment_registry.json'
SNAPSHOT = ROOT / 'reports/experiment_process_20261026'
sys.stdout.reconfigure(encoding='utf-8')

GROUPS = [
    ('01-reproduction', '공격 재현', ['R01', 'R02'], '삭제 전후 모델이 어떤 절차로 만들어졌는지 확인한다.'),
    ('02-detection', '공격 탐지', [f'D{i:02}' for i in range(1, 20)], '공격 삭제와 큰 정상 참여자 삭제를 같은 조건에서 비교한다.'),
    ('03-mechanism', '원인 확인', ['T01'], '독성 자료와 위장 자료의 역할을 대조한다.'),
    ('04-purification', '정화', ['P01', 'P02', 'P03'], '삭제 후 공격을 줄이면서 정상 성능을 유지할 수 있는지 검사한다.'),
    ('05-parked', '보류한 제안', ['N01'], '실행 근거가 부족한 제안과 다시 검토할 조건을 기록한다.'),
]
SLUGS = dict(zip(
    ['R01','R02'] + [f'D{i:02}' for i in range(1,20)] + ['T01','P01','P02','P03','N01'],
    ['badfu-reproduction','fuba-reproduction','training-history','influence','input-response',
     'client-removal','feature-bias','forgetting','diagnostic-task','matched-clients',
     'inversion-cost','cost-correction','minimum-cost','data-free-probes','transform-families',
     'conditional-transform','joint-search','retired-magnitude','direct-search',
     'feature-projection','fuba-projection','causal-controls','response-transfer',
     'classifier-repair','purification-pilot','trusted-reference']))
DETECTION_SECTIONS = [
    ('학습 이력과 영향력', ['D01','D02']),
    ('입력·특징·참여자 응답', ['D03','D04','D05','D06','D07','D08']),
    ('변형을 찾는 데 필요한 비용', ['D09','D10','D11']),
    ('삭제 후 새로 생긴 오류 찾기', ['D12','D13','D14','D15','D17']),
    ('모델 변화량과 후속 진단', ['D16','D18','D19']),
]
LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def href(source, target):
    return Path(os.path.relpath(target, source.parent)).as_posix()


def rebase(text, source, target):
    def replace(match):
        dest = match.group(2)
        if re.match(r'^[a-z]+:', dest, re.I) or dest.startswith('#'):
            return match.group(0)
        part, sep, anchor = dest.partition('#')
        return f'[{match.group(1)}]({href(target, (source.parent / part).resolve())}{sep}{anchor})'
    return LINK.sub(replace, text)


def write(path, content, check):
    content = content.rstrip() + '\n'
    if check:
        assert path.is_file() and path.read_text(encoding='utf-8') == content, f'Stale: {path}'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def table(ids, page, entries):
    rows = ['| ID | 실험 | 현재 판단 |', '|---|---|---|']
    for card_id in ids:
        entry = entries[card_id]
        report = ROOT / entry['process_report']
        title = report.read_text(encoding='utf-8').splitlines()[0].removeprefix('# ').removeprefix(card_id + ' ')
        rows.append(f"| {card_id} | [{title}]({href(page, report)}) | {entry['status']} |")
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initialize', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    assert not (args.initialize and args.check)
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    entries = {e['id']: e for e in data['entries']}
    outputs = []
    ids = [i for _, _, group_ids, _ in GROUPS for i in group_ids]
    assert set(ids) == set(entries) and len(ids) == len(set(ids))

    for folder, group_title, group_ids, _ in GROUPS:
        group_page = ROOT / 'experiments' / folder / 'README.md'
        for card_id in group_ids:
            entry = entries[card_id]
            report = group_page.parent / f'{card_id}-{SLUGS[card_id]}' / 'README.md'
            if args.initialize:
                assert not report.exists(), f'Will not overwrite authored experiment: {report}'
                source = ROOT / entry['process_report']
                text = rebase(source.read_text(encoding='utf-8'), source, report)
                title, body = text.split('\n', 1)
                nav = '[저장소 첫 화면](../../../README.md) · [전체 실험](../../README.md) · [분야 목록](../README.md)'
                footer = '\n\n[등록된 근거 파일 전체](SOURCES.md) · [실험 조건과 판정 원문](../../../research/EXPERIMENT_CARDS.md#' + card_id.lower() + ')'
                write(report, title + '\n\n' + nav + '\n\n' + body.strip() + footer, False)
                entry['process_report'] = report.relative_to(ROOT).as_posix()
                entry['github_group'] = folder
            assert entry['process_report'] == report.relative_to(ROOT).as_posix(), card_id
            outputs.append(report)
            sources_page = report.parent / 'SOURCES.md'
            source_lines = [f'# {card_id} 근거 파일', '', '[실험 과정과 결과로 돌아가기](README.md)', '',
                '실험 설정, 원 보고서, 결과와 정정 기록을 함께 연결했다. 파일을 보존한 사실과 실험 성능이 검증된 범위는 본문의 판단에서 구분한다.', '',
                '| 파일 | 원래 보관 경로 |', '|---|---|']
            for rel in entry['sources']:
                source_lines.append(f'| [{Path(rel).name}]({href(sources_page, ROOT / rel)}) | `{str(Path(rel).parent).replace(chr(92), "/")}` |')
            write(sources_page, '\n'.join(source_lines), args.check)
            outputs.append(sources_page)

    if args.initialize:
        data['process_reporting']['index'] = 'experiments/README.md'
        data['process_reporting']['snapshot_index'] = 'reports/experiment_process_20261026/README.md'
        data['process_reporting']['purpose'] = 'GitHub에서 읽는 실험 과정의 정식 입구. 날짜별 통합 문서는 당시의 내보내기 사본이다.'
        REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    index = ROOT / 'experiments/README.md'
    index_lines = ['# 실험 목록', '', '[저장소 첫 화면](../README.md) · [용어와 모델 구분](GUIDE.md) · [과거 세부 실험](archive/README.md)', '',
        '분야를 고른 뒤 실험 제목을 누르면 시작 이유, 조건, 실제 순서, 결과와 판단을 바로 읽을 수 있다. 각 실험의 `SOURCES.md`에는 원 보고서와 결과 파일을 모았다.', '',
        '26개 항목은 연구 기록을 주제별로 묶은 것이다. 같은 모델을 여러 방법으로 검사한 경우가 있어 독립 학습 26회를 뜻하지 않는다.', '']
    for folder, title, group_ids, description in GROUPS:
        group_page = ROOT / 'experiments' / folder / 'README.md'
        lines = [f'# {title}', '', '[저장소 첫 화면](../../README.md) · [전체 실험](../README.md)', '', description, '']
        if folder == '02-detection':
            for section_title, section_ids in DETECTION_SECTIONS:
                lines.extend([f'## {section_title}', '', table(section_ids, group_page, entries), ''])
        else:
            lines.append(table(group_ids, group_page, entries))
        write(group_page, '\n'.join(lines), args.check)
        outputs.append(group_page)
        index_lines.extend([f'## [{title}]({folder}/README.md)', '', table(group_ids, index, entries), ''])
    index_lines.extend(['## 과거 세부 기록', '',
        '[기존 PR 보고서 68개](archive/README.md)는 당시 번호와 수치를 유지했다. 본문의 D01과 과거 PR D01은 다른 기록이다. [추가 파일럿](archive/PILOTS.md)은 내용 판정 미재검토 상태를 유지한다.', '',
        '[새 실험 기록 형식](TEMPLATE.md) · [판정과 출처를 관리하는 등록부](../research/experiment_registry.json)'])
    write(index, '\n'.join(index_lines), args.check)
    outputs.append(index)

    archive = ROOT / 'experiments/archive/README.md'
    records = json.loads((SNAPSHOT / 'legacy_source_records.json').read_text(encoding='utf-8'))
    legacy_groups = [('detection','탐지'),('purification','정화'),('mechanism','원인 확인'),('literature','논문 확인'),('pending','보류')]
    lines = ['# 과거 세부 실험', '', '[전체 실험](../README.md) · [추가 파일럿](PILOTS.md)', '',
        '기존 PR 보고서 68개를 분야별로 모았다. 현재 실험 목록의 ID와 구분하기 위해 여기서는 `PR D01`처럼 표시한다. 같은 모델·요청을 재사용한 기록을 독립 학습 횟수로 합산하지 않는다.', '',
        '원문에 적힌 실행 중·다음 실험은 작성 당시의 기록이다. 현재 판단은 [실험 목록](../README.md)에서 확인한다.', '']
    for key, title in legacy_groups:
        subset = [r for r in records if r['group'] == key]
        lines.extend([f'## {title} · {len(subset)}개', '', '| 기록 | 확인한 내용 |', '|---|---|'])
        for record in subset:
            lines.append(f"| PR {record['old_id']} | [{record['title']}]({href(archive, ROOT / record['source'])}) |")
        lines.append('')
    write(archive, '\n'.join(lines), args.check)
    outputs.append(archive)

    if args.initialize:
        pilot_page = ROOT / 'experiments/archive/PILOTS.md'
        pilot_source = SNAPSHOT / 'ADDITIONAL_RECORDS.md'
        write(pilot_page, rebase(pilot_source.read_text(encoding='utf-8'), pilot_source, pilot_page) + '\n\n[과거 실험 목록](README.md)', False)

    if args.check:
        tracked = set(subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode('utf-8').split('\0'))
        outputs += [ROOT/'README.md', ROOT/'research/README.md', ROOT/'experiments/GUIDE.md',
                    ROOT/'experiments/TEMPLATE.md', ROOT/'experiments/archive/PILOTS.md',
                    ROOT/'reports/README.md', SNAPSHOT/'README.md', ROOT/'pr_reports/README.md']
        outputs += [ROOT / record['source'] for record in records]
        link_count = 0
        for page in outputs:
            assert page.relative_to(ROOT).as_posix() in tracked, f'Unpublished page: {page}'
            for match in LINK.finditer(page.read_text(encoding='utf-8')):
                dest = unquote(match.group(2).split('#')[0])
                if not dest or re.match(r'^[a-z]+:', dest, re.I):
                    continue
                target = (page.parent / dest).resolve()
                assert target.is_relative_to(ROOT) and target.exists(), (page, dest)
                rel = target.relative_to(ROOT).as_posix()
                published = rel in tracked or (target.is_dir() and any(p.startswith(rel + '/') for p in tracked))
                assert published, f'Local-only target: {page} -> {dest}'
                link_count += 1
        print(json.dumps({'state':'checked','experiment_pages':len(ids),'legacy_records':len(records),
                          'published_navigation_pages':len(outputs),'local_links_in_git':link_count}, ensure_ascii=False))
    else:
        print(json.dumps({'state':'built','experiment_pages':len(ids),'legacy_records':len(records)}))


if __name__ == '__main__':
    main()
