# P04 BadFU·FedUBA 방어 개발

가설: 필요한 정상 삭제 기능을 유지하는 표현·헤드 개입으로 언러닝 유발 공격을 억제할 수 있다.

가설 → 실제 과정 → 결과 → 수정은 [실행 프로토콜](../../../research/badfu_feduba_defense_20261031/PROTOCOL.txt)에 고정한다. 큰 정상 non-IID 삭제의 필요조건부터 검사하고 전체 방어 성공은 아직 주장하지 않는다.

첫 H1은 Pre-backbone/Post-head 결합이다. 기존의 전체 정확도 보존 관측을 이어받았지만, 실제 CPU 검사에서 큰 정상 삭제의 한 클래스가5.62%p 낮아졌다. H2 무라벨 head 운반은 전체 효용도 악화시켰다. [실제 결과와 다음 수정](../../../research/badfu_feduba_defense_20261031/STAGE01_REPORT_KO.txt)을 보존한다.

다음 H3은 [backbone 가중치·BN 통계·head를 분리한 실제 개입](../../../research/badfu_feduba_defense_20261031/STAGE03_PROTOCOL.txt)이다. 이 진단은 공격 목표를 서버 선택에 넣지 않으며, 적격 FedUBA 모델과 삭제 품질은 아직 별도 필요조건이다.

[연구 카드와 근거](../../../research/EXPERIMENT_CARDS.md#p04)
