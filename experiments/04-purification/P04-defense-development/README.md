# P04 BadFU·FedUBA 방어 개발

가설: 실제 삭제 품질과 정상 non-IID 삭제의 효용을 보존하는 공개 기능 교정으로 BadFU·FedUBA의 활성화를 억제할 수 있다.

발견의 출발점은 Pre-backbone/Post-head 결합의 낮은 공격 성공률이었다. 전체 정확도뿐 아니라 클래스별 효용과 실제 삭제 자료를 검사하면서 무엇이 보존되고 무엇이 복원되는지 확인했고, 그 결과에 따라 방법을 수정했다. [첫 고정 프로토콜](../../../research/badfu_feduba_defense_20261031/PROTOCOL.txt)과 모든 실패는 보존한다.

| 단계 | 실제 관측과 수정 이유 |
|---|---|
| H1 단순 교차 결합 | ASR5.2444%지만 큰 정상 삭제의 worst-class가5.62%p 하락 |
| H2 head 운반 | 세 쌍 전체 정확도 악화 |
| H3 가중치·BN·head 분해 | BN/head만 복원해도 ASR100%; 모듈의 공동 적응을 무시할 수 없음 |
| H4 블록 선택 | 무라벨 예측 보존 조건에서 모두 원래 Post를 선택, 공격 ASR100% |
| H5 좌표 정렬 | ASR3.4778%/세 쌍 CA 기준 통과, 그러나 실제 삭제 cover 누설advantage.8354로 실패 |
| H6 Post 표현의 역운반 | 삭제 감사 기준은 통과하지만 ASR100% |
| H8 Post 학생 증류 | 큰 정상 삭제의 누설 기준 통과, CA4.2–4.4%p 하락. 같은-batch 손실 감소도 전체 정상 기능 보존을 뜻하지 않았음 |
| H9 공개 기능 보존 선택 | 큰 정상9668삭제에서 두 nonzero 후보 모두 CA·각class·삭제 감사·기존 교정90% 기준 통과 |
| H10 동일 규칙의 공격 확장 | 실제9000장 ASR raw100/99.7667%, 선택 후 두arm100%로 실패. 같은850 후속 실험은 중단 |
| 평가 대조군 정정 | 학생학습 public500을 비회원 대조에서 제외. 9500 clean/8542 trigger로440 class AUC를 검산했고 H9 큰정상 필요조건은 유지 |
| 전달 충실도 진단 | query 학생은 합성 자료에서 teacher와77.7344% 일치하지만 실제 heldout trigger에서는3.6057% 일치. 합성 탐색의 출력 대부분이 두 클래스로 집중됨 |
| H11 모든 출력 클래스 탐색 | 같은240시작점/20탐색step/100학생step으로 KL탐색과 모든클래스 공동목표를 비교하는 새 고정 프로토콜. 큰정상부터 다시 검사하며 아직 효과 미검증 |

[실제 삭제 감사](../../../research/badfu_feduba_defense_20261031/STAGE07_REPORT_KO.txt)는 초기 낮은 ASR이 삭제 기억 복원과 함께 나타났음을 확인했다. [H8 결과](../../../research/badfu_feduba_defense_20261031/STAGE08_REPORT_KO.txt)는 Pre 전체를 복사하지 않는 증류에서도 효용 손실을 제어해야 함을 보였다. [H9 결과](../../../research/badfu_feduba_defense_20261031/STAGE09_REPORT_KO.txt)는 정상 필요조건을 통과했지만 [H10 실제공격 결과](../../../research/badfu_feduba_defense_20261031/STAGE10_REPORT_KO.txt)는 동일 recipe의 공격 억제 실패를 보였다.

[H10 고정 프로토콜](../../../research/badfu_feduba_defense_20261031/STAGE10_PROTOCOL.txt)은 실제 트리거/타깃/ASR을 학습이나 서버 선택에 넣지 않는다. 원래 H8 후보와 교정 후 후보를 모두 보존하고, 공격 필요조건 실패 시 같은 예산을 사후 조절하지 않는다.

[대조군 정정 결과](../../../research/badfu_feduba_defense_20261031/HELDOUT_REFERENCE_CORRECTION_REPORT_KO.txt)가 삭제 감사의 최신 기준이다. 과거 all-test 수치는 지우지 않되 학생에게 미관측인 비회원 결과로 해석하지 않는다. [충실도 진단](../../../research/badfu_feduba_defense_20261031/FIDELITY_DIAGNOSIS_REPORT_KO.txt)을 바탕으로 만든 [H11 프로토콜](../../../research/badfu_feduba_defense_20261031/STAGE11_PROTOCOL.txt)은 실제 공격 타깃을 입력하지 않고 모든 출력 인덱스에 같은 탐색 예산을 배정한다. 이 자체가 충분한 영역 포괄이나 정상 non-IID 구별을 보장하지 않으므로 큰정상 삭제부터 동일 고정 기준으로 다시 검사한다.

현재는 기존 BadFU 한 시드와 재사용한 공개 분할의 개발 결과다. D08/D15의 다른 FU·시드 반례, 적격 FedUBA 전후 모델, 추가 확인 조건을 대신하지 않는다. 유한 회원 추론 감사 통과는 형식적 삭제 증명이 아니며, 공개 KL이나 alpha는 공격 탐지 점수가 아니다. [연구 카드와 전체 근거](../../../research/EXPERIMENT_CARDS.md#p04).
