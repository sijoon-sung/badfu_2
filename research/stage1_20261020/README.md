# 서버 관측 모델 비교와 공격 성립 재검증

이 폴더는 2026년 10월 20일 실행한 모델 추론, 원본 대조와 같은 시작점 학습의 기록이다. **원논문 조건과 높은 삭제 전 ASR의 원인에 대한 판정은 [재검증 보고서](../01_reproduction/badfu/PRE_ASR_REAUDIT.md)를 먼저 읽는다.**

사전 학습 자체와 향후 비교의 준비 상태는 [궤적 재사용 판정](../01_reproduction/TRAJECTORY_DECISION.md)에서 확인한다. 원본 궤적은 보존·재사용하고, 이 폴더의 탐지 점수를 잠복 활성화 검증 결과와 구분한다.

## 완료한 측정

- CIFAR-10 보존 학습 7개 갈래에서 서버가 보관할 수 있는 마지막 라운드 모델을 검증했다.
- 정상 학습 4개 실행과 공격 구성 3개에서 제출분 제외 모델 48개, 최근 라운드 비교 7개, 저자 BadFU FU 기준 2개를 비교했다. 같은 시드의 BadFU 두 공격 구성은 독립 시드가 아니다.
- 공개 원본·고정 패치 32종의 반응을 직접 추론했다. 선택용 160장과 확인용 160장을 분리했다. 실제 트리거·타깃 정답·ASR은 점수를 저장한 뒤 별도 평가에만 사용했다.
- BadFU 6개 보존 모델의 정상 10,000장·공격 9,000장을 새로 추론해 원본 전체 평가와 대조했다.
- 실제 학습 때의 위장 이미지 850장과 해시를 맞춰, 같은 시작 모델에서 독성·위장 배치 3조건을 비교했다. 변경한 로컬 데이터셋 4개를 각각 5 epoch 새로 학습했다.
- FUBA 학습된 생성기·무작위 생성기·무작위 교란 및 train/eval 모드를 정상 모델 3개와 공격 모델에 대조했다.

## 주요 파일

| 파일 | 의미 |
|---|---|
| [PROTOCOL.json](PROTOCOL.json), [CALIBRATION.json](CALIBRATION.json) | 새 원점수를 확인하기 전에 고정한 관측·점수·보정 기준 |
| [scores.json](scores.json) | 트리거 정답과 ASR을 입력받지 않은 탐지 점수 |
| [evaluation.json](evaluation.json) | 점수 동결 후 실제 트리거·생성기로 계산한 평가 |
| [results.csv](results.csv), [summary.json](summary.json) | 요청별 측정과 실행 단위 비교 |
| [configuration_audit.json](configuration_audit.json) | α·비율·학습 조건·실제 표본 수·클래스 분포 |
| [badfu_full_evaluation_audit.json](badfu_full_evaluation_audit.json) | 전체 시험 재추론과 원본 평가의 차이 |
| [badfu_arrangement_intervention.json](badfu_arrangement_intervention.json) | 동일 초기 모델에서 위장 위치를 바꾼 새 학습 |
| [cover_image_provenance_audit.json](cover_image_provenance_audit.json) | 로컬 위장 파일과 실제 사용본의 차이 및 복원 |
| [generator_controls.json](generator_controls.json) | FUBA 입력 생성기의 정상 모델 전이 대조 |
| [fuba_scaling_code_audit.json](fuba_scaling_code_audit.json) | 실제 실행 코드의 γ 불일치와 0 L2 항 검사 |
| [exploratory_normalization.json](exploratory_normalization.json) | 원점수 확인 후 수행한 개발 실험. 독립 검증 아님 |
| [figures](figures) | 측정 그래프 PNG·SVG |
| [assets/sources.json](assets/sources.json), [assets/bundle_hashes.json](assets/bundle_hashes.json) | 원본 체크포인트와 추출 모델 출처 |

`exclude_last_submission`은 마지막 라운드의 특정 제출분을 제외한 재집계다. 실제 FU나 과거 전체 기여 삭제로 부르지 않는다. 개별 제출 모델을 볼 수 없는 보안 집계 환경에서는 해당 비교를 계산할 수 없다.

현재 공격 실행은 충분한 새 시드·잠복 활성화 대조를 충족하지 않아, 1단계 탐지기를 확정하는 평가 집합으로 채택하지 않았다. 연구 방향을 정하는 기초 측정과 원인 재검증으로 보존한다.

## 재실행 경로

기존 `envs/badfu-original/python.exe` 환경에서 `run_observable.py`로 점수를 먼저 생성하고, 그 뒤 `evaluate_ground_truth.py`, `plot_and_summarize.py`를 실행한다. 원본 해시 목록과 `public_split.json`을 함께 보존해야 한다. 이미지 생성기나 실제 트리거를 탐지 단계로 가져오지 않는다.

`audit_badfu_mechanism.py --mode full_evaluation`은 전체 시험 재평가, `--mode intervention`은 동일 시작점의 한 라운드 대조다. `check_generator_controls.py`와 `plot_cause_audit.py`는 생성기 대조 및 원인 그래프를 만든다. 같은 모델 관측 파일이 존재하면 추론을 재사용하며, 다른 모델이나 조건의 결과를 같은 파일명으로 덮어쓰지 않는다.
