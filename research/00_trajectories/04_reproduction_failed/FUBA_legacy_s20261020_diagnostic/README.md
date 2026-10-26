# 과거 FUBA s20261020 전후 — 재현 실패 보존 진단

고정ID: `fuba.legacy.s20261020.retained_pairs.diagnostic` · 허용목적: diagnostic

- 기존4개 저장분류기의 해시/출처만 별도 명시. 새 학습/새 공격 재현이 아니다.
- 삭제 전 이미 높은ASR/정상모델 G전이. 잠복 전후쌍 또는 탐지양성 승인 아님.
- 억제 참여자 삭제와 정상 같은 참여자 삭제의 진단 대조. 큰 정상 탈퇴 대조 없음.
- latest v5 단일모델 또는 다른 라운드를 전후에 섞지 않는다.
- 표본 기하학 통계를 기술할 diagnostic만 허용. 기본 BadFU/전체 이력/기존 모든실패 보존.

[등록 근거](../../audit/FUBA_LEGACY_S20261020_DIAGNOSTIC_20261025.json)
