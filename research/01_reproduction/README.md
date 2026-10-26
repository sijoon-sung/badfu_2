> **모델·분할·궤적의 최신 검증:** [2026-10-23 궤적 목록](../00_trajectories/README.md). 원본 공개 코드 재현, 5인 Paper32 재현, 추가 시드, 수정 FUBA 후보를 분리한다.

# 원논문 이해와 기본 검증

먼저 공격의 구성과 삭제 대상을 맞춘다. 그다음 같은 유지 데이터에서 정확한 재학습과 FU를 비교한다. 이전 저장 실험을 이번 재출발의 새 재현 결과로 세지 않는다.

**미리 학습한 원본 궤적은 비교 준비로 보존·재사용한다.** [궤적별 사용 판정](TRAJECTORY_DECISION.md)과 [등록 목록](TRAJECTORY_CATALOG.json)에서 원본 재현, 정상 대조, 기존 공격 대조, 잠복 활성화 비교의 용도를 구분했다. 향후 FU에는 저장된 학습 분할을 그대로 연결해야 한다.

- [BadFU 논문 분석](badfu/PAPER_ANALYSIS.md): 저자의 주장과 그 주장을 넘어서는 해석을 구분한다.
- [BadFU 코드 분석](badfu/CODE_AUDIT.md): 데이터 중복·삭제 단위·가중 방식·평가 분모를 확인한다.
- [FUBA 논문과 코드의 첫 검토](fuba/README.md): 위장을 맡은 공격 역할의 삭제와 FU 중 새 주입을 나눈다.
- [관련 연구 분석](RELATED_WORK.md): UBA-Inf, FedEraser와 탐지·정화·이론의 출발 문헌을 연결한다.
- [기본 검증 계획](BASIC_VALIDATION.md): 정상·독성·위장 학습 조건과 삭제 대조를 정한다.

현재는 [작은 CPU 함수 검사](badfu/code_contract_results.json)와 [수학 구성 예](../04_theory/README.md), [전체 시험 재평가 및 동일 시작점의 이미지 학습 대조](badfu/PRE_ASR_REAUDIT.md)를 완료했다. 새로 수행한 학습은 한 라운드 대조를 구성하는 로컬 학습 4개이며, 새로운 전체 FL 재학습과 완전한 방어 평가는 별도다.

기존 실행을 이어갈 때는 [원래 재현 절차](../../REPRODUCE.md)와 [저자 함수 보존 실행기](../../reference_runner.py)를 참고한다. `sources.json`은 이전 구현·환경 위치의 연결 자료이며 새 검증의 결과표가 아니다.
