# BadFU 실험 기록

BadFU·FUBA 재현과 탐지·정화 실험의 조건, 과정, 결과를 정리했다.

[전체 실험 목록](experiments/README.md) · [용어와 모델 구분](experiments/GUIDE.md) · [과거 세부 실험](experiments/archive/README.md)

## 분야별 실험

| 분야 | 확인한 내용 | 기록 |
|---|---|---|
| [공격 재현](experiments/01-reproduction/README.md) | BadFU·FUBA의 학습과 실제 삭제 전후 모델 | R01–R02 |
| [공격 탐지](experiments/02-detection/README.md) | 이력, 입력 변형, 참여자 응답, 변형 비용과 모델 변화 비교 | D01–D19 |
| [원인 확인](experiments/03-mechanism/README.md) | 독성·위장 자료의 역할을 나눈 대조 | T01 |
| [정화](experiments/04-purification/README.md) | 반응 전이와 분류층 교정, 후속 파일럿 | P01–P03 |
| [보류한 제안](experiments/05-parked/README.md) | 신뢰 기준 모델 제안의 근거와 미확인 조건 | N01 |
| [과거 세부 실험](experiments/archive/README.md) | 기존 PR 보고서 68개와 추가 파일럿 | 과거 번호 유지 |

## 현재까지 확인한 범위

BadFU의 위장 자료 제거 후 공격 활성화는 관측했다. 탐지에서는 큰 정상 삭제와 점수가 겹치는 반례가 남았고, 일부 조건에서 얻은 분리 결과도 있다. 트리거 종류와 정상 분포가 달라져도 통하는 탐지 방법은 아직 확인하지 못했다.

## 브랜치

| 브랜치 | 용도 |
|---|---|
| [experiment-records](https://github.com/sijoon-sung/badfu_2/tree/experiment-records) · 기본 | 실험 과정·결과·근거 기록 |
| [original-reproduction](https://github.com/sijoon-sung/badfu_2/tree/original-reproduction) | 최초 재현 코드와 당시 실행 안내 |

## 자료 위치

| 위치 | 내용 |
|---|---|
| [experiments](experiments/README.md) | GitHub에서 읽는 실험 과정과 분야별 목록 |
| [research](research/README.md) | 원 보고서, 수치, 설정, 정정과 검증 기록 |
| [pr_reports](pr_reports/README.md) | 과거 세부 실험의 원문 |
| [reports](reports/README.md) | 날짜별 통합 문서와 내보내기 사본 |

[모델 안내](experiments/GUIDE.md) · [실험 기록 형식](experiments/TEMPLATE.md)
