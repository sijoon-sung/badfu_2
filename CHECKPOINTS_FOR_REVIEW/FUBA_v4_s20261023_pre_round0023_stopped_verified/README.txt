FUBA v4 /23R 중단 모델 검토용 사본

100R 미완료·진단 전용입니다.24R client3의 gamma 탐색이 고정 상한10에서 종료됐습니다.
23R 독립 전체10000/9000장 평가: CA77.12%, ASR13.944444%. 기록과 정확히 일치합니다.
파일/연결/정확집계0,184역할/28생성기 그룹을 검증했습니다. 원본1–15R 재사용과16R 첫 역할 재사용은 별도 표시했습니다.
classifier.pt와 aggregate_generator.pt는 bare state_dict입니다. checkpoint_round0023.pt는 원본 묶음이며 gm_after / extras.aggregate_generator를 사용합니다.
failure_round0024_client03.pt는 원본 실패 당시incoming/G이며 중간모델과 gamma점수는 누락됐습니다. 이 한계를 숨기지 않습니다.
사용자가 별도 승인한 단일 참여자 진단은 provenance/cap24_replay_cached_G_20261024 아래에 있습니다. G재계산 사전검사의 실패는 cap24_replay_20261024에 보존했습니다. 원래 FL 라운드나 독립 학습 시드가 아닙니다.
본 사본에는 마지막23R 묶음만 있습니다. 전체23개 원본은 DISLAB 학습 폴더에 보존돼 있습니다.
외부 EXPORT23_READY.json의 manifest_sha256을 사용하여 load_checkpoint.py --expected-manifest-sha256 값으로 전체 해시/엄격 CPU 로딩/출력을 검사할 수 있습니다.
전체100R/CA80/ASR10 게이트와 잠복 전후쌍은 미통과입니다. 생성기/타깃/ASR/역할 진실은 평가자 전용이며 서버 탐지 방법 입력에 넣지 않습니다.
기존 BadFU/FUBA 사본은 보존했습니다.
