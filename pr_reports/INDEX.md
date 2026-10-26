# 실험별 PR 리포트 목록

연구 전체의 조건 변경·실패 원인·논문 대조·DISLAB 궤적은 [체계적 연구 정리](../research_audit_20261019/README.md)에서 읽는다. 해당 정리는 같은84건의 패치·기울기 결과와 정상144건을 별도로 보존한다.

각 링크는 가설 하나의 리포트다. 실행 명령은 저장소 루트의 PowerShell 기준이다. **D26 패치 탐지 리포트는 2026년 10월 19일 16:58 KST의 완료 70건으로 고정했으며, 조건·수식·그래프 4개와 개별 판정을 포함한다.** 나머지 진행 중 실험의 기존 리포트는 같은 날 15:15 조회 사본을 유지한다. H01은 과거 이력 실험이 없다는 오해를 막도록 범위를 정정했다. 서로 다른 시점의 수치를 같은 완료 건수로 비교하지 않는다.

## Non IID 최근 비교

- [M07 Non IID에서 실제 삭제 후 공격률 비교](mechanism/M07.md)
- [L01 BadFU 원논문의 정상 삭제와 공격자 삭제](literature/L01.md)
- [D26 고정 패치 탐지의 Non IID 규모 확장](detection/D26.md)
- [D27 FC 노름 비율의 Non IID 규모 확장](detection/D27.md)
- [D28 Conv 노름 비율의 Non IID 규모 확장](detection/D28.md)
- [D29 FC 직교 잔차 비율의 Non IID 규모 확장](detection/D29.md)
- [D30 Conv 직교 잔차 비율의 Non IID 규모 확장](detection/D30.md)
- [D33 쉽게 맞히는 정상 샘플 삭제의 오탐](detection/D33.md)

## 탐지

- [D01 고정 패치 짝 비교의 개발 실험](detection/D01.md)
- [D02 새 시드에서 위험 삭제와 같은 크기 안전 삭제 비교](detection/D02.md)
- [D03 정상 클래스 편향 대조에서 고정 패치 탐지](detection/D03.md)
- [D04 오라벨 대조에서 고정 패치 탐지](detection/D04.md)
- [D05 연속 패치 최적화로 위험 입력 찾기](detection/D05.md)
- [D06 정상 라벨 대조에서 연속 패치 탐지의 오탐 확인](detection/D06.md)
- [D07 요청 라벨 비율과 손실만으로 탐지하기](detection/D07.md)
- [D08 기존 복제 모델의 FC와 BN 변화 확인](detection/D08.md)
- [D09 FC 갱신 합의 클래스 집중도](detection/D09.md)
- [D10 유지 학습과 삭제 학습의 순서 차이](detection/D10.md)
- [D11 기존 16건의 순수 FC 노름 비율](detection/D11.md)
- [D12 FC 최대 특이값 비율](detection/D12.md)
- [D13 기존 100스텝 Conv 복제 모델의 노름 비율](detection/D13.md)
- [D14 FC와 Conv를 함께 놓은 2차원 비교](detection/D14.md)
- [D15 채널별 변화 집중도](detection/D15.md)
- [D16 유지와 삭제 갱신의 코사인 방향](detection/D16.md)
- [D17 Conv 변화 부분공간의 정렬도](detection/D17.md)
- [D18 두 복제 모델의 직접 차분](detection/D18.md)
- [D19 기존 16건의 순수 Conv 1스텝 노름 비율](detection/D19.md)
- [D20 FC 직교 잔차의 F노름 비율](detection/D20.md)
- [D21 Conv 직교 잔차의 F노름 비율](detection/D21.md)
- [D22 직교 잔차의 최대 특이값 비율](detection/D22.md)
- [D23 상위 좌표의 부호 충돌 탐지](detection/D23.md)
- [D24 정상 이미지 대신 랜덤 입력으로 패치 탐지](detection/D24.md)
- [D25 랜덤 입력 실패의 원인 분해](detection/D25.md)
- [D26 고정 패치 탐지의 Non IID 규모 확장](detection/D26.md)
- [D27 FC 노름 비율의 Non IID 규모 확장](detection/D27.md)
- [D28 Conv 노름 비율의 Non IID 규모 확장](detection/D28.md)
- [D29 FC 직교 잔차 비율의 Non IID 규모 확장](detection/D29.md)
- [D30 Conv 직교 잔차 비율의 Non IID 규모 확장](detection/D30.md)
- [D31 클래스 비율을 맞춘 정상 무작위 삭제](detection/D31.md)
- [D32 다수 클래스에 집중한 정상 삭제](detection/D32.md)
- [D33 쉽게 맞히는 정상 샘플 삭제의 오탐](detection/D33.md)
- [D34 어려운 정상 샘플 삭제의 오탐](detection/D34.md)
- [D35 삭제 요청과 잔류 자료의 상호작용으로 독성 자료 찾기](detection/D35.md)
- [D36 전후 손실 차이로 독성 학습 샘플 찾기](detection/D36.md)
- [D37 전후 입력 기울기로 독성 샘플 찾기](detection/D37.md)

## 정화

- [P01 공격 타겟 로짓 마스킹](purification/P01.md)
- [P02 전후 부분공간을 이용한 정화의 다른 시드 확인](purification/P02.md)
- [P03 전 층 상위 특이성분 제거 정화](purification/P03.md)
- [P04 사후 미세조정과 특징 모멘트 기준선](purification/P04.md)
- [P05 고정 변형의 반응 전이 정화](purification/P05.md)
- [P06 작은 학습률의 반응 전이 정화](purification/P06.md)
- [P07 입력을 다시 탐색하는 반복형 반응 전이](purification/P07.md)
- [P08 같은 정상 출력 변화 예산에서 반응 전이 비교](purification/P08.md)
- [P09 반응 전이 후 삭제 자료 기억 진단](purification/P09.md)
- [P10 실제 FU 후 모델의 마지막 층 일관성 교정](purification/P10.md)
- [P11 잔류 자료 재학습 모델의 마지막 층 교정](purification/P11.md)
- [P12 정상 모델에 같은 마지막 층 교정 적용](purification/P12.md)
- [P13 정상 클라이언트 삭제 후 마지막 층 교정](purification/P13.md)
- [P14 고정 패치 은행 수를 바꾼 교정 비교](purification/P14.md)
- [P15 FU 후 모델의 반례 패치 보강 교정](purification/P15.md)
- [P16 잔류 자료 재학습 모델의 반례 보강 실패](purification/P16.md)
- [P17 교정 모델에 대한 새 적응 패치 공격](purification/P17.md)
- [P18 요청 조건부로 잔류 자료를 더 제외한 재학습](purification/P18.md)
- [P19 반례 교정 실패의 선택 점수 스케일 분석](purification/P19.md)

## 기전 검증

- [M01 독성과 억제 자료의 네 조건 재학습](mechanism/M01.md)
- [M02 블록 교차 이식으로 활성화 위치 확인](mechanism/M02.md)
- [M03 마지막 특징 공간의 트리거 방향 분석](mechanism/M03.md)
- [M04 정상 입력의 타겟 편향과 트리거 반응 비교](mechanism/M04.md)
- [M05 전역 색감 변형에서 삭제 순서의 중간 위험](mechanism/M05.md)
- [M06 전역 질감 변형에서 삭제 순서의 중간 위험](mechanism/M06.md)
- [M07 Non IID에서 실제 삭제 후 공격률 비교](mechanism/M07.md)
- [M08 저자 코드 계열 모델의 삭제 전 잠복 여부 감사](mechanism/M08.md)
- [M09 정상 자료에서도 큰 직교 잔차가 나오는 수학적 반례](mechanism/M09.md)

## 논문 확인

- [L01 BadFU 원논문의 정상 삭제와 공격자 삭제](literature/L01.md)

## 미실행 제안

- [H01 최근16건과 과거 이력 자료의 대응 범위](pending/H01.md)
- [U01 요청자 전체 자료 일괄 삭제 정책](pending/U01.md)
