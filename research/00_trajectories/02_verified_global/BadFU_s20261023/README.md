# BadFU 추가 시드 — 완료된 다섯 조건의 전역 모델 이력

고정 ID: `badfu.multiseed.s20261023`

저장 검증: **전역 모델 이력 검증 통과**

공격 재현: **부분 억제 후 활성화 확인**

삭제 후 모델의 종류: `retained_data_retraining`

허용 용도: retrain_activation, global_history, purification_pilot

DISLAB 원본 위치:

```text
D:\MULTISEED_ACTUAL_FU_20261022\badfu\seed_20261023
```

유의할 범위:

- 개별 참여자 제출 텐서는 미저장: client_history 용도로 승인하지 않음
- 집계 오류0은 학습 당시 기록. 이번 감사는 파일·전역 텐서 연결을 재검증했고 개별 제출의 재집계는 불가능
- 큰 정상 참여자 삭제는31R부터 재개하여40R 완료. 다음 조건과 전체3시드 실행은 진행 중.
- 20261024·20261025는 아직 완료된 독립 반복이 아님
- 정상850 삭제 대조의 pre는 clean 모델. 같은 감염 pre의 큰 정상 삭제 대조는 미완료
- 원 평가의 channels-last 형식과 저자 NCHW 형식을 구분. 정상 pre ASR은 기존1.4111%, 저자 형식1.3889%; 원 기록 보존.

[전체 목록](../../README.md) · [기계 판독 정보](case.json)
