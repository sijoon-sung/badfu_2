# DISLAB 궤적과 관측 캐시 확인

사용자가 지적한 대로 전체 궤적은 남아 있다. 아래는 이번에 manifest와 실제 파일 존재·크기를 대조한 묶음이다.

| DISLAB 경로 | 계획 라운드 | 초기 포함 파일 | 현재 확인 |
|---|---|---|---|
| artifacts/badfu_author_s42/full6 | 40 | 41 | 파일 존재·크기 일치 |
| artifacts/badfu_author_s42/cover5 | 40 | 41 | 파일 존재·크기 일치 |
| artifacts/badfu_author_s42/bd5 | 40 | 41 | 파일 존재·크기 일치 |
| artifacts/badfu_author_s42/clean5 | 40 | 41 | 파일 존재·크기 일치 |
| artifacts/badfu_author_s42/fu_remove5 | 20 | 21 | 파일 존재·크기 일치 |
| artifacts/badfu_author_s42/fu_remove1 | 20 | 21 | 파일 존재·크기 일치 |
| artifacts/fuba_cifar10_s42/fl | 100 | 101 | 파일 존재·크기 일치 |
| artifacts/fuba_cifar10_benign_s42/fl | 100 | 101 | 파일 존재·크기 일치 |
| artifacts/fuba_cifar10_benign_s43/fl | 100 | 101 | 파일 존재·크기 일치 |
| artifacts/fuba_cifar10_benign_s44/fl | 100 | 101 | 파일 존재·크기 일치 |

BadFU 6단계는 초기 모델을 포함해 **206파일**이다. 파일 시각은 복사·이동으로 바뀔 수 있으므로 실행 순서의 단독 근거로 사용하지 않는다.

샘플 체크포인트에는 `gm`, `cms`, `gm_after`, `client_ids`, `weights`, `extras`가 들어 있다. 글로벌 모델 하나만 저장된 자료가 아니다. BadFU full6 1R의 float 텐서102개와 FUBA1R의122개를 집계한 최대 절대 차이는 각각 **3.58e-7**, **3.73e-9**였다. FU remove5의 weights는 재보정 의미로 명시돼 있어 최종 FedAvg와 같은 집계 검사를 적용하지 않았다.

## 이미지별 캐시도 보존돼 있다

| 캐시 | 라운드 파일 | 확인한 배열 |
|---|---|---|
| BadFU full6 관측 | 40 | 3묶음 × 6명 × 13변형 × 80이미지 × 10출력 |
| FUBA 공격 관측 | 100 | 3묶음 × 20명 × 13변형 × 80이미지 × 10출력, 참여 마스크 |
| FUBA 정상 seed42 관측 | 100 | 같은 구조, 참여 마스크 |

각 묶음 첫 파일의 구조를 직접 읽었다. 모든 파일의 내부 배열을 이번에 전부 검산한 것은 아니다. 이미지별 재집계에 필요한 원자료가 남아 있다는 점은 확인했다. 이미지 ID와 정답을 연결한 클래스별 재분석은 추가 확인 후 가능하며, 새 FL 학습이 반드시 필요한 작업은 아니다.

## 사용할 수 있는 것과 별도로 필요한 것

- **가능:** 과거 클라이언트별 기여, 참여, 패치 반응, 점수·보정·순위의 재분석.
- **대응 확인 필요:** 최근 16개 요청 또는 새84건과 이 과거 궤적의 모델·자료 동일성. 다른 시드·분할·클라이언트 구성이면 같은 요청의 이력으로 대체하지 않는다.
- **별도 관측 필요:** 같은 클라이언트 내부 부분 삭제의 원자 기여와 독립 요청 기여. 글로벌·클라이언트 궤적이 있다고 그 내부 정보까지 자동 복원되는 것은 아니다.
- **대조 필요:** 같은 full6 시작점·같은 실제 FU 방법의 정상 삭제. clean5와 full6, cover5에서 시작한 remove1과 full6에서 시작한 remove5를 대응 대조처럼 사용하지 않는다.

이전 [H01](../pr_reports/pending/H01.md)의 최근16건 대응 문제와, 전체 이력 실험의 존재를 구분한다. 저장소 전체에 이력 자료가 없다는 해석은 잘못이다.

근거: [전체 파일 목록](evidence/dislab_inventory.json), [파일·구조 확인](evidence/trajectory_check.json), [샘플 집계 검산](evidence/sampled_aggregation_check.json), [캐시 구조](evidence/cache_check.json). 전체 디스크가 아니라 확인한 antigravity 저장소와 지정 깊이의 목록이다. FUBA의 과거 pkl5,745개도 목록에 있지만 이번 안전 로딩 표본 검사는 위 새 pt 형식만 대상으로 했다.
