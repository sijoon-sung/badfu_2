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
