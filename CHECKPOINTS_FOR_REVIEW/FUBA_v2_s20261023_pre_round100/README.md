# FUBA v2 검토용 체크포인트 · 100라운드

**학습과 저장 무결성 검사가 완료된 삭제 전 모델입니다.** 사전 억제 기준 실패. 잠복 공격 확정본으로 사용할 수 없음.

대상: stcebra/FUBA 수정 후보, 시드20261023. 별도 ity207/FedUBA와 다릅니다.

- 정상 정확도: 71.8700% (전체10000장)
- 삭제 전 ASR: 99.0889% (타깃 제외9000장)
- 원본 최종 라운드 SHA256: `4a8ee78cdd68c4365ca4b7e50296b58c5e45e689c5ef5287a6f230c8c75a1268`
- `classifier.pt`: 최종 분류기 상태, `aggregate_generator.pt`: 같은 체크포인트의 집계 생성기
- `initial.pt`: 실제 학습 초기값. 모두 CPU에서 torch.load(..., weights_only=True)로 읽을 수 있습니다.

`python load_checkpoint.py --expected-manifest-sha256 <EXPORT_READY.json의 manifest_sha256>`으로 파일 해시·엄격한 모델 로딩·CPU 출력을 확인할 수 있습니다.

82R 저장 목록 교체 오류를 복구하고83R부터 이어간 운영 근거는 `provenance/`에 있습니다. 원래 저장 파일과 학습 조건은 보존했습니다.82R은 중단 당시 평가 전송 전이어서 해당 라운드 평가가 없습니다.

이 모델을 CONFIRMED_CHECKPOINTS 또는 승인된 삭제 전후쌍으로 표시하지 않습니다. 평가 정보·타깃·생성기는 방어 알고리즘의 서버 입력에 전달하지 않습니다. 기존 실패와 모델 원본은 보존되어 있습니다.
