**실험 과정을 읽는 자료:** [전체 정리와 개별 실험](reports/experiment_process_20261026/README.md) · [교수 미팅용 Word 문서](reports/experiment_process_20261026/BadFU_실험과정_전체정리_20261026.docx)

> **항상 먼저 읽기:** [연구 실험 인덱스](research/INDEX.md) → [관련 실험 카드](research/EXPERIMENT_CARDS.md) → 연결된 원 보고서. **단순 반응량은 큰 정상 non-IID 탈퇴와 공격을 구별하지 못했다.** 새 제안은 이 반례와 기존 실패를 먼저 검토한다. [전체 폴더 색인](research/EXPERIMENT_FOLDERS.md)
>
> **확정 모델 바로 열기:** [BadFU 기준 체크포인트 v1](CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1/README.md). 삭제 전 ASR **14.29% → 위장 제거 후 100%**, 정상 정확도 **90.38% → 90.46%**. 저자 코드 직접 비교를 통과한 모델·정상 대조·공통 초기값을 읽기 전용 독립 사본으로 보관했다. 공격 재현의 관측이며 탐지 성공을 의미하지 않는다.
>
> **연구 모델 선택:** [검증된 궤적과 폴더 목록](research/00_trajectories/README.md). 최종 모델 기본 ID는 `badfu.confirmed.s20261023.v1`, 전체 이력 기본 ID는 `badfu.paper32.s20261020`이다. 파일 이름이나 날짜로 모델을 고르지 않는다.

# BadFU 연구

[FUBA 체크포인트 생성·로컬 전달 상태](CHECKPOINTS_FOR_REVIEW/README.md)

[처음부터 읽는 연구 정리](research/README.md)에서 논문·코드·기본 검증·방어 가설·수학적 근거를 순서대로 읽는다.

모든 새 실험은 [가설 한 줄 정리 원칙](research/EXPERIMENT_RULES.md)을 따른다. 최신 판정은 연구 실험 인덱스를 우선하고, [2026-10-20 미팅 자료](research/05_meetings/20261020/CLAIM_BOARD.md)는 당시 주장과 검증의 기록으로 읽는다.

- [원논문 재현](research/01_reproduction/README.md)
- [정화와 방어 가설](research/02_purification/README.md)
- [탐지의 문제 정의](research/03_detection/README.md)
- [수학적 명제와 증명](research/04_theory/README.md)
- [앞에서 제외한 시도](research/90_archive/README.md)

실행을 이어갈 때는 [재현 및 재개 절차](REPRODUCE.md)를 사용한다. 모델·데이터·환경·기존 실행 코드는 원래 경로를 유지한다.

[이전 전체 실행 안내](research/90_archive/root_readme_before_reorganization.md) · [옛 실험 원본 색인](pr_reports/INDEX.md)
