# R03 FedUBA 공식 배포본과 논문 재현의 진입 조건

[연구 인덱스](../../../research/INDEX.md) · [카드](../../../research/EXPERIMENT_CARDS.md#r03) · [재현 분야](../README.md)

가설: 공식 FedUBA 코드가 논문의 실행 절차와 표본 정체를 보존하여 탐지 검증에 쓸 실제 공격 전후쌍을 제공한다.

BadFU 외의 공격에도 탐지가 통하는지 검증하려면 먼저 해당 공격 자체를 재현해야 한다. `ity207/FedUBA`를 `stcebra/FUBA`와 구별하고, 저자 홈페이지의 원문·ZIP과 고정 GitHub commit을 대조했다. 기존 FUBA 모델을 재명명하지 않았다. 관련 R01/R02/D08/D15/D18/D19/N02의 한계와 실패를 보존한다.

계획과 코드를 [PR #1의 사전 고정 commit](https://github.com/sijoon-sung/badfu_2/commit/23159e615cd19e8d6b93c569c1110206da9ca2df)에 먼저 게시한 뒤 DISLAB에서 CPU 검사했다. 저자 ZIP 9파일은 고정 Git blob과 모두 같았다. 원본 두 모듈 import는 누락된 `utils`·`models` 때문에 실패했다. 원래 민감도 정렬 함수를 합성32샘플로 실행하니 섞인 로더의 반환 ID 순위는 정답과0/32, 순차 대조는32/32 일치했다. 기본 공격자 ID5/7과 보조자료 helper의 ID2/3 불일치도 원본 함수로 확인했다.

이는 원본 함수의 특정 계약 실패를 재현한 것이며 실제 공격 FL/FU나 ASR/CA 재현이 아니다. 필수 정의의 권위 있는 출처와 불일치를 해소하기 전 대규모 학습 진입을 중단했다. 수정 구현이 필요하면 변경 목록·고정 profile을 원본과 구별해야 한다. 현재 검증된 FedUBA 모델쌍은 없으며 탐지 사용도 미검증이다.

D08에서 공격0.75848이 큰 정상0.75525/0.76188 사이였던 반례는 그대로 남는다. 모델 재현에 성공해도 정상 큰 non-IID 삭제와의 구별이 자동으로 입증되지 않는다. 같은 실제 FU의 정상 대조와 새로운 행동 관측·독립 보정이 없으면 공통 탐지 주장을 하지 않는다.

- [원문·코드 대응](../../../research/feduba_reproduction_audit_20261031/CODE_PAPER_MATRIX.txt)
- [고정 프로토콜](../../../research/feduba_reproduction_audit_20261031/PROTOCOL.txt)
- [DISLAB 실제 결과](../../../research/feduba_reproduction_audit_20261031/RESULTS.json)
- [판정과 중단 지점](../../../research/feduba_reproduction_audit_20261031/REPORT_KO.txt)
- [큰 주장부터의 탐지 진입 조건](../../../research/feduba_reproduction_audit_20261031/DETECTION_GATES.txt)


2026-11-02 최신: 실제target-only125 정상·공격 체크포인트 생성을 DISLAB에서 진행한다. 기존all-class 선택에는목표클래스가0개였고 새선택125개는모두class2(owner58/67)다. 저장형식키누락으로학습전중단한첫시도와호출오류를보존한뒤 별도동일조건복구의실제trainer가시작됐다. 현재최종성능은미측정이다. [고정실행·오류·현재범위](../../../research/feduba_targetclass_pair_recovery_20261102/REPORT_KO.txt)와 [원조건·중단규칙](../../../research/feduba_targetclass_pair_recovery_20261102/PROTOCOL.txt)을읽는다. D08/D15와trigger-family독립탐지한계는해결하지않았다.


2026-11-03 최신: fixed10/newSSS 정상·공격FU20과 양독립CPU·각60000sample474calls 표준평가·원격readonly봉인이 실제완료했다. pre CA85.53/ASR20.1444%, 정상CA84.74/ASR-B16.6667%, 공격CA84.69/ASR13.8222%로 4성능gate실패/2CA통과다. 공격활성화가 재현되지 않았으며 저장완료를 성능성공으로 취급하지 않는다. [최종실제결과·한계](../../../research/feduba_fixed10_pair_20261103/FINAL_REPORT_KO.txt), [논문비교](../../../research/feduba_fixed10_pair_20261103/PAPER_COMPARISON.txt), [후속근거범위](../../../research/feduba_fixed10_pair_20261103/NEXT_STAGE_RATIONALE.txt)를 읽는다. task Ready/exit0/native0/failure0이며 이전유한작업 재실행0. Local전달/탐지/전체성능목표는 미완료다.


2026-11-03 후속: 새추론없이기존SSS40의저장logit을분석했다. 선택target125중76에서positive-delta의targetmargin이감소했고,비선택target343중202도감소했다. 비target4532의margin은3858개에서증가했다. 과반가설은지지됐지만selector고유원인/새선택/재훈련채택으로승격하지않는다. [고정진단·독립검산·범위](../../../research/feduba_fixed10_sss_direction_diagnosis_20261103/REPORT_KO.txt)를읽는다. 모델load/forward0·원query/rank/FU재실행0이며표준ASR와다른학습자료진단이다.

 관련 helper의 동일 poison_image 호출 signature/positive addition 대 논문 Eq8 negative 부호 차이를 새 source-only 조건으로 분리했다. 정상/minus baseline·새SSS선택은 원위치 명시재사용, 변경은 selected-image sign 한 개이며 helper의 추가 dataset getitem/RNG는 미채택. synthetic4 CPU 계약·새 attackFU20/CPU·후속 새 모델만 평가 계획을 선게시하며 아직 신규실행/성능0, Eq8적합/누락helper복구/탐지성공 미주장.

[별도 부호 조건 프로토콜](../../../research/feduba_related_helper_positive_20261103/PROTOCOL.txt) · [출처 근거](../../../research/feduba_related_helper_positive_20261103/SIGN_SOURCE_EVIDENCE.json)

[새 조건 실제 시작](../../../research/feduba_related_helper_positive_20261103/RUNNING_REPORT_KO.txt) · [새 모델만 평가 source](../../../research/feduba_related_helper_positive_evaluation_20261103/PROTOCOL.txt)。최종성능 미측정, 기존실패 불변.

[새 정 부호 FU20·CPU 완료](../../../research/feduba_related_helper_positive_20261103/CPU_COMPLETION_REPORT_KO.txt) · [새 모델 평가 실제 준비](../../../research/feduba_related_helper_positive_evaluation_20261103/ACTUAL_EVALUATION_REPORT_KO.txt)。최종성능 미측정.

[새 평가의 원실패와 한정 보관 계약](../../../research/feduba_positive_evaluation_prefix_archive_20261103/PROTOCOL.txt): primaryASR58.7444,독립수치대조종료후확인서작성실패. 원VERIFIED합성/재추론0.

[정 부호 최종 결과와 원실패 보존](../../../research/feduba_positive_evaluation_prefix_archive_20261103/FINAL_REPORT_KO.txt) · [고정 비교](../../../research/feduba_positive_evaluation_prefix_archive_20261103/COMPARISON.txt) · [후속 검토 범위](../../../research/feduba_positive_evaluation_prefix_archive_20261103/NEXT_STAGE_RATIONALE.txt). 새after/원raw와원평가exit1·VERIFIED부재를보존한별도CPU/봉인완료이며성공재현아님.
