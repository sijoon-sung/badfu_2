가설: FUBA 체크포인트 생성을 BadFU의 추가 탐지 평가와 분리하면, 무관한 평가 오류가 FUBA 학습·저장을 막는 실행 의존성을 제거할 수 있다.

조건: 기존 등록 대상인 `stcebra/FUBA`의 v2 수정 후보, 시드20261023, 20개 참여자, 네이티브5-rank MPI, 전체 자료, 기존100R 예산을 유지한다. 별도 `ity207/FedUBA`와 혼동하지 않는다. 기존 실패와 BadFU 확정 모델은 보존한다.

비교: 동결된 v2 학습·평가 코드는 유지하며 실행 대기 조건과 운영상 상태 기록만 분리한다. GPU가 실제 비어 있는지와 새 CUDA 프로세스의 정상 동작을 확인한 뒤 시작한다.

결과: 실제100R 학습·전체 저장 검증·최종 평가·로컬 복사를 완료했다.100개 라운드의 파일·모델 연결·참여자 집계 오차0과186개 라운드/참여자 그룹의 작업자 생성기 일치를 확인했다. 전체 시험10000장 정확도71.87%, 타깃 제외9000장 ASR99.0889%로 사전 억제 기준10%를 실패했다. 같은 최종 분류기와 집계 생성기를 사용했으며 생성기의 평가 전후 상태가 같았다.

판정: 체크포인트 생성·검증·전달 완료, 잠복 공격 재현 실패. 삭제 전 단일 검토용 모델을 진단 전용으로 등록했다. 사전 억제 실패에 따라 이 후보의 정상 대조·삭제 후 활성화 분기는 실행하지 않았으며, 승인된 FUBA 전후쌍으로 사용하지 않는다. 조건을 바꾸거나 같은 학습을 자동 반복하지 않는다.

반증 기준: 새 CUDA 검사, 저장 무결성, 집계 또는 생성기 동기화가 실패하면 오류와 저장된 접두 구간을 보존한다. ASR에 맞춰 하이퍼파라미터·시드·판정 기준을 바꾸지 않는다.

## 현재 실행과 확인

- DISLAB 운영 폴더: `D:/FUBA_CHECKPOINT_RECOVERY_20261023`
- 실제 학습·저장: `D:/FUBA_CHECKPOINT_RECOVERY_20261023/controller/fuba_v2_seed20261023_attack`
- 최초 Windows 일회성 작업: `Codex-FUBA-checkpoint-20261023` (82R 저장 목록 교체 오류로 종료; 재실행 금지)
- 완료된 재개 작업: `Codex-FUBA-checkpoint-resume-20261023` (83–100R 완료; 예약 트리거·반복 없음; 재실행 금지)
- [첫 저장 파일 검증](FIRST_CHECKPOINT_VERIFIED.json) · [공격 역할6R 검증](ATTACK_CHECKPOINT_VERIFIED.json) · [대기 의존성 변경](execution_dependency.patch) · [실행 계획](RECOVERY_PLAN.json)

저장 라운드는 변하므로 다음 명령으로 실제 프로세스·GPU·manifest를 함께 확인한다.

```powershell
.\envs\badfu-original\python.exe research\fuba_checkpoint_recovery_20261023\ops.py run status_remote.py
```

이 대화의10분 간격 후속 확인(ID `fuba`)으로 오류 복구·최종 검증·복사를 마쳤다. 전달 관련 검증이 끝나 이 자동 확인을 종료한다. 실패한 기존 큐의 `queued_after_badfu` 문구는 현재 상태로 사용하지 않는다.

## 완료된 최종100R 전달

- [이 컴퓨터의 최종 모델·코드 열기](../../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_pre_round100/README.md)
- [로컬 복사·CPU 로딩·출력 검사](LOCAL_COPY_COMPLETE.json) · [외부 등록 봉인 근거](../00_trajectories/audit/FUBA_V2_ROUND100_DELIVERY.json)
- 명시적 ID: `fuba.v2.s20261023.pre.round100`, 허용 용도 `diagnostic`. 분류기·같은 집계 생성기·초기값·아키텍처·로더·평가 및 복구 근거25개 파일을 읽기 전용 사본으로 보존했다.
- 평가 버전: 고정 v2 `evaluate_v2.py`, SHA256 `d21c9f6b52e97f12f09892555c04de860afd153a89ee11c608c378e9410e27bb`. 전체10000/9000장 결과와 학습 중 별도 시험 분할의72.3058%/99.0022%를 혼동하지 않는다.
- [생성기 평가 연결 검사](FINAL_EVALUATOR_LINKAGE.json): 저장 형식의15개 BN 카운터가 float32, 모델 로딩 후 int64라 원시 텐서 해시와 평가 해시는 다르다. 카운터 값30030은 동일하며, 실제 로딩된 생성기의 전체 텐서 해시는 평가기가 사용한 생성기와 정확히 일치한다. 모델·평가·보존본은 변경하지 않았다.

아래는 사용한 전달 절차다. 완료 증거가 있으면 기존 봉인과 해시를 확인하며, 사본을 새 학습의 재개 폴더로 사용하지 않는다.

최종100R 및 고정 평가가 완료되면 `ops.py run export_finished.py`, 이어서 로컬 `collect_finished.py`를 실행한다. 검토용 가중치는 `CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_pre_round100`에 복사하고 해시와 CPU 텐서 로딩을 확인한다. 이는 검토용 삭제 전 모델이며, 정상 대조·삭제 후 활성화까지 통과하기 전에는 확정 전후쌍으로 등록하지 않는다. 사전 억제 실패도 판정과 함께 보존·전달한다.

복사 후 `register_finished.py`로 외부 봉인 근거를 등록하고 `build_catalog.py`에서 진단 전용 case를 생성했다. 기본 BadFU 사례는 유지한다. 사전 억제 실패에 따라 `04_reproduction_failed/FUBA_v2_s20261023_pre100`에 분류했다. 카탈로그는 DISLAB에도 게시하며, 로컬 연구 목록은 `research/index_tools/rebuild_index.py --check`로 확인한다.

운영 점검의 최초6R 진단 스크립트에서 추적 라운드를0부터 세는 것으로 잘못 가정한 시도는 `verify_attack_checkpoint_round_index_attempt1.py`에 보존했다. 실제 추적은1부터 세므로 이를 맞춰 다시 검증했다. 학습 코드를 바꾸거나 학습을 재시작한 사건이 아니다.

## 사용자 요청으로 중간63R 전달

관련 카드 R02.100R 완료를 기다리지 않고 실제63R 저장 파일을 고정했다. 8개 참여자와 전역 모델·생성기 텐서의 유한성/BN,62→63 연결, 해당 라운드 집계 오차0 및 작업자 생성기 동기화를 확인했다. 같은 파일에서 추출한 분류기·집계 생성기를 DISLAB와 로컬 양쪽에서 엄격 로딩하고 유한 출력까지 확인했다. 학습은 중단하거나 다시 시작하지 않았다.

- [로컬 모델·코드 바로 보기](../../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_round0063/README.md)
- [중간 체크포인트 압축파일](../../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_round0063.zip)
- [로컬 복사·로딩 검사](PARTIAL_LOCAL_round0063.json)
- 명시적 ID: `fuba.v2.s20261023.round0063.partial`, 허용 용도 `diagnostic`. 승인된 잠복 공격 전후쌍은 아니다.

새 탐지 실험 또는 non-IID 구별 가설이 아닌 사용자 요청 파일 전달이다. 중간63R 사본은 보존하며 최종100R의 별도 전달도 완료했다.

## 82R 저장 오류 복구와83R 재개

관련 카드 R02. 첫 실행은81R 목록까지 게시한 뒤82R `manifest.json.tmp`를 `manifest.json`으로 교체하다 Windows 접근 거부(WinError5)로 종료됐다.82R 모델 파일은 이미 완전히 저장돼 있었다. 원래 코드·실패 로그·81R 목록·82R 임시 목록은 `storage_incident_round0082`에 보존했다.

가설: 일시적인 Windows 파일 잠금을 견디는 원자적 JSON 저장과 저장된 상태 복원만으로 같은 학습 궤적을 이어갈 수 있다. 이는 저장 운영 가설이며 새로운 공격 탐지 관측이 아니다. 큰 정상 non-IID 탈퇴 반례를 해결했다는 주장은 하지 않는다.

조건·비교: 기존82개 파일 해시, 기존81개 목록 항목의 불변성,81→82 모델 연결,82R 집계 재구성 오차0을 확인한 후82R 저장 목록을 복구했다. 별도 `storage_resume_v1/runtime`에서 최종 분류기·집계 생성기·개별 제출 생성기를 복원하고83R부터 이어간다. 원본 학습 소스·초기값·82개 모델은 보존하며, 같은 시드·자료·참여자 선택·역할 루프·100R 조건을 유지한다. 실제 Windows 삭제 공유를 막는 파일 핸들로 재시도 검사를 통과했다.

결과: 새83R 파일 해시와82→83 전역 모델 연결, 집계 오차0, 텐서 유한성·BN, 세 작업자의 생성기 해시·평가 모드를 확인했다. 이후100R까지 완료했고 전체 검증·평가·복사 결과는 위에 연결했다. 중단은82R 평가 전송 전에 발생했으므로 빠진82R 평가 수치를 만들어 채우지 않는다.

검증 코드의 별도 정정: 동결된 `verify_v2.py`가 최초5R 준비 구간에 정상적으로 존재하는 생성기 `None`을 순회하던 오류를 확인했다. `storage_resume_v1/verify_v2.py`에서 해당 준비 구간만 허용하며6R 이후 생성기 누락은 실패로 처리한다. 원본 검증 코드는 보존했다.

판정·중단 기준: 저장 복구와 첫 재개 라운드 검사는 통과했다. 접두 모델·연결·참여자·집계·동기화가 어긋나면 멈추고 근거를 보존한다. 사전 ASR이나 결과에 맞춰 재학습 조건을 바꾸지 않는다.

- [82R 복구 근거](PENDING82_RECOVERED.json) · [재개 계획](STORAGE_RESUME_PLAN.json) · [83R 확인](RESUMED_ROUND0083_VERIFIED.json)
- [실제 Windows 잠금 재시도 검사](storage_resume_v1/ATOMIC_JSON_RETRY_CHECK.json) · [재개 코드 차분](storage_resume_v1/runtime.patch) · [준비 구간 검증 정정](storage_resume_v1/verifier_warmup_fix.patch)
- 실제 로그는 `STATE.json`의 `training_console_path`와 `supervisor_console_path`를 따른다. 최초 로그만 보고 재개 상태를 판단하지 않는다.
