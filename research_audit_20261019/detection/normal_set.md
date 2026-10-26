# 정상 설명 집합과 누적 기여 차감이 막힌 이유

**질문:** 정상 학습으로 설명 가능한 이력 기여를 제거하면 남는 상쇄 관계로 위험 삭제를 구별할 수 있는가?

## 관측 결과

| 사례 | 모델 종류 | 정상 정확도 전→후 | 이력 판정 |
|---|---|---|---|
| badfu_attack_actual | {'candidate_kind': 'actual_author_fu', 'request_clients': [5], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'5': 40}, 'actual_fu_verified': True, 'fu_phase': 'fu_remove5', 'fu_manifest_sha256': '3406e9e2efa06e026f1da473507f5ee4cf3d25955f19afdeb29d475695bbfe5f'} | 91.25→95.00% | 미판정 |
| badfu_attack_surrogate | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [5], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'5': 40}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 91.25→43.75% | 미판정 |
| badfu_clean_delete0 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [0], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'0': 40}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 86.25→12.50% | 미판정 |
| badfu_clean_delete1 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [1], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'1': 40}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 86.25→17.50% | 미판정 |
| badfu_clean_delete2 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [2], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'2': 40}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 86.25→26.25% | 미판정 |
| badfu_clean_delete3 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [3], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'3': 40}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 86.25→28.75% | 미판정 |
| badfu_clean_delete4 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [4], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'4': 40}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 86.25→11.25% | 미판정 |
| fuba_attack_surrogate | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [4], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'4': 35}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 78.75→10.00% | 미판정 |
| fuba_benign0_delete4 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [4], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'4': 35}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 81.25→20.00% | 미판정 |
| fuba_benign1_delete4 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [4], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'4': 39}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 86.25→15.00% | 미판정 |
| fuba_benign2_delete4 | {'candidate_kind': 'historical_parameter_subtraction_surrogate', 'request_clients': [4], 'request_unit': 'whole_client', 'dose': 1.0, 'participation': {'4': 41}, 'actual_fu_verified': False, 'buffer_policy': 'final FL buffers unchanged; parameters only subtracted'} | 83.75→10.00% | 미판정 |

정상 설명 집합을 사용한 점수는11건 전부null이다. 이력의 정상 설명 범위가 충분하지 않아 미판정한 것이며, 공격을 안전하다고 맞힌 결과가 아니다. 과거 분석에는 비영 기여1,110개 전부 설명 실패가 기록돼 있다. 이번에는11개 원본 scores의 미판정을 다시 확인했다.

## 두 가지 문제가 분리된다

**첫째, 정상 설명 가정의 미충족이다.** 깨끗한 관측으로 만든 설명 집합이 실제 이력 기여를 포괄하지 못해 계산이 멈췄다. 정상 학습의 여러 SGD 스텝, BN, 유한한 공개 관측의 영향 중 무엇이 얼마나 기여했는지는 별도 원인 실험이 필요하다. 알고리즘 전체의 수학적 불가능성으로 확대하지 않는다.

**둘째, 실제 FU가 아닌 대용 모델의 붕괴다.** 누적 기여 차감으로 만든 FUBA 공격 대용 모델은 정상 정확도가78.75→10.00%로 떨어지고 깨끗한 입력도 모두 한 타깃으로 갔다. 큰 점수를 실제 FU의 잠복 백도어 활성화라고 볼 수 없다. 정상 BadFU 차감 대조도 정상 정확도가 무너진 사례가 있다.

실제 BadFU FU 사례는 정상 정확도91.25→95.00%를 유지하며 탐색 패치 응답2.78→73.61%가 관측됐다. 하지만 동일 시작 모델의 실제 정상 FU 대조와 진짜 트리거 ASR은 이 관측표에서 없었다. 대용 대조로 그 공백을 메우지 않는다.

15R의 별도 FU 재평가에서는 삭제 없는 보정만으로 ASR21.88→65.23%였고, 정상 삭제는67.58–77.73%, 억제자 삭제는91.02%였다. 이 한 단계 조정 결과를40R 공식 FU의 대응 정상 대조로 옮기지 않는다.

**당시 판단:** 2026-10-17 연구 기록에서 정상 표현 가정이 충족되지 않았고 이력 추가 이득을 입증하지 못했다고 정정했다. 이후 실제 FU 후 교정으로 범위를 옮겼다. [조건 변경표](../CHANGES.md)

근거: [11건 비교](../evidence/remote/artifacts/deletion_comparison_v1/report.md), [미판정·대조 범위](../evidence/remote/artifacts/deletion_comparison_v1/comparison.json), [FUBA 붕괴 원본](../evidence/remote/artifacts/deletion_comparison_v1/fuba_attack_surrogate/scores.json), [실제 FU 관측](../evidence/remote/artifacts/deletion_comparison_v1/badfu_attack_actual/scores.json), [15R 재평가](../evidence/remote/experiments/detection/hrac_matched/results/fu_recheck_v1/results.json).
