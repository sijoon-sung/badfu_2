# 실험 목록

[저장소 첫 화면](../README.md) · [용어와 모델 구분](GUIDE.md) · [과거 세부 실험](archive/README.md)

분야를 고른 뒤 실험 제목을 누르면 시작 이유, 조건, 실제 순서, 결과와 판단을 바로 읽을 수 있다. 각 실험의 `SOURCES.md`에는 원 보고서와 결과 파일을 모았다.

28개 항목은 연구 기록을 주제별로 묶은 것이다. 같은 모델을 여러 방법으로 검사한 경우가 있어 독립 학습 28회를 뜻하지 않는다.

## [공격 재현](01-reproduction/README.md)

| ID | 실험 | 현재 판단 |
|---|---|---|
| R01 | [BadFU 학습과 삭제 전후 모델 확인](01-reproduction/R01-badfu-reproduction/README.md) | 검증 범위 한정 |
| R02 | [FUBA 재현의 수정 과정과 실제 삭제 후 결과](01-reproduction/R02-fuba-reproduction/README.md) | FUBA 두완료실패 보존 / 사용자 FedUBA 대상정정으로 나머지queue중지 |
| R03 | [FedUBA 공식 배포본과 논문 재현의 진입 조건](01-reproduction/R03-feduba-reproduction/README.md) | FedUBA cleanFL20 실행 중 / STG100·5·100 CPU준비 통과·검증기반 대기 / 공격 미완료 |

## [공격 탐지](02-detection/README.md)

| ID | 실험 | 현재 판단 |
|---|---|---|
| D01 | [과거 학습 기여를 누적한 탐지](02-detection/D01-training-history/README.md) | 기존 점수 보류 |
| D02 | [의심 입력과 정상 입력의 이력 영향 비교](02-detection/D02-influence/README.md) | 구별 실패 |
| D03 | [입력 변형에 대한 삭제 전후 반응 비교](02-detection/D03-input-response/README.md) | 공통 구별 미확보 |
| D04 | [마지막 제출 제외와 참여자 역할 검사](02-detection/D04-client-removal/README.md) | 구별·역할 판정 실패 |
| D05 | [중간 특징에서 특정 출력으로 쏠리는 정도 검사](02-detection/D05-feature-bias/README.md) | 공통 특징 채택 안 함 |
| D06 | [정상 과제를 잊히는 진단의 반응 검사](02-detection/D06-forgetting/README.md) | 큰 정상 탈퇴 혼동 |
| D07 | [서버가 심은 진단 과제의 유지 여부 검사](02-detection/D07-diagnostic-task/README.md) | 파일럿 구별 실패 |
| D08 | [같은 잔류 참여자의 삭제 전후 응답 비교](02-detection/D08-matched-clients/README.md) | 핵심 반례 — 구별 실패 |
| D09 | [같은 성공률에 필요한 입력 변형 비용 비교](02-detection/D09-inversion-cost/README.md) | 제한적 관찰·안정성 미확보 |
| D10 | [비용 비교의 확인 자료와 공통 변화 보정](02-detection/D10-cost-correction/README.md) | 제한된 BadFU 지지 |
| D11 | [이미지별 변형 비용과 최소값 요약의 한계](02-detection/D11-minimum-cost/README.md) | 주력 채택 안 함·입력 한계 |
| D12 | [정상 이미지 없이 조건부 전환과 이력을 찾는 검사](02-detection/D12-data-free-probes/README.md) | 독립 입력 재현 실패 |
| D13 | [고정 패턴과 자유 마스크 및 특징 변환 비교](02-detection/D13-transform-families/README.md) | 범용 탐지 미확보 |
| D14 | [입력마다 달라지는 변형 규칙 학습](02-detection/D14-conditional-transform/README.md) | 일반화·구별 실패 |
| D15 | [두 학습 시드와 정상 참여자 자료에서 전후 탐색 확인](02-detection/D15-joint-search/README.md) | 두 시드 일관 구별 실패 |
| D16 | [후기 층 변화량 추천을 철회한 기록](02-detection/D16-retired-magnitude/README.md) | 사용자 지시로 주력 제외 |
| D17 | [정상 기능을 약화한 복사본과 원래 모델의 직접 탐색 비교](02-detection/D17-direct-search/README.md) | 노출 가설 기각·직접 탐색 한정 관찰 |
| D18 | [정상 이미지의 특징 공간 밖에 놓인 FC 변화 검사](02-detection/D18-feature-projection/README.md) | 한 시드 분리 관측·투영 추가 가치 미입증 |
| D19 | [같은 FC 공간 검사를 과거 FUBA 모델에 적용](02-detection/D19-fuba-projection/README.md) | 진단 쌍 분리 미관측·유효 잠복 FUBA는 미검증 |

## [원인 확인](03-mechanism/README.md)

| ID | 실험 | 현재 판단 |
|---|---|---|
| T01 | [독성 자료가 남는 경우와 없는 경우의 원인 대조](03-mechanism/T01-causal-controls/README.md) | 평가자 진단·조건부 증거 |

## [정화](04-purification/README.md)

| ID | 실험 | 현재 판단 |
|---|---|---|
| P01 | [삭제 전 반응을 옮기는 정화](04-purification/P01-response-transfer/README.md) | 제한된 정화 관찰 |
| P02 | [마지막 분류층만 바꾸는 교정](04-purification/P02-classifier-repair/README.md) | 제한된 정화 관찰 |
| P03 | [손실 분산과 채널 가림 및 헤드 증류 파일럿](04-purification/P03-purification-pilot/README.md) | 목표 판정 제외 — 입력 선택 오류 |

## [보류한 제안](05-parked/README.md)

| ID | 실험 | 현재 판단 |
|---|---|---|
| N01 | [신뢰 기준 모델을 더하는 제안의 보류](05-parked/N01-trusted-reference/README.md) | 미검증·자동 실행 대상 아님 |
| N02 | [넓은 탐지 주장과 공개 코드 정체 감사](05-parked/N02-broad-claim-audit/README.md) | 필요기하반례 확인·공통 탐지 보류 |

## 과거 세부 기록

[기존 PR 보고서 68개](archive/README.md)는 당시 번호와 수치를 유지했다. 본문의 D01과 과거 PR D01은 다른 기록이다. [추가 파일럿](archive/PILOTS.md)은 내용 판정 미재검토 상태를 유지한다.

[새 실험 기록 형식](TEMPLATE.md) · [판정과 출처를 관리하는 등록부](../research/experiment_registry.json)
