# 확정 체크포인트 보존 기록 · 2026-10-23

최종 결과: [확정 BadFU 기준 모델 v1](../../CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1/README.md). 같은 학습의 최종 모델을 별도로 보관한 작업이며 새 독립 학습 실험이 아니다.

가설: 이미 검증한 모델을 원본과 분리한 실제 사본으로 고정하고 외부 등록 해시를 검사하면 이후 실험에서 입력이 바뀌거나 과거 고ASR 모델과 섞이는 실수를 차단할 수 있다.

조건과 비교: `badfu.multiseed.s20261023`의 명시적 최종40R 모델5개와 공통 초기값1개를 선택했다. DISLAB 원본 → DISLAB 별도 사본 → 로컬 별도 사본의 SHA256을 비교했다. 전체 이력은 복제하지 않았다.

결과: 양쪽 실제 사본의 6개 모델이 엄격한 상태 로딩, 유한 텐서와 BN 버퍼, 1×10 유한 출력 검사를 통과했다. 보관 파일은 읽기 전용이다. 기존 저자 형식 평가값은 삭제 전 CA90.38%/ASR14.2889%, 삭제 후 CA90.46%/ASR100%이며 가중치 해시로 연결되어 있다.

판정: `badfu.confirmed.s20261023.v1`을 최종 모델 실험의 기본 ID로 등록했다. 전체 이력 기본값은 `badfu.paper32.s20261020`이다. 새 보관본은 `retrain_activation`, `purification_pilot`만 허용하며 `client_history`를 거부한다.

반증 범위: 해시·봉인·모델 로딩 중 하나라도 불일치하면 이 보관본을 사용하지 않는다. 보관본은 논문3회 평균, ASR≤10% 강한 잠복 기준, 근사 FedEraser 또는 FUBA의 성공을 추가로 입증하지 않는다.

- [DISLAB 복사·검증](REMOTE_SNAPSHOT.json)
- [로컬 복사·검증](LOCAL_SNAPSHOT.json)
- [외부 등록 증거](../00_trajectories/audit/CONFIRMED_BADFU_S20261023_V1.json)
- [DISLAB 등록 최종 확인](REGISTRATION_CHECK.json)

가중치 경로는 안내 폴더에 고정했다. 운영 스크립트는 동일 버전의 재실행·덮어쓰기를 거부하며, 이전 안내와 목록은 `navigation_before_confirmation.zip`에 보존했다. 원본 학습 경로와 진행 중 실행은 건드리지 않았다.
