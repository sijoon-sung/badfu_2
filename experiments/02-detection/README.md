# 공격 탐지

[저장소 첫 화면](../../README.md) · [전체 실험](../README.md)

공격 삭제와 큰 정상 참여자 삭제를 같은 조건에서 비교한다.

## 학습 이력과 영향력

| ID | 실험 | 현재 판단 |
|---|---|---|
| D01 | [과거 학습 기여를 누적한 탐지](D01-training-history/README.md) | 기존 점수 보류 |
| D02 | [의심 입력과 정상 입력의 이력 영향 비교](D02-influence/README.md) | 구별 실패 |

## 입력·특징·참여자 응답

| ID | 실험 | 현재 판단 |
|---|---|---|
| D03 | [입력 변형에 대한 삭제 전후 반응 비교](D03-input-response/README.md) | 공통 구별 미확보 |
| D04 | [마지막 제출 제외와 참여자 역할 검사](D04-client-removal/README.md) | 구별·역할 판정 실패 |
| D05 | [중간 특징에서 특정 출력으로 쏠리는 정도 검사](D05-feature-bias/README.md) | 공통 특징 채택 안 함 |
| D06 | [정상 과제를 잊히는 진단의 반응 검사](D06-forgetting/README.md) | 큰 정상 탈퇴 혼동 |
| D07 | [서버가 심은 진단 과제의 유지 여부 검사](D07-diagnostic-task/README.md) | 파일럿 구별 실패 |
| D08 | [같은 잔류 참여자의 삭제 전후 응답 비교](D08-matched-clients/README.md) | 핵심 반례 — 구별 실패 |

## 변형을 찾는 데 필요한 비용

| ID | 실험 | 현재 판단 |
|---|---|---|
| D09 | [같은 성공률에 필요한 입력 변형 비용 비교](D09-inversion-cost/README.md) | 제한적 관찰·안정성 미확보 |
| D10 | [비용 비교의 확인 자료와 공통 변화 보정](D10-cost-correction/README.md) | 제한된 BadFU 지지 |
| D11 | [이미지별 변형 비용과 최소값 요약의 한계](D11-minimum-cost/README.md) | 주력 채택 안 함·입력 한계 |

## 삭제 후 새로 생긴 오류 찾기

| ID | 실험 | 현재 판단 |
|---|---|---|
| D12 | [정상 이미지 없이 조건부 전환과 이력을 찾는 검사](D12-data-free-probes/README.md) | 독립 입력 재현 실패 |
| D13 | [고정 패턴과 자유 마스크 및 특징 변환 비교](D13-transform-families/README.md) | 범용 탐지 미확보 |
| D14 | [입력마다 달라지는 변형 규칙 학습](D14-conditional-transform/README.md) | 일반화·구별 실패 |
| D15 | [두 학습 시드와 정상 참여자 자료에서 전후 탐색 확인](D15-joint-search/README.md) | 두 시드 일관 구별 실패 |
| D17 | [정상 기능을 약화한 복사본과 원래 모델의 직접 탐색 비교](D17-direct-search/README.md) | 노출 가설 기각·직접 탐색 한정 관찰 |

## 모델 변화량과 후속 진단

| ID | 실험 | 현재 판단 |
|---|---|---|
| D16 | [후기 층 변화량 추천을 철회한 기록](D16-retired-magnitude/README.md) | 사용자 지시로 주력 제외 |
| D18 | [정상 이미지의 특징 공간 밖에 놓인 FC 변화 검사](D18-feature-projection/README.md) | 한 시드 분리 관측·투영 추가 가치 미입증 |
| D19 | [같은 FC 공간 검사를 과거 FUBA 모델에 적용](D19-fuba-projection/README.md) | 진단 쌍 분리 미관측·유효 잠복 FUBA는 미검증 |
