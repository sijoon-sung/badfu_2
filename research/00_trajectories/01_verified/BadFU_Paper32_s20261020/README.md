# BadFU 5인 Paper32 — 전체 궤적·부분 억제 후 활성화

고정 ID: `badfu.paper32.s20261020`

저장 검증: **전체 궤적 검증 통과**

공격 재현: **부분 억제 후 활성화 확인**

삭제 후 모델의 종류: `retained_data_retraining`

허용 용도: retrain_activation, global_history, client_history, purification_pilot

DISLAB 원본 위치:

```text
C:\Users\DISLAB\Documents\antigravity\dazzling-lovelace\research_20261020\stage1_migrated_20261020\research\stage1_fresh_20261020\runs\badfu_paper32_plain_s20261020
```

유의할 범위:

- 1 FL 시드; 논문 3회 평균의 완전 재현으로 선언하지 않음
- 삭제 전 ASR 약16%: 부분 억제이며 ASR≤10%의 강한 잠복 기준은 충족하지 않음
- 삭제 후는 동일 초기화부터 유지 자료 전체 재학습; 근사 FedEraser 결과가 아님
- 정상850장 삭제 대조는 같은 감염 pre 모델을 사용하며 독성·위장을 유지

[전체 목록](../../README.md) · [기계 판독 정보](case.json)
