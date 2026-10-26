# 과거 세부 실험

[전체 실험](../README.md) · [추가 파일럿](PILOTS.md)

기존 PR 보고서 68개를 분야별로 모았다. 현재 실험 목록의 ID와 구분하기 위해 여기서는 `PR D01`처럼 표시한다. 같은 모델·요청을 재사용한 기록을 독립 학습 횟수로 합산하지 않는다.

원문에 적힌 실행 중·다음 실험은 작성 당시의 기록이다. 현재 판단은 [실험 목록](../README.md)에서 확인한다.

## 탐지 · 37개

| 기록 | 확인한 내용 |
|---|---|
| PR D01 | [고정 패치 짝 비교의 개발 실험](../../pr_reports/detection/D01.md) |
| PR D02 | [새 시드에서 위험 삭제와 같은 크기 안전 삭제 비교](../../pr_reports/detection/D02.md) |
| PR D03 | [정상 클래스 편향 대조에서 고정 패치 탐지](../../pr_reports/detection/D03.md) |
| PR D04 | [오라벨 대조에서 고정 패치 탐지](../../pr_reports/detection/D04.md) |
| PR D05 | [연속 패치 최적화로 위험 입력 찾기](../../pr_reports/detection/D05.md) |
| PR D06 | [정상 라벨 대조에서 연속 패치 탐지의 오탐 확인](../../pr_reports/detection/D06.md) |
| PR D07 | [요청 라벨 비율과 손실만으로 탐지하기](../../pr_reports/detection/D07.md) |
| PR D08 | [기존 복제 모델의 FC와 BN 변화 확인](../../pr_reports/detection/D08.md) |
| PR D09 | [FC 갱신 합의 클래스 집중도](../../pr_reports/detection/D09.md) |
| PR D10 | [유지 학습과 삭제 학습의 순서 차이](../../pr_reports/detection/D10.md) |
| PR D11 | [기존 16건의 순수 FC 노름 비율](../../pr_reports/detection/D11.md) |
| PR D12 | [FC 최대 특이값 비율](../../pr_reports/detection/D12.md) |
| PR D13 | [기존 100스텝 Conv 복제 모델의 노름 비율](../../pr_reports/detection/D13.md) |
| PR D14 | [FC와 Conv를 함께 놓은 2차원 비교](../../pr_reports/detection/D14.md) |
| PR D15 | [채널별 변화 집중도](../../pr_reports/detection/D15.md) |
| PR D16 | [유지와 삭제 갱신의 코사인 방향](../../pr_reports/detection/D16.md) |
| PR D17 | [Conv 변화 부분공간의 정렬도](../../pr_reports/detection/D17.md) |
| PR D18 | [두 복제 모델의 직접 차분](../../pr_reports/detection/D18.md) |
| PR D19 | [기존 16건의 순수 Conv 1스텝 노름 비율](../../pr_reports/detection/D19.md) |
| PR D20 | [FC 직교 잔차의 F노름 비율](../../pr_reports/detection/D20.md) |
| PR D21 | [Conv 직교 잔차의 F노름 비율](../../pr_reports/detection/D21.md) |
| PR D22 | [직교 잔차의 최대 특이값 비율](../../pr_reports/detection/D22.md) |
| PR D23 | [상위 좌표의 부호 충돌 탐지](../../pr_reports/detection/D23.md) |
| PR D24 | [정상 이미지 대신 랜덤 입력으로 패치 탐지](../../pr_reports/detection/D24.md) |
| PR D25 | [랜덤 입력 실패의 원인 분해](../../pr_reports/detection/D25.md) |
| PR D26 | [D26 — 고정 패치 탐지는 Non-IID에서 위험한 삭제 요청을 구별하는가?](../../pr_reports/detection/D26.md) |
| PR D27 | [FC 노름 비율의 Non IID 규모 확장](../../pr_reports/detection/D27.md) |
| PR D28 | [Conv 노름 비율의 Non IID 규모 확장](../../pr_reports/detection/D28.md) |
| PR D29 | [FC 직교 잔차 비율의 Non IID 규모 확장](../../pr_reports/detection/D29.md) |
| PR D30 | [Conv 직교 잔차 비율의 Non IID 규모 확장](../../pr_reports/detection/D30.md) |
| PR D31 | [클래스 비율을 맞춘 정상 무작위 삭제](../../pr_reports/detection/D31.md) |
| PR D32 | [다수 클래스에 집중한 정상 삭제](../../pr_reports/detection/D32.md) |
| PR D33 | [쉽게 맞히는 정상 샘플 삭제의 오탐](../../pr_reports/detection/D33.md) |
| PR D34 | [어려운 정상 샘플 삭제의 오탐](../../pr_reports/detection/D34.md) |
| PR D35 | [삭제 요청과 잔류 자료의 상호작용으로 독성 자료 찾기](../../pr_reports/detection/D35.md) |
| PR D36 | [전후 손실 차이로 독성 학습 샘플 찾기](../../pr_reports/detection/D36.md) |
| PR D37 | [전후 입력 기울기로 독성 샘플 찾기](../../pr_reports/detection/D37.md) |

## 정화 · 19개

| 기록 | 확인한 내용 |
|---|---|
| PR P01 | [공격 타겟 로짓 마스킹](../../pr_reports/purification/P01.md) |
| PR P02 | [전후 부분공간을 이용한 정화의 다른 시드 확인](../../pr_reports/purification/P02.md) |
| PR P03 | [전 층 상위 특이성분 제거 정화](../../pr_reports/purification/P03.md) |
| PR P04 | [사후 미세조정과 특징 모멘트 기준선](../../pr_reports/purification/P04.md) |
| PR P05 | [고정 변형의 반응 전이 정화](../../pr_reports/purification/P05.md) |
| PR P06 | [작은 학습률의 반응 전이 정화](../../pr_reports/purification/P06.md) |
| PR P07 | [입력을 다시 탐색하는 반복형 반응 전이](../../pr_reports/purification/P07.md) |
| PR P08 | [같은 정상 출력 변화 예산에서 반응 전이 비교](../../pr_reports/purification/P08.md) |
| PR P09 | [반응 전이 후 삭제 자료 기억 진단](../../pr_reports/purification/P09.md) |
| PR P10 | [실제 FU 후 모델의 마지막 층 일관성 교정](../../pr_reports/purification/P10.md) |
| PR P11 | [잔류 자료 재학습 모델의 마지막 층 교정](../../pr_reports/purification/P11.md) |
| PR P12 | [정상 모델에 같은 마지막 층 교정 적용](../../pr_reports/purification/P12.md) |
| PR P13 | [정상 클라이언트 삭제 후 마지막 층 교정](../../pr_reports/purification/P13.md) |
| PR P14 | [고정 패치 은행 수를 바꾼 교정 비교](../../pr_reports/purification/P14.md) |
| PR P15 | [FU 후 모델의 반례 패치 보강 교정](../../pr_reports/purification/P15.md) |
| PR P16 | [잔류 자료 재학습 모델의 반례 보강 실패](../../pr_reports/purification/P16.md) |
| PR P17 | [교정 모델에 대한 새 적응 패치 공격](../../pr_reports/purification/P17.md) |
| PR P18 | [요청 조건부로 잔류 자료를 더 제외한 재학습](../../pr_reports/purification/P18.md) |
| PR P19 | [반례 교정 실패의 선택 점수 스케일 분석](../../pr_reports/purification/P19.md) |

## 원인 확인 · 9개

| 기록 | 확인한 내용 |
|---|---|
| PR M01 | [독성과 억제 자료의 네 조건 재학습](../../pr_reports/mechanism/M01.md) |
| PR M02 | [블록 교차 이식으로 활성화 위치 확인](../../pr_reports/mechanism/M02.md) |
| PR M03 | [마지막 특징 공간의 트리거 방향 분석](../../pr_reports/mechanism/M03.md) |
| PR M04 | [정상 입력의 타겟 편향과 트리거 반응 비교](../../pr_reports/mechanism/M04.md) |
| PR M05 | [전역 색감 변형에서 삭제 순서의 중간 위험](../../pr_reports/mechanism/M05.md) |
| PR M06 | [전역 질감 변형에서 삭제 순서의 중간 위험](../../pr_reports/mechanism/M06.md) |
| PR M07 | [Non IID에서 실제 삭제 후 공격률 비교](../../pr_reports/mechanism/M07.md) |
| PR M08 | [저자 코드 계열 모델의 삭제 전 잠복 여부 감사](../../pr_reports/mechanism/M08.md) |
| PR M09 | [정상 자료에서도 큰 직교 잔차가 나오는 수학적 반례](../../pr_reports/mechanism/M09.md) |

## 논문 확인 · 1개

| 기록 | 확인한 내용 |
|---|---|
| PR L01 | [BadFU 원논문의 정상 삭제와 공격자 삭제](../../pr_reports/literature/L01.md) |

## 보류 · 2개

| 기록 | 확인한 내용 |
|---|---|
| PR H01 | [최근16건과 과거 이력 자료의 대응 범위](../../pr_reports/pending/H01.md) |
| PR U01 | [요청자 전체 자료 일괄 삭제 정책](../../pr_reports/pending/U01.md) |
