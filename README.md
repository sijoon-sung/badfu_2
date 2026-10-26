# BadFU 실험 기록

위장 자료를 삭제한 뒤 강해지는 공격을 재현하고, 이를 큰 정상 참여자의 자료 삭제와 구별할 수 있는지 실험했다. 각 기록에는 **시작 이유 → 실험 조건 → 실행 순서 → 결과 → 판단**을 적었다.

**[전체 실험 목록](experiments/README.md)** · [용어와 모델 구분](experiments/GUIDE.md) · [과거 세부 실험](experiments/archive/README.md)

## 처음 읽는 순서

1. **[R01 · BadFU 재현](experiments/01-reproduction/R01-badfu-reproduction/README.md)** — 어떤 모델과 삭제 절차를 사용했는지 확인한다.
2. **[D08 · 같은 참여자 응답 비교](experiments/02-detection/D08-matched-clients/README.md)** — 큰 정상 삭제가 공격과 비슷한 점수를 만드는 문제를 본다.
3. **[D17 · 직접 탐색과 복사본 탐색 비교](experiments/02-detection/D17-direct-search/README.md)** — 후속 실험의 실제 과정과 제한된 결과를 본다.

그다음 아래 분야에서 필요한 실험을 고르면 된다. 각 실험 폴더의 `README.md`에서 과정을 읽고, `SOURCES.md`에서 원 보고서·결과·정정 기록을 확인할 수 있다.

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

BadFU의 위장 자료 제거 후 공격 활성화는 관측했다. 탐지에서는 큰 정상 삭제와 점수가 겹치는 반례가 남았고, 일부 조건에서 얻은 분리 결과도 있다. **트리거 종류와 정상 분포가 달라져도 통하는 탐지 방법은 아직 확인하지 못했다.** 각 결과의 비교 조건과 한계는 해당 실험에 함께 적었다.

## 브랜치

| 브랜치 | 용도 |
|---|---|
| [codex/experiment-records](https://github.com/sijoon-sung/badfu_2/tree/codex/experiment-records) · 기본 | 이 실험 목록과 과정·결과·근거 기록 |
| [codex/original-reproduction](https://github.com/sijoon-sung/badfu_2/tree/codex/original-reproduction) | 최초 재현 코드와 당시 실행 안내 |

## 자료 위치

| 위치 | 내용 |
|---|---|
| [experiments](experiments/README.md) | GitHub에서 읽는 실험 과정과 분야별 목록 |
| [research](research/README.md) | 원 보고서, 수치, 설정, 정정과 검증 기록 |
| [pr_reports](pr_reports/README.md) | 과거 세부 실험의 원문 |
| [reports](reports/README.md) | 날짜별 통합 문서와 내보내기 사본 |

모델 선택과 보관 범위는 [용어와 모델 안내](experiments/GUIDE.md)를 따른다. 새 실험을 기록할 때는 [기록 형식](experiments/TEMPLATE.md)을 사용한다.
