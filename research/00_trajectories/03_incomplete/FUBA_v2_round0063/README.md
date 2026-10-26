# FUBA v2 중간 체크포인트 — 63/100R 로컬 전달

고정 ID: `fuba.v2.s20261023.round0063.partial`

저장 검증: **중간 저장 파일·로딩 검증 통과**

공격 재현: **미완료**

삭제 후 모델의 종류: `pre_FU_partial_training`

허용 용도: diagnostic

DISLAB 원본 위치:

```text
D:\FUBA_CHECKPOINT_RECOVERY_20261023\partial_exports\FUBA_v2_s20261023_round0063
```

유의할 범위:

- 사용자 요청으로 당시 저장된 고정 라운드를 복사한 중간 모델. 전달 당시 전체100R은 진행 중.
- 해당 라운드 집계·인접 연결·분류기와 생성기 로딩을 확인했으며 전체 이력 감사는 아님.
- 완성된 잠복 공격 전후쌍·정화 입력·근사FU·탐지 성능 판정에 사용하지 않음.
- 원본 checkpoint.pt의 분류기는 gm_after만 추출. extras의 생성기는 평가자 전용.

[전체 목록](../../README.md) · [기계 판독 정보](case.json)
