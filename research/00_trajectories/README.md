# 궤적부터 확인하는 연구 입구

**모델 선택 전에도 먼저 [연구 실험 인덱스](../INDEX.md)와 관련 카드·원 보고서를 읽는다.** 이 목록은 저장 상태와 허용 용도를 확인하는 곳이며, 기존 non-IID 구별 실패를 대신 검토해 주지 않는다. 아래 상태는 기록 시점의 감사이며 실행 중 여부는 별도로 확인한다.

**실험 모델은 이 목록의 고정 ID로 선택한다. 최종 모델 기본 입력은 `badfu.confirmed.s20261023.v1`, 전체 이력 기본 입력은 `badfu.paper32.s20261020`다.** 저장 검증·부분 억제 후 활성화·삭제 방식은 각각 별도 판정이다. FUBA에는 현재 승인된 잠복 활성화 전후쌍이 없다.

[재개·FUBA 수정의 최신 상태](../continuation_20261023/README.md) · [40R 추가 감사](audit/BADFU_RESUMED_COMPLETED.json)

[BadFU 알고리즘·저자 코드 직접 비교](../badfu_algorithm_audit_20261023/README.md) — 핵심 구현·첫 라운드 계산 일치, 원본 스크립트 전체/논문3회 평균 동일 재현은 미확정.

[확정 체크포인트 폴더](../../CONFIRMED_CHECKPOINTS/README.md) · [보관·로딩 검증 증거](audit/CONFIRMED_BADFU_S20261023_V1.json)

[검증 결과 요약](AUDIT_REPORT_KO.md)

## 먼저 읽을 판정

- **Paper32 5인:** 네 조건40R의 모든 파일 해시·모델 연결·참여자 집계 재구성·BN 버퍼·동일 초기화·삭제 인덱스를 직접 검사했다. 정상10000장/트리거9000장의 전후 평가도 다시 수행했다.
- **BadFU 추가 시드20261023:** 네 조건40R의 전역 모델 파일·텐서 연결·삭제 집합을 확인했다. 개별 참여자 제출 텐서가 없으므로 개별 이력 재집계 검증은 지원하지 않는다. 큰 정상 삭제는31R에서 재개하여40R 완료했고 추가 감사도 통과했다. 다음 조건은 진행 중이다.
- **FUBA 과거 후보:** 사전ASR98.69% 억제 실패와 미완료 대조 기록은 보존했다. 별도 v2 최종100R 검토용 사본은 아래 고정 ID와 근거를 따른다. 저장 통과를 잠복 공격 재현 성공으로 세지 않는다.
- **과거 seed42 및 잘못된 A/C 입력:** 원본은 보존하되 목표 잠복 공격 판정의 기본 입력에서 제외한다.

## 분류된 폴더

| 고정 ID | 저장 검증 | 용도/한계 | 폴더 |
|---|---|---|---|
| `badfu.confirmed.s20261023.v1` | 확정 모델 사본·로딩 검증 통과 | 부분 억제 후 활성화 확인 | [열기](00_confirmed/BadFU_s20261023_v1/README.md) |
| `badfu.paper32.s20261020` | 전체 궤적 검증 통과 | 부분 억제 후 활성화 확인 | [열기](01_verified/BadFU_Paper32_s20261020/README.md) |
| `badfu.multiseed.s20261023` | 전역 모델 이력 검증 통과 | 부분 억제 후 활성화 확인 | [열기](02_verified_global/BadFU_s20261023/README.md) |
| `badfu.multiseed.s20261023.normal_big4.partial` | 중단 전 저장 구간만 확인 | 최종 평가 없음 | [열기](03_incomplete/BadFU_normal_big4_round31/README.md) |
| `fuba.multiseed.s20261023.attack` | 전체 저장 궤적 검증 통과 | 삭제 전 억제 미성립 | [열기](04_reproduction_failed/FUBA_s20261023_attack/README.md) |
| `fuba.multiseed.s20261023.normal` | 중단 전 저장 구간만 확인 | 미완료 | [열기](03_incomplete/FUBA_s20261023_normal/README.md) |
| `fuba.corrected.s20261020.attack` | 전체 저장 궤적 검증 통과 | 수정 후보·목표 재현 미확인 | [열기](04_unapproved/FUBA_corrected_attack/README.md) |
| `fuba.corrected.s20261020.normal` | 중단 전 저장 구간만 확인 | 미완료 | [열기](03_incomplete/FUBA_corrected_normal/README.md) |
| `legacy.badfu.s42` | 목록·파일 크기만 확인 | 목표 잠복 검증에서 제외 | [열기](90_legacy/legacy_badfu/README.md) |
| `legacy.fuba.s42` | 목록·파일 크기만 확인 | 목표 잠복 검증에서 제외 | [열기](90_legacy/legacy_fuba/README.md) |
| `diagnostic.ac.wrong_source` | 실행 완료·입력 선택 부적합 | 목표 잠복 검증에서 제외 | [열기](90_legacy/ac_wrong_source/README.md) |
| `fuba.v2.s20261023.round0063.partial` | 중간 저장 파일·로딩 검증 통과 | 미완료 | [열기](03_incomplete/FUBA_v2_round0063/README.md) |
| `fuba.v2.s20261023.pre.round100` | 검토용 모델 사본·로딩 검증 통과 | 삭제 전 억제 미성립 | [열기](04_reproduction_failed/FUBA_v2_s20261023_pre100/README.md) |

| `fuba.v3.s20261023.pre.round0015.stopped` | 중단15R·사본 검증 통과 | γ0 억제 실패·진단 전용 | [열기](04_reproduction_failed/FUBA_v3_s20261023_stopped15/README.md) |

| `fuba.v4.s20261023.pre.round0023.stopped` | 중단23R·사본 검증 통과 | gamma상한중단·진단 전용 | [열기](04_reproduction_failed/FUBA_v4_s20261023_stopped23/README.md) |

**FUBA v5 최신:** `fuba.v5.s20261023.pre.round100` — 실제100R·사본 검증 통과, CA/사전억제 실패·진단 전용. [모델과 근거 열기](04_reproduction_failed/FUBA_v5_s20261023_pre100/README.md).

## 확인 범위와 증거

이번 감사는 전체 상태 형식의 362개 라운드와 전역 모델 형식의 191개 라운드를 새로 읽었다. 라운드 수는 독립 시드 수가 아니다. 과거 seed42 자료는 파일 존재·크기만 재확인했으며 이번에 모든 모델을 재집계한 자료로 표시하지 않는다.

[전체 감사](audit/AUDIT.json) · [분할·보류 자료 검사](audit/PARTITION_AUDIT.json) · [현재 상태 스냅샷](audit/INVENTORY.json) · [고정 목록](catalog.json) · [CSV](catalog.csv)

## 모델 선택

기본 사례의 삭제 전후 재학습 입력을 얻는다. 서버 입력에는 모델 위치·해시·상태 추출 키만 포함하며 실제 타깃/트리거/ASR은 전달하지 않는다.

```powershell
.\envs\badfu-original\python.exe research\00_trajectories\select_case.py badfu.confirmed.s20261023.v1 --purpose retrain_activation
```

`client_history`는 개별 참여자 상태가 있는 Paper32에서만 가능하다. `approximate_FU`로 사용할 수 있는 승인 사례는 현재 없다. 같은 초기값에서의 유지 자료 재학습을 근사 FedEraser로 부르지 않는다.

## 원본 경로와 정리 방식

모델·코드의 원본 경로는 유지한다. 기존 실행기는 절대 경로와 상위 폴더 위치에 의존하므로 큰 폴더를 옮기면 출처와 실행이 끊길 수 있다. DISLAB의 같은 분류 폴더 안 `original_data`는 원본을 그대로 보는 폴더 연결이다. 사본이나 추가 학습 결과가 아니다. 확정 체크포인트는 사용자 요청에 따라 별도 CONFIRMED_CHECKPOINTS 폴더에 실제 모델 사본도 보존한다. 이 보관본은 전체 이력이 아니다.

실제 원본: DISLAB `D:/TRAJECTORY_CATALOG_20261023`. 과거 개별 폴더의 상태 문장은 당시 스냅샷으로 취급하고 이 감사일의 목록을 우선한다.

**반증 기준:** 파일 해시, 앞뒤 모델, 재집계, 삭제 인덱스, 체크포인트와 평가의 연결 중 하나라도 실패하면 해당 사례의 용도를 승인하지 않는다. 저장 검증이 통과해도 사전 억제가 실패하거나 전후쌍이 없으면 목표 잠복 활성화 시험에 사용하지 않는다.

추가 감사는 같은 BadFU 실행의40R을 다시 확인했다(기존31R+새9R). 위553R 감사 합계에 독립 실행40R을 더한 것으로 세지 않는다. FUBA v2의1R CPU 검사는 실행 연결 검사이며 잠복 재현 성공이 아니다.

확정 모델을 로컬에서 바로 선택하려면 위 선택 명령에 `--location local`을 추가한다. 기본 출력 경로는 DISLAB다. 선택기는 해당 호스트에서 봉인 목록과 파일 해시를 확인하며, 학습 코드의 자동 재개 대상에는 이 보관 폴더를 넣지 않는다.

FUBA v2 최종 사본은 사용자 검토·진단 전용이다. [학습·평가·로컬 복사 근거](audit/FUBA_V2_ROUND100_DELIVERY.json)에 저장 검증과 사전 억제 판정을 구분했다. 기본 BadFU 사례는 유지한다.

FUBA v3는16R γ0 로컬 기준 실패로 중단됐습니다. [15R 사본 전달·독립 평가 근거](audit/FUBA_V3_STOPPED15_DELIVERY.json)를 따르며 기존 기본 사례는 유지합니다.

**2026-10-25 기존 FUBA 진단 입력 명시:** `fuba.legacy.s20261020.retained_pairs.diagnostic` — [기존 억제/정상 삭제 전후](04_reproduction_failed/FUBA_legacy_s20261020_diagnostic/README.md). diagnostic만 허용하며 잠복 재현 실패/큰 정상 대조 부재는 유지한다. 최신v5와 모든 기존 기본사례는 바뀌지 않는다.

FUBA v5의 실제 KD10 삭제 전후 모델과 로그: [fuba.v5.s20261023.post.kd10](04_reproduction_failed/FUBA_v5_s20261023_KD10_pair/README.md). 사전 성능 미달은 보존합니다.
