# FUBA v3 · 15/100R 중단 모델 검토용 사본

**100R 재현 미완료·진단 전용입니다.** 16R 참여자1의 γ=0 가상 집계가 로컬 사전 억제 기준을 실패해 등록된 규칙대로 중단했습니다. 재학습·재개·조건 변경은 하지 않았습니다. stcebra/FUBA 수정 후보이며 별도 ity207/FedUBA와 다릅니다.

- 마지막 완전 저장: 15R 분류기와 동일 집계 생성기. 정상 정확도 76.1000% / 전체10000장, ASR 8.1333% / 타깃 제외9000장. 독립 재계산이 기존 평가와 정확히 일치했습니다.
- 실패 지점: 16R γ0 로컬 ASR 12.946429% (29/224). 15R의 전체 시험 ASR과 분모·모델·생성기가 다릅니다. 고정 실패 모델로 이 값도 재현했습니다.
- CA>=80%·ASR<=10%·100R 완료의 전체 게이트는 통과하지 못했습니다. 승인된 잠복 전후쌍·논문 재현 성공이 아닙니다.
- 15R 전체 파일·앞뒤 모델·집계 오차0,120개 역할 기록·13개 같은 생성기 그룹, 단계별50epoch/생성기5epoch를 검사했습니다.

`classifier.pt`, `aggregate_generator.pt`는 바로 읽을 수 있는 bare state_dict입니다. `checkpoint_round0015.pt`는 원본 전체 묶음이며 분류기는 `gm_after`, 생성기는 `extras.aggregate_generator`입니다. `failure_round0016_client01.pt`에는 실패 당시 생성기·수신 모델·앵커·γ0 가상 모델이 있습니다.

파일 해시·엄격 CPU 로딩·출력은 `python load_checkpoint.py --expected-manifest-sha256 <외부 EXPORT_TERMINAL_READY.json 값>`으로 확인할 수 있습니다. `MANIFEST.json`과 `SEAL.json`을 검증하며 외부 해시는 연구 카탈로그에도 등록합니다.

원본 전체15R은 D:\FUBA_PAPER_REBUILD_20261024\attack_100R/fl 에 보존했습니다. 이 사본은 마지막 라운드와 실패 진단만 포함하며 전체15개 라운드 묶음을 복제한 것은 아닙니다. `native_manifest_running_prefix.json`의 running 문구는 원본 저장 시점 메타데이터입니다. 실제 프로세스는 종료됐고 STATE는 failed입니다.

검증 도구의 최초 두 시도는 모듈용 digest를 bare dict에 호출한 오류와 원시 평균 BN 정수 카운터 비교 오류로 멈췄습니다. 원래 검증 소스는 provenance에 보존했습니다. 최종 검사는 num_batches_tracked의 정상 float→int 로딩만 명시적으로 인정하며 파라미터·BN 평균/분산의 동일성은 그대로 검사했습니다. 학습 모델이나 학습 조건을 수정한 사건이 아닙니다. 첫 내보내기는 Windows 경로 구분자와 ZIP 목록의 표기 차이로 최종 봉인을 완료하지 못했습니다. 그 중간 폴더와 소스를 보존했고 이 별도 _verified 폴더의 경로·파일·ZIP을 검증했습니다.

생성기·실제 타깃·ASR·공격 역할 정보는 평가자 전용입니다. 서버 탐지 방법 입력에 넣지 않습니다. 기존 BadFU 확정본과 FUBA63R/100R 사본은 보존돼 있습니다.
