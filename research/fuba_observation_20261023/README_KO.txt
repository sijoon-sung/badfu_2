가설: 이미지별 변형을 허용해도 공격 삭제는 큰 정상 참여자의 삭제보다 특정 클래스의 변형 비용을 더 크게 낮춘다.

현재 판단
정밀 점검까지 완료: 공격11.30, 정상27.49로 정상 점수가 더 높았다. 이 비용 점수는 FUBA주력 탐지기로 채택하지 않는다.
코드는 정상 이미지/모델 관측을 검증하는 도구로 보존한다. 큰 정상 참여자와 성공한 잠복 재현 대조는 아직 미완료다.
전역에 잡음을 넣는다는 사실 자체가 공통 변형 탐색의 실패 원인은 아니다. 공통 전역 잡음도 옛 탐색에 포함된다.
옛 탐색에서 빠진 것은 이미지에 따라 달라지는 변형이며, 실패 원인으로 의심할 수 있을 뿐 인과관계는 미검증이다.
입력별 탐색은 이 제약을 완화하지만 정상 모델의 일반 적대적 취약성도 같이 측정한다.
기존 FUBA의 삭제 전 ASR이 이미 높고 G가 정상 모델에도 전이되므로, 이 자료는 잠복 공격 탐지 성공 자료가 아니다.

실제 코드의 분리
1. probe.py: 서버 조건만으로 비용/Conv/FC를 수집한다. 기존 분류기의 가중치를 학습하거나 FU를 다시 하지 않는다.
2. report.py: 모든10클래스의 비용과 Conv/FC 결과를 그래프로 그린다. 공격 여부를 ASR로 점수에 주입하지 않는다.
3. check_invariants.py: 공통 변화 상쇄, 정상 클래스 편향 반례, 탐색 실패의 결측 처리, 실제 변형 비용/예측 재검증, CKA 좌표 불변성을 확인한다.
4. 기존 평가자: research/multiseed_actual_fu_20261022/fuba_oracle.py가 동일 pre/post G를 모든 공격/정상 전후 분류기에 교차 적용한다.
   G/ASR/실제 목표는 평가자 전용이다. 새 서버 코드에는 전달하지 않는다.
5. cost_counterexample.py: ASR0→100이면서 정상 정확도와 최소 변형 비용이 그대로인 정확한 수학적 반례를 계산하고 그린다. 실제 FUBA 재현 실험과 구별한다.

관측 흐름
실제 삭제 전/후 분류기 + 정상 이미지와 라벨 + 입력 기울기
  ├─ 각 목표 클래스, 각 이미지별 변형 탐색
  │    └─ 성공 이미지95%의 Linf 비용 → 전후 비율 → 다른 클래스의 중앙값으로 보정
  └─ post에서 찾은 고정 반경.04의 같은 탐침을 pre/post에 모두 입력
       ├─ 출력: 목표 로짓 마진의 입력 반응 차분
       └─ 내부: 모든 Conv/FC의 반응 RMS와 CKA 차분

수식
이상적 r_m,c(x) = inf{||delta||inf : argmax m(clip(x+delta,0,1))=c}, y!=c.
실제 구현은 유한 PGD로 찾은 성공 변형의 상한 r_hat만 저장한다. 성공하지 못하면 결측/검열 처리한다.
C_m,c = r_hat의95백분위수. 최소95%에서 성공해야 유효하다.
q_c = C_post,c / C_pre,c.
S = 100 max_c[1 - q_c / median_{k!=c}(q_k)].
공통 배율 변화 q_c=g는 정확히 상쇄되지만, 정상 삭제의 클래스별 변화는 상쇄되지 않는다.
반례: 정상 삭제에서도 q=(0.1,1,1,...)이면 S=90이 된다. 이것이 큰 정상 non-IID 대조가 필수인 이유다.
더 근본적인 반례: 기존 오분류 경로 비용이0.01이고 삭제 후 생긴 공격 경로 비용이0.04이면, 최소 비용은 전후 모두0.01이다.
공격 결과가 실제로 달라져도 이 요약 점수는 놓칠 수 있다. 이는 전체 모델 관측으로 탐지가 불가능하다는 증명이 아니라 최소 비용 점수의 정보 손실이다.
95%이상에서 비용eps의 공격이 성공하면 post의95백분위 비용<=eps라는 상한은 따라오지만, pre의 비용이eps보다 크다는 결론은 따라오지 않는다.
내부 반응은 각 모델 안에서 clean-vs-probe로 측정한 후 모델 사이에서 뺀다. 재학습 전후 뉴런 번호가 같은 의미라고 가정하지 않는다.
FC는 원래 출력 클래스 의미가 고정되어 있지만, 중간 특징의 좌표는 고정이라고 가정하지 않는다.

추가로 필요한 조건
서버가 실제 전후 분류기와 입력 기울기(white-box), 같은 과제의 클래스별 정상 이미지/라벨을 보유한다.
협조 클라이언트나 그 로컬 데이터, 실제 트리거, G, ASR은 이 버전에 필요 없다.
조건이 부족한 서버에서 이 구현을 그대로 사용할 수 있다고 주장하지 않는다.
probe 비용은 이미지별로 새로 최적화한 값이다. 배포 가능한 공통 트리거 함수나 범용 공격을 복원했다고 해석하지 않는다.
입력 범위를[0,1]로 고정했으므로 원 코드가 허용하는 음수 픽셀까지 포함한 포괄성 주장은 하지 않는다.

실행 (작업 폴더: C:\Users\sijoo\Documents\ChatGPT\badFU)
한 번에 실행: powershell -NoProfile -File research/fuba_observation_20261023/run.ps1 -Split pilot -Precision fine
수식/구현 점검만: powershell -NoProfile -File research/fuba_observation_20261023/run.ps1 -CheckOnly
실제 재현 후 공격1쌍과 큰 정상 참여자 삭제1쌍의 파일/해시를 새 config로 지정해 probe.py에 --config를 전달하면 같은 관측을 실행할 수 있다.
현재 run.ps1의 기본 config는 기존 빠른 점검용 체크포인트이므로 재현 성공 모델로 오해하지 않는다.
envs/badfu-original/python.exe research/fuba_observation_20261023/check_invariants.py
envs/badfu-original/python.exe -u research/fuba_observation_20261023/probe.py --config research/rapid_checkpoint_validation_20261023/FUBA_CONFIG.json --out research/fuba_observation_20261023/fine_pilot --split pilot --precision fine
envs/badfu-original/python.exe research/fuba_observation_20261023/report.py --out research/fuba_observation_20261023/fine_pilot
envs/badfu-original/python.exe -u research/fuba_observation_20261023/probe.py --config research/rapid_checkpoint_validation_20261023/FUBA_CONFIG.json --out research/fuba_observation_20261023/confirmation --split confirmation
envs/badfu-original/python.exe research/fuba_observation_20261023/report.py --out research/fuba_observation_20261023/confirmation
동일 출력 폴더의 재실행은 거절하여 결과를 덮어쓰지 않는다. quick은 최초4회 반경 세분화, fine은10회이며 모든 모델에 똑같은 예산을 적용한다.
최초 quick 결과(공격40.32, 정상40.27)는 pilot/에, 실행 소스는 probe_pilot_executed.py로 보존했다.
quick의 여러 클래스 비용이 같은 거친 값으로 모여 수치 해상도 진단으로 fine을 추가했다. 목표/점수/임계값/분류기는 바꾸지 않았다.

지금 실행하는 자료
기존 FUBA m07/m08 공격 전후, m09/m10 정상 같은 참여자 삭제 전후.
pilot80장과 confirmation80장은 서로 겹치지 않으며 기존 gamma 강도 선택9280장과도 겹치지 않는다.
이 자료는 이전 진단에서도 사용했으므로 새로운 독립 검증집합이 아니다. 학습1회이며 fine의 탐색 초기화2회를 학습2회라고 세지 않는다.
동일한 비용 하한95%는 달성률을 정확히 일치시키는 절차가 아니다. 이 버전은 독립 변형의 비용 백분위수다.
분류기의 실제 학습 시드 반복이나 큰 정상 참여자의 온전한 탈퇴를 대체하지 않는다.

주력 채택 기준
가설을 유지하려면: 재현 통과 → 정확도 유지한 실제 전후 → 최대 정상 참여자 탈퇴와 동등 조건 → 독립 FL시드 → 별도 정상 보정에서 정한 동일 오탐률 비교.
probe 계열별 예산이 다르므로 옛 universal-L1와 새 per-image-Linf의 수치/옛40% 경보 임계값을 혼용하지 않는다.
Conv/FC의 추가 가치는 단순 그래프 차이가 아닌 같은 오탐률에서의 추가 탐지로 평가한다.
재현 실패는 탐지 불가능의 증명이 아니다. 정상과 겹치는 결과도 숨기지 않는다.
상기 조건에서 구별되지 않으면 이 관측만 쓰는 주력 탐지기 주장을 버리고, 협조 클라이언트의 반응 같은 별도 관측을 명시한 새 가설로 옮긴다.

발상의 출처
PGD/적대적 입력 탐색: Madry et al., https://arxiv.org/abs/1706.06083
신경망 표현 비교 CKA: Kornblith et al., https://arxiv.org/abs/1905.00414
입력과 무관한 공통 변형/모델 간 전이의 선행 예: Moosavi-Dezfooli et al., https://arxiv.org/abs/1610.08401
공격 코드 출처: https://github.com/stcebra/FUBA (ity207/FedUBA와 별개)
위 논문들은 이 새 전후 탐지기가 FUBA와 큰 정상 non-IID 탈퇴를 구별한다는 증거가 아니다.
우리 검증 후보는 전후 비용/반응과 정상 삭제 대조의 결합이며, 신규성 확정도 아직 하지 않는다.
